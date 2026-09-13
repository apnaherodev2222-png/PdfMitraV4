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


async def rich_send(chat_id, blocks):
    # FIX_PM_RICH_4: Rich HTTP is blocking; run it off the PTB event loop.
    if not RICH_AVAILABLE:
        raise RichMessageError("rich_message.py unavailable")
    return await asyncio.to_thread(send_blocks, chat_id, list(blocks))


async def rich_replace(chat_id, message_id, blocks):
    # FIX_PM_RICH_5: Delete-then-send avoids unreliable rich editMessageText behavior.
    if not RICH_AVAILABLE:
        raise RichMessageError("rich_message.py unavailable")
    try:
        await asyncio.to_thread(delete_message, chat_id, message_id)
    except RichMessageError:
        logger.debug("RICH_PM: old message delete skipped")
    return await asyncio.to_thread(send_blocks, chat_id, list(blocks))


# FIX_PM_18: Extract the Telegram message_id from a rich API response so
# workflow cleanup can track rich cards just like PTB messages.
def rich_message_id(resp) -> Optional[int]:
    """Extract a Telegram message_id from a rich_message response dict."""
    if not isinstance(resp, dict):
        return None
    inner = resp.get("result", resp)
    if isinstance(inner, dict):
        mid = inner.get("message_id")
        try:
            return int(mid) if mid is not None else None
        except (TypeError, ValueError):
            return None
    return None


async def rich_send_or(chat_id, blocks, fallback):
    # FIX_PM_RICH_6: Every rich send has a PTB fallback and never breaks the bot flow.
    try:
        return await rich_send(chat_id, blocks)
    except RichMessageError:
        logger.warning("RICH_PM: rich send failed, using fallback", exc_info=True)
    except Exception:
        logger.warning("RICH_PM: rich send crashed, using fallback", exc_info=True)
    return await fallback()


async def rich_replace_or(chat_id, message_id, blocks, fallback):
    # FIX_PM_RICH_7: Every rich replace has a PTB fallback and never breaks the bot flow.
    try:
        return await rich_replace(chat_id, message_id, blocks)
    except RichMessageError:
        logger.warning("RICH_PM: rich edit failed, using fallback", exc_info=True)
    except Exception:
        logger.warning("RICH_PM: rich edit crashed, using fallback", exc_info=True)
    return await fallback()
