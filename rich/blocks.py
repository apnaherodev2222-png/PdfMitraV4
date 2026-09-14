"""Pure rich-message block constructors."""
from typing import Any, Dict, List, Sequence

def heading(text: str, size: int = 2) -> Dict[str, Any]:
    return {"type": "heading", "text": str(text), "size": int(size)}

def paragraph(text: str) -> Dict[str, Any]:
    return {"type": "paragraph", "text": str(text)}

def video(url: str) -> Dict[str, Any]:
    return {"type": "video", "video": {"type": "video", "media": str(url)}}

def compact_table(header_row: Sequence[str], data_rows: Sequence[Sequence[str]]) -> Dict[str, Any]:
    def cell(text: Any, is_header: bool = False) -> Dict[str, Any]:
        item: Dict[str, Any] = {"text": str(text), "align": "left", "valign": "middle"}
        if is_header:
            item["is_header"] = True
        return item
    cells: List[List[Dict[str, Any]]] = [[cell(value, True) for value in header_row]]
    cells.extend([[cell(value) for value in row] for row in data_rows])
    return {"type": "table", "is_compact": True, "cells": cells}

def button_row(buttons: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """Build one in-message button row."""
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
    return {"type": "divider"}

def spacer(height: int = 8) -> Dict[str, Any]:
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
    return {"type": "markdown", "text": str(text)}

def bullet_list(items: Sequence[str]) -> Dict[str, Any]:
    return {"type": "list", "items": [str(i) for i in items]}

def checklist(items: Sequence[Sequence[Any]]) -> Dict[str, Any]:
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
    block = {"type": "animation", "animation": {"type": "animation", "media": str(url)}
    }
    if caption:
        block["caption"] = str(caption)
    return block

def details(summary: str, body: str) -> Dict[str, Any]:
    return {"type": "details", "summary": str(summary), "text": str(body)}

def spoiler(text: str) -> Dict[str, Any]:
    return {"type": "spoiler", "text": str(text)}

def button_grid(rows: Sequence[Sequence[Dict[str, Any]]], widths: Sequence[int] = None) -> Dict[str, Any]:
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

def _validate_callback_data(data: str) -> None:
    """FIX_PM_105: Telegram's 64-byte callback_data limit."""
    if data is None:
        return
    if len(str(data).encode("utf-8")) > 64:
        raise ValueError(f"callback_data exceeds 64 bytes: {str(data)[:40]!r}…")

def rich_callback_button(text, callback_data, style="primary"):
    # FIX_PM_RICH_2: Centralize rich callback button construction without changing callback_data values.
    _validate_callback_data(callback_data)
    return {"text": text, "callback_data": callback_data, "style": style}

def rich_url_button(text, url, style="primary"):
    # FIX_PM_RICH_3: Centralize rich URL button construction for keyboards that expose links.
    return {"text": text, "url": url, "style": style}

__all__ = [
    "heading", "paragraph", "video", "compact_table", "button_row", "divider",
    "spacer", "quote", "code", "markdown", "bullet_list", "checklist",
    "photo", "animation", "details", "spoiler", "button_grid",
    "rich_callback_button", "rich_url_button",
]
