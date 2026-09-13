"""PDF Mitra Pro — Telegram Rich Message glue layer."""
from __future__ import annotations

import asyncio
from typing import Any, Awaitable, Callable, Dict, Optional, Sequence

from core import logger

# FIX_PM_21: RICH_IMPORT_ERROR is always defined so boot logs can print it.
RICH_IMPORT_ERROR: Optional[str] = None
try:
    from rich_message import (
        RichMessageError,
        heading, paragraph, compact_table, button_row, video,
        send_blocks, edit_blocks, delete_message,
    )
    RICH_AVAILABLE = True
except Exception as _imp_exc:
    # FIX_PM_RICH_1: Keep the bot bootable when rich_message.py or its dependency is unavailable.
    RICH_IMPORT_ERROR = str(_imp_exc)
    RICH_AVAILABLE = False
    class RichMessageError(Exception):
        pass
    def _missing(*_a, **_k):
        raise RichMessageError(f"rich_message.py unavailable: {RICH_IMPORT_ERROR}")
    heading = paragraph = compact_table = button_row = video = _missing
    send_blocks = edit_blocks = delete_message = _missing


def rich_callback_button(text, callback_data, style="primary"):
    # FIX_PM_RICH_2: Centralize rich callback button construction without changing callback_data values.
    return {"text": text, "callback_data": callback_data, "style": style}


def rich_url_button(text, url, style="primary"):
    # FIX_PM_RICH_3: Centralize rich URL button construction for keyboards that expose links.
    return {"text": text, "url": url, "style": style}


# FIX_PM_91: retry once on transient connection errors so the fallback
# path only fires on real failures.
_TRANSIENT_MARKERS = (
    "connection reset",
    "connection aborted",
    "temporarily unavailable",
    "timed out",
    "timeout",
)

def _is_transient(exc) -> bool:
    msg = str(exc).lower()
    return any(m in msg for m in _TRANSIENT_MARKERS)

async def _send_with_retry(chat_id, blocks):
    # FIX_PM_93: compute block_list once; if `blocks` is a generator, calling
    # list(blocks) a second time on retry would send an empty payload.
    block_list = list(blocks)
    try:
        return await asyncio.to_thread(send_blocks, chat_id, block_list)
    except RichMessageError as exc:
        if not _is_transient(exc):
            raise
        await asyncio.sleep(0.4)
        return await asyncio.to_thread(send_blocks, chat_id, block_list)


async def rich_send(chat_id, blocks):
    # FIX_PM_RICH_4: Rich HTTP is blocking; run it off the PTB event loop.
    # FIX_PM_91: transient Rich API connection failures get one retry.
    if not RICH_AVAILABLE:
        raise RichMessageError("rich_message.py unavailable")
    return await _send_with_retry(chat_id, blocks)


async def rich_replace(chat_id, message_id, blocks):
    # FIX_PM_RICH_5 (superseded by FIX_PM_94 below): originally always did a
    # delete-then-send to avoid unreliable rich editMessageText behavior.
    # FIX_PM_94: That delete-then-send meant that if the subsequent send then
    # failed, every PTB fallback calling q.edit_message_text() was editing a
    # message that no longer existed and failed silently. Now edit_blocks is
    # tried first; only fall back to delete+send if the edit itself fails,
    # and preserve the old message if even that fails so a PTB fallback edit
    # still has something to target.
    if not RICH_AVAILABLE:
        raise RichMessageError("rich_message.py unavailable")
    block_list = list(blocks)
    try:
        return await asyncio.to_thread(edit_blocks, chat_id, message_id, block_list)
    except Exception as exc:
        logger.debug("RICH_PM: rich edit failed (%s), delete+send", str(exc)[:120])
        try:
            await asyncio.to_thread(delete_message, chat_id, message_id)
        except Exception:
            logger.debug("RICH_PM: old message delete skipped")
        return await _send_with_retry(chat_id, block_list)


# FIX_PM_18: Extract the Telegram message_id from a rich API response so
# workflow cleanup can track rich cards just like PTB messages.
def rich_message_id(resp) -> Optional[int]:
    """Extract a Telegram message_id from either a rich_message response dict
    or a plain PTB Message object (returned by rich_send_or/rich_replace_or
    fallbacks), so callers don't each need their own hasattr check."""
    if isinstance(resp, dict):
        inner = resp.get("result", resp)
        if isinstance(inner, dict):
            mid = inner.get("message_id")
            try:
                return int(mid) if mid is not None else None
            except (TypeError, ValueError):
                return None
        return None
    mid = getattr(resp, "message_id", None)
    try:
        return int(mid) if mid is not None else None
    except (TypeError, ValueError):
        return None


async def rich_send_or(chat_id, blocks, fallback):
    # FIX_PM_RICH_6: Every rich send has a PTB fallback and never breaks the bot flow.
    try:
        return await rich_send(chat_id, blocks)
    # FIX_PM_92: include the actual rich failure reason in fallback logs.
    except RichMessageError as exc:
        logger.warning("RICH_PM: rich send failed (%s), using fallback", str(exc)[:180])
    except Exception:
        logger.warning("RICH_PM: rich send crashed, using fallback", exc_info=True)
    return await fallback()


# FIX_PM_92: fallback logging includes the RichMessageError reason.
async def rich_replace_or(chat_id, message_id, blocks, fallback):
    # FIX_PM_RICH_7: Every rich replace has a PTB fallback and never breaks the bot flow.
    try:
        return await rich_replace(chat_id, message_id, blocks)
    # FIX_PM_92: include the actual rich replacement failure reason in fallback logs.
    except RichMessageError as exc:
        logger.warning("RICH_PM: rich edit failed (%s), using fallback", str(exc)[:180])
    except Exception:
        logger.warning("RICH_PM: rich edit crashed, using fallback", exc_info=True)
    return await fallback()
