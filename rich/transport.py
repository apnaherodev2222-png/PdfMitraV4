"""Rich HTTP transport, retries, circuit breaker and lifecycle operations."""
from __future__ import annotations

import asyncio
import time
from weakref import WeakValueDictionary

from core import logger
from rich_message import (
    RichMessageError, send_blocks, edit_blocks, edit_blocks_plain,
    delete_message, blocks_to_inline_keyboard,
)
from .validator import validate_blocks, _is_transient, _STRIPPABLE_BLOCK_TYPES
from .metrics import METRICS

try:
    import config as _cfg_mod
    _MAX_ATTEMPTS = max(1, getattr(_cfg_mod, "RICH_MAX_ATTEMPTS", 3))
    _BACKOFF_BASE = float(getattr(_cfg_mod, "RICH_BACKOFF_BASE", 0.4))
    _BACKOFF_MAX = float(getattr(_cfg_mod, "RICH_BACKOFF_MAX", 4.0))
    _MAX_CONCURRENT = max(1, getattr(_cfg_mod, "RICH_MAX_CONCURRENT", 8))
    _CIRCUIT_THRESHOLD = int(getattr(_cfg_mod, "RICH_CIRCUIT_THRESHOLD", 5))
    _CIRCUIT_COOLDOWN = int(getattr(_cfg_mod, "RICH_CIRCUIT_COOLDOWN", 60))
except Exception:
    _MAX_ATTEMPTS = 3
    _BACKOFF_BASE = 0.4
    _BACKOFF_MAX = 4.0
    _MAX_CONCURRENT = 8
    _CIRCUIT_THRESHOLD = 5
    _CIRCUIT_COOLDOWN = 60

# FIX_PM_91: retry once on transient connection errors so the fallback path only fires on real failures.
class _CircuitBreaker:
    """FIX_PM_102: fast-fail during Rich API outages."""
    def __init__(self, threshold: int, cooldown: int):
        self.threshold = max(1, threshold)
        self.cooldown = max(1, cooldown)
        self.fails = 0
        self.opened_at = 0.0

    def is_open(self) -> bool:
        if self.fails < self.threshold:
            return False
        if (time.monotonic() - self.opened_at) > self.cooldown:
            self.fails = self.threshold - 1
            return False
        return True

    def record_success(self):
        self.fails = 0
        self.opened_at = 0.0

    def record_failure(self):
        self.fails += 1
        if self.fails >= self.threshold and self.opened_at == 0.0:
            self.opened_at = time.monotonic()

_BREAKER = _CircuitBreaker(_CIRCUIT_THRESHOLD, _CIRCUIT_COOLDOWN)

async def _send_with_retry(chat_id, block_list, *, reply_to_message_id=None,
                           disable_notification=False):
    # FIX_PM_93: compute block_list once; retries reuse the same list.
    # FIX_PM_109: each retry reuses the same precomputed block_list.
    delay = _BACKOFF_BASE
    for attempt in range(_MAX_ATTEMPTS):
        t0 = time.monotonic()
        try:
            resp = await asyncio.to_thread(
                send_blocks, chat_id, block_list,
                reply_to_message_id=reply_to_message_id,
                disable_notification=disable_notification,
            )
            METRICS.record_send((time.monotonic() - t0) * 1000.0)
            _BREAKER.record_success()
            return resp
        except RichMessageError as exc:
            METRICS.record_fail(str(exc))
            if not _is_transient(exc) or attempt == _MAX_ATTEMPTS - 1:
                _BREAKER.record_failure()
                raise
            await asyncio.sleep(delay)
            delay = min(delay * 2.0, _BACKOFF_MAX)
    raise RuntimeError("unreachable: retry loop exited without return/raise")

async def _send_with_media_strip(chat_id, block_list, *,
                                 reply_to_message_id=None,
                                 disable_notification=False):
    try:
        return await _send_with_retry(
            chat_id, block_list,
            reply_to_message_id=reply_to_message_id,
            disable_notification=disable_notification,
        )
    except RichMessageError as exc:
        if not _is_transient(exc):
            raise
        stripped = [
            b for b in block_list
            if not (isinstance(b, dict) and b.get("type") in _STRIPPABLE_BLOCK_TYPES)
        ]
        if len(stripped) == len(block_list):
            raise
        logger.warning(
            "RICH_PM: retrying without %d media block(s) after transient",
            len(block_list) - len(stripped),
        )
        return await _send_with_retry(
            chat_id, stripped,
            reply_to_message_id=reply_to_message_id,
            disable_notification=disable_notification,
        )

# FIX_PM_108: WeakValueDictionary lets idle per-chat locks be GC'd once no
# coroutine references them, so long-running bots do not accumulate locks.
_CHAT_LOCKS: "WeakValueDictionary[int, asyncio.Lock]" = WeakValueDictionary()
_CHAT_LOCKS_GUARD = asyncio.Lock()

async def _chat_lock(chat_id: int) -> asyncio.Lock:
    async with _CHAT_LOCKS_GUARD:
        lock = _CHAT_LOCKS.get(chat_id)
        if lock is None:
            lock = asyncio.Lock()
            _CHAT_LOCKS[chat_id] = lock
        return lock

_SEMAPHORE = None

def _semaphore() -> asyncio.Semaphore:
    global _SEMAPHORE
    if _SEMAPHORE is None:
        _SEMAPHORE = asyncio.Semaphore(_MAX_CONCURRENT)
    return _SEMAPHORE

async def rich_send(chat_id, blocks, *, reply_to_message_id=None,
                    disable_notification=False):
    # FIX_PM_RICH_4: Rich HTTP is blocking; run it off the PTB event loop.
    # FIX_PM_101: circuit breaker + semaphore + validator + media-strip.
    # FIX_PM_91: transient Rich API connection failures get one retry.
    block_list = list(blocks)
    errs = validate_blocks(block_list)
    if errs:
        raise RichMessageError(f"invalid blocks: {errs[0]}")
    if _BREAKER.is_open():
        METRICS.record_circuit_skip()
        raise RichMessageError("rich circuit open")
    async with _semaphore():
        resp = await _send_with_media_strip(
            chat_id, block_list,
            reply_to_message_id=reply_to_message_id,
            disable_notification=disable_notification,
        )
        METRICS.record_blocks(block_list)
        return resp

async def rich_replace(chat_id, message_id, blocks):
    # FIX_PM_RICH_5 (superseded by FIX_PM_94 below): originally always did a
    # delete-then-send to avoid unreliable rich editMessageText behavior.
    # FIX_PM_94: try in-place edit first; fall back only after edit failure.
    # FIX_PM_101: same circuit + semaphore + validator path.
    block_list = list(blocks)
    errs = validate_blocks(block_list)
    if errs:
        raise RichMessageError(f"invalid blocks: {errs[0]}")
    if _BREAKER.is_open():
        METRICS.record_circuit_skip()
        raise RichMessageError("rich circuit open")
    lock = await _chat_lock(chat_id)
    async with lock:
        async with _semaphore():
            try:
                t0 = time.monotonic()
                resp = await asyncio.to_thread(edit_blocks, chat_id, message_id, block_list)
                METRICS.record_send((time.monotonic() - t0) * 1000.0)
                METRICS.record_blocks(block_list)
                _BREAKER.record_success()
                return resp
            except Exception as exc:
                METRICS.record_fail(str(exc))
                logger.debug("RICH_PM: rich edit failed (%s)", str(exc)[:120])
            # FIX_PM_94: rich edit is attempted before any destructive operation.
            try:
                t0 = time.monotonic()
                reply_markup = blocks_to_inline_keyboard(block_list) or {"inline_keyboard": []}
                resp = await asyncio.to_thread(
                    edit_blocks_plain, chat_id, message_id, block_list, reply_markup
                )
                METRICS.record_send((time.monotonic() - t0) * 1000.0)
                METRICS.record_blocks(block_list)
                _BREAKER.record_success()
                logger.debug("RICH_PM: plain-text edit succeeded")
                return resp
            except Exception as exc:
                METRICS.record_fail(str(exc))
                logger.debug("RICH_PM: plain edit failed (%s)", str(exc)[:120])
            # FIX_PM_94 v2: send new first; delete old only after successful send.
            new_resp = await _send_with_media_strip(chat_id, block_list)
            try:
                await asyncio.to_thread(delete_message, chat_id, message_id)
            except Exception:
                logger.debug("RICH_PM: old message delete skipped")
            METRICS.record_blocks(block_list)
            return new_resp


__all__ = ["rich_send", "rich_replace"]
