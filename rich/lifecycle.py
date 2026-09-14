"""Rich message lifecycle and PTB fallback helpers."""
from typing import Optional

from core import logger
from rich_message import RichMessageError
from .transport import rich_send, rich_replace
from .metrics import METRICS

def rich_message_id(resp) -> Optional[int]:
    # FIX_PM_18: Extract Telegram message_id from rich or PTB responses.
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
    # FIX_PM_RICH_6: Every rich send has a PTB fallback.
    try:
        return await rich_send(chat_id, blocks)
    except RichMessageError as exc:
        # FIX_PM_92: include the actual rich failure reason in fallback logs.
        METRICS.record_fallback()
        logger.warning("RICH_PM: rich send failed (%s), using fallback", str(exc)[:180])
    except Exception:
        # FIX_PM_92: fallback logging includes the RichMessageError reason.
        METRICS.record_fallback()
        logger.warning("RICH_PM: rich send crashed, using fallback", exc_info=True)
    return await fallback()

async def rich_replace_or(chat_id, message_id, blocks, fallback):
    # FIX_PM_RICH_7: Every rich replace has a PTB fallback.
    try:
        return await rich_replace(chat_id, message_id, blocks)
    except RichMessageError as exc:
        # FIX_PM_92: include the actual rich failure reason in fallback logs.
        METRICS.record_fallback()
        logger.warning("RICH_PM: rich edit failed (%s), using fallback", str(exc)[:180])
    except Exception:
        METRICS.record_fallback()
        logger.warning("RICH_PM: rich edit crashed, using fallback", exc_info=True)
    return await fallback()

async def tracked_send_or(context, chat_id, blocks, fallback, track_key):
    """FIX_PM_112: track returned message_id in context.user_data."""
    resp = await rich_send_or(chat_id, blocks, fallback)
    mid = rich_message_id(resp)
    if not mid:
        mid = getattr(resp, "message_id", None)
    if mid:
        try:
            context.user_data[track_key] = int(mid)
        except (TypeError, ValueError):
            pass
    return resp

async def tracked_replace_or(context, chat_id, message_id, blocks,
                             fallback, track_key):
    """FIX_PM_112: track returned message_id in context.user_data."""
    resp = await rich_replace_or(chat_id, message_id, blocks, fallback)
    mid = rich_message_id(resp)
    if not mid:
        mid = getattr(resp, "message_id", None)
    if mid:
        try:
            context.user_data[track_key] = int(mid)
        except (TypeError, ValueError):
            pass
    return resp
