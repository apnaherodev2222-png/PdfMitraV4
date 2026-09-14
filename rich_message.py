"""Telegram Bot API 10.3 Rich Message helpers.

All HTTP failures are normalized to RichMessageError so callers can safely
fall back to the existing python-telegram-bot rendering path.
"""
from __future__ import annotations

import os
import logging
from typing import Any, Dict, List, Sequence

import requests

try:
    from config import RICH_HTTP_TIMEOUT as _TIMEOUT
except Exception:
    _TIMEOUT = 20

try:
    from config import RICH_DEBUG as _RICH_DEBUG
except Exception:
    _RICH_DEBUG = False

_SESSION = requests.Session()
_SESSION.headers.update({"User-Agent": "PdfMitra-Rich/1.0"})
_adapter = requests.adapters.HTTPAdapter(
    pool_connections=8, pool_maxsize=16, max_retries=0,
)
_SESSION.mount("https://", _adapter)
_SESSION.mount("http://", _adapter)
# FIX_PM_107: urllib3's PoolManager is thread-safe and we never mutate
# cookies, so no external lock is needed. The old external session lock turned
# rich_ui's Semaphore(8) into a de-facto Semaphore(1).

logger = logging.getLogger("pdf_bot")


class RichMessageError(Exception):
    """Raised when Telegram rejects or cannot receive a rich-message call."""


TELEGRAM_API = os.getenv("TELEGRAM_API", "https://api.telegram.org")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

def _redact_url(url: str) -> str:
    """Hide the bot token before a debug URL is emitted to logs."""
    try:
        marker = "/bot"
        pos = url.find(marker)
        if pos < 0:
            return url
        slash = url.find("/", pos + len(marker))
        if slash < 0:
            return url[:pos + len(marker)] + "<REDACTED>"
        return url[:pos + len(marker)] + "<REDACTED>" + url[slash:]
    except Exception:
        return "<REDACTED_URL>"


def send_blocks_raw(
    chat_id: int,
    blocks: Sequence[Dict[str, Any]],
    token: str = None,
    reply_to_message_id: int = None,
    disable_notification: bool = False,
) -> Dict[str, Any]:
    """Return the complete Telegram JSON envelope for a rich send."""
    payload = {
        "chat_id": chat_id,
        "rich_message": {"blocks": list(blocks)},
    }
    if reply_to_message_id:
        payload["reply_to_message_id"] = int(reply_to_message_id)
    if disable_notification:
        payload["disable_notification"] = True
    return _call_api_raw("sendRichMessage", payload, token=token)


def edit_blocks_raw(chat_id: int, message_id: int, blocks: Sequence[Dict[str, Any]], token: str = None) -> Dict[str, Any]:
    """Return the complete Telegram JSON envelope for a rich edit."""
    return _call_api_raw(
        "editMessageText",
        {
            "chat_id": chat_id,
            "message_id": message_id,
            "rich_message": {"blocks": list(blocks)},
        },
        token=token,
    )


def _call_api_raw(method: str, payload: Dict[str, Any], token: str = None) -> Dict[str, Any]:
    """POST a Bot API request and return its complete JSON envelope."""
    # FIX_RICH_1: Allow approval_bot.py to route rich API calls through its own token.
    tk = token or BOT_TOKEN
    if not tk:
        raise RichMessageError("BOT_TOKEN is not configured")
    url = f"{TELEGRAM_API.rstrip('/')}/bot{tk}/{method}"
    if _RICH_DEBUG:
        logger.debug("RICH_PM: POST %s payload=%r", _redact_url(url), payload)
    try:
        response = _SESSION.post(url, json=payload, timeout=_TIMEOUT)
        try:
            data = response.json()
        except Exception as exc:
            raise RichMessageError(
                f"{method} returned invalid JSON (HTTP {response.status_code}): {exc}"
            ) from exc
    except RichMessageError:
        raise
    except requests.RequestException as exc:
        raise RichMessageError(f"{method} request failed: {type(exc).__name__}: {exc}") from exc
    except Exception as exc:
        raise RichMessageError(f"{method} request failed: {type(exc).__name__}: {exc}") from exc

    if _RICH_DEBUG:
        logger.debug("RICH_PM: response HTTP %s JSON=%r", response.status_code, data)
    if not isinstance(data, dict) or not data.get("ok"):
        description = data.get("description") if isinstance(data, dict) else None
        raise RichMessageError(
            f"{description or f'{method} failed'} (HTTP {response.status_code})"
        )
    return data


def _call_api(method: str, payload: Dict[str, Any], token: str = None) -> Dict[str, Any]:
    """POST a Bot API request using an optional per-call bot token."""
    data = _call_api_raw(method, payload, token=token)
    result = data.get("result")
    return result if isinstance(result, dict) else {"result": result}


def heading(text: str, size: int = 2) -> Dict[str, Any]:
    return {"type": "heading", "text": str(text), "size": int(size)}


def paragraph(text: str) -> Dict[str, Any]:
    return {"type": "paragraph", "text": str(text)}


def video(url: str) -> Dict[str, Any]:
    return {"type": "video", "video": {"type": "video", "media": str(url)}}


def compact_table(header_row: Sequence[str], data_rows: Sequence[Sequence[str]]) -> Dict[str, Any]:
    def cell(text: Any, is_header: bool = False) -> Dict[str, Any]:
        item: Dict[str, Any] = {
            "text": str(text),
            "align": "left",
            "valign": "middle",
        }
        if is_header:
            item["is_header"] = True
        return item

    cells: List[List[Dict[str, Any]]] = [[cell(value, True) for value in header_row]]
    cells.extend([[cell(value) for value in row] for row in data_rows])
    return {"type": "table", "is_compact": True, "cells": cells}


def button_row(buttons: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """Build one in-message button row.

    Supported button fields are text + callback_data or url, and optional style.
    """
    out: List[Dict[str, Any]] = []
    for button in buttons:
        item: Dict[str, Any] = {"text": str(button["text"])}
        if button.get("callback_data") is not None:
            item["callback_data"] = str(button["callback_data"])
        elif button.get("url") is not None:
            item["url"] = str(button["url"])
        if button.get("style") is not None:
            item["style"] = str(button["style"])
        out.append(item)
    return {"type": "buttons", "buttons": out}


def divider() -> Dict[str, Any]:
    """Full-width horizontal rule."""
    return {"type": "divider"}


def spacer(height: int = 8) -> Dict[str, Any]:
    """Vertical whitespace, height in abstract units."""
    return {"type": "spacer", "height": int(height)}


def quote(text: str, author: str = None) -> Dict[str, Any]:
    block = {"type": "quote", "text": str(text)}
    if author:
        block["author"] = str(author)
    return block


def code(text: str, language: str = None) -> Dict[str, Any]:
    block = {"type": "code", "text": str(text)}
    if language:
        block["language"] = str(language)
    return block


def markdown(text: str) -> Dict[str, Any]:
    """Explicitly-marked markdown (for cases where paragraph does not
    interpret markdown syntax)."""
    return {"type": "markdown", "text": str(text)}


def bullet_list(items: Sequence[str]) -> Dict[str, Any]:
    return {"type": "list", "items": [str(i) for i in items]}


def checklist(items: Sequence[Sequence[Any]]) -> Dict[str, Any]:
    """items: sequence of (text, checked_bool) tuples/lists."""
    out = []
    for item in items:
        text, checked = item[0], bool(item[1])
        out.append({"text": str(text), "checked": checked})
    return {"type": "checklist", "items": out}


def photo(url: str, caption: str = None) -> Dict[str, Any]:
    block = {"type": "photo", "photo": {"type": "photo", "media": str(url)}}
    if caption:
        block["caption"] = str(caption)
    return block


def animation(url: str, caption: str = None) -> Dict[str, Any]:
    block = {
        "type": "animation",
        "animation": {"type": "animation", "media": str(url)},
    }
    if caption:
        block["caption"] = str(caption)
    return block


def details(summary: str, body: str) -> Dict[str, Any]:
    return {
        "type": "details",
        "summary": str(summary),
        "text": str(body),
    }


def spoiler(text: str) -> Dict[str, Any]:
    return {"type": "spoiler", "text": str(text)}


def button_grid(
    rows: Sequence[Sequence[Dict[str, Any]]],
    widths: Sequence[int] = None,
) -> Dict[str, Any]:
    """Multi-row button grid flattened into one `buttons` block.
    Telegram button blocks are flat lists; row boundaries are conveyed
    by widths. If the API supports per-row nesting, prefer emitting
    one button_row() per row. Kept for callers that want a
    single combined block.
    """
    flat = []
    for row in rows:
        for btn in row:
            item = {"text": str(btn["text"])}
            if btn.get("callback_data") is not None:
                item["callback_data"] = str(btn["callback_data"])
            elif btn.get("url") is not None:
                item["url"] = str(btn["url"])
            if btn.get("style") is not None:
                item["style"] = str(btn["style"])
            flat.append(item)
    block = {"type": "buttons", "buttons": flat}
    if widths:
        block["widths"] = [int(w) for w in widths]
    return block


def send_blocks(
    chat_id: int,
    blocks: Sequence[Dict[str, Any]],
    token: str = None,
    reply_to_message_id: int = None,
    disable_notification: bool = False,
) -> Dict[str, Any]:
    # FIX_RICH_1: token is optional so existing hosting-bot callers remain backwards compatible.
    data = send_blocks_raw(
        chat_id,
        blocks,
        token=token,
        reply_to_message_id=reply_to_message_id,
        disable_notification=disable_notification,
    )
    result = data.get("result")
    return result if isinstance(result, dict) else {"result": result}



def blocks_to_plain_text(blocks: Sequence[Dict[str, Any]]) -> str:
    """Render rich blocks to a plain Markdown-ish string for the
    standard editMessageText path. Best-effort, no exceptions.
    FIX_PM_110: used only as a fallback when the rich edit endpoint
    rejects a rich_message payload.
    """
    parts = []
    for b in blocks or []:
        if not isinstance(b, dict):
            continue
        t = b.get("type")
        if t == "heading":
            parts.append(f"*{b.get('text', '')}*")
        elif t == "paragraph":
            parts.append(str(b.get("text", "")))
        elif t == "quote":
            parts.append(f"> {b.get('text', '')}")
        elif t == "code":
            parts.append(f"```\n{b.get('text', '')}\n```")
        elif t == "markdown":
            parts.append(str(b.get("text", "")))
        elif t == "list":
            for item in b.get("items", []) or []:
                parts.append(f"• {item}")
        elif t == "checklist":
            for item in b.get("items", []) or []:
                mark = "☑" if item.get("checked") else "☐"
                parts.append(f"{mark} {item.get('text', '')}")
        elif t == "divider":
            parts.append("―" * 12)
        elif t == "spacer":
            parts.append("")
        elif t == "table":
            for row in b.get("cells", []) or []:
                line = " | ".join(
                    str(c.get("text", "")) for c in row if isinstance(c, dict)
                )
                if line.strip():
                    parts.append(line)
        elif t == "details":
            parts.append(f"▸ {b.get('summary', '')}")
            parts.append(str(b.get("text", "")))
        elif t == "spoiler":
            parts.append("(spoiler)")
        elif t == "video":
            parts.append("🎬 (video)")
        elif t == "photo":
            parts.append("🖼️ (photo)")
        elif t == "animation":
            parts.append("🎞️ (animation)")
        elif t == "buttons":
            continue
        else:
            if "text" in b:
                parts.append(str(b["text"]))
    return "\n".join(p for p in parts if p is not None).strip()


def blocks_to_inline_keyboard(blocks):
    """Extract a standard Telegram inline_keyboard from rich block payload.
    FIX_PM_113: ensures plain-edit fallback still updates buttons so callers
    never see stale keyboards after a plain edit.
    """
    rows = []
    for b in blocks or []:
        if not isinstance(b, dict) or b.get("type") != "buttons":
            continue
        row = []
        for btn in b.get("buttons", []) or []:
            if not isinstance(btn, dict):
                continue
            item = {"text": str(btn.get("text", ""))}
            if btn.get("callback_data") is not None:
                item["callback_data"] = str(btn["callback_data"])
            elif btn.get("url") is not None:
                item["url"] = str(btn["url"])
            row.append(item)
        if row:
            rows.append(row)
    return {"inline_keyboard": rows} if rows else None


def edit_blocks_plain(
    chat_id: int,
    message_id: int,
    blocks: Sequence[Dict[str, Any]],
    reply_markup: Dict[str, Any] = None,
    token: str = None,
) -> Dict[str, Any]:
    """Standard editMessageText with plain text + optional reply_markup.
    FIX_PM_110: fallback path when the rich payload is rejected.
    """
    payload = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": blocks_to_plain_text(blocks) or "(updated)",
        "parse_mode": "Markdown",
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    data = _call_api_raw("editMessageText", payload, token=token)
    result = data.get("result")
    return result if isinstance(result, dict) else {"result": result}

def edit_blocks(chat_id: int, message_id: int, blocks: Sequence[Dict[str, Any]], token: str = None) -> Dict[str, Any]:
    # FIX_RICH_1: token is optional so existing hosting-bot callers keep using BOT_TOKEN.
    data = edit_blocks_raw(chat_id, message_id, blocks, token=token)
    result = data.get("result")
    return result if isinstance(result, dict) else {"result": result}


# FIX_RICH_27: delete helper for replacing rich cards instead of unreliable rich edits.
def delete_message(chat_id: int, message_id: int, token: str = None) -> Dict[str, Any]:
    """Delete a message used by the rich-edit replace flow."""
    return _call_api(
        "deleteMessage",
        {"chat_id": chat_id, "message_id": message_id},
        token=token,
    )


__all__ = [
    "RichMessageError", "heading", "paragraph", "compact_table", "button_row",
    "video", "divider", "spacer", "quote", "code", "markdown",
    "bullet_list", "checklist", "photo", "animation", "details", "spoiler",
    "button_grid", "blocks_to_plain_text", "blocks_to_inline_keyboard", "send_blocks_raw", "send_blocks",
    "edit_blocks_raw", "edit_blocks_plain", "edit_blocks", "delete_message",
]
