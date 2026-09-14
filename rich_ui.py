"""PDF Mitra Pro — Telegram Rich Message glue layer (facade).
FIX_PM_115: public API is preserved 1:1 for backwards compatibility.
Actual implementation lives in the `rich/` package.
"""
from __future__ import annotations
from typing import Optional

from core import logger
# FIX_PM_21: RICH_IMPORT_ERROR is always defined so boot logs can print it.
RICH_IMPORT_ERROR: Optional[str] = None

_PUBLIC = [
    "heading", "paragraph", "compact_table", "button_row", "video",
    "divider", "spacer", "quote", "code", "markdown", "bullet_list",
    "checklist", "photo", "animation", "details", "spoiler", "button_grid",
    "rich_callback_button", "rich_url_button", "rich_send", "rich_replace",
    "rich_send_or", "rich_replace_or", "rich_message_id", "send_blocks",
    "edit_blocks", "delete_message", "rich_metrics_report",
    "get_block_type_counts", "success_card", "error_card", "progress_card",
    "stats_card", "info_card", "confirm_card", "wizard_card", "section_card",
    "tracked_send_or", "tracked_replace_or", "blocks_to_plain_text", "validate_blocks",
]

try:
    from rich_message import RichMessageError
except Exception as _rm_exc:
    class RichMessageError(Exception):
        pass
    RICH_IMPORT_ERROR = str(_rm_exc)

try:
    from rich import (
        heading, paragraph, compact_table, button_row, video,
        divider, spacer, quote, code, markdown, bullet_list, checklist,
        photo, animation, details, spoiler, button_grid,
        rich_callback_button, rich_url_button, rich_send, rich_replace,
        rich_send_or, rich_replace_or, rich_message_id, send_blocks,
        edit_blocks, delete_message, rich_metrics_report,
        get_block_type_counts, success_card, error_card, progress_card,
        stats_card, info_card, confirm_card, wizard_card, section_card,
        tracked_send_or, tracked_replace_or, blocks_to_plain_text,
        validate_blocks,
    )
    RICH_AVAILABLE = True
except Exception as _imp_exc:
    # FIX_PM_RICH_1: Keep the bot bootable when rich package or its dependency is unavailable.
    RICH_IMPORT_ERROR = str(_imp_exc)
    RICH_AVAILABLE = False
    def _missing(*_a, **_k):
        raise RichMessageError(f"rich package unavailable: {RICH_IMPORT_ERROR}")
    for _name in _PUBLIC:
        globals()[_name] = _missing

__all__ = [
    "RICH_AVAILABLE", "RICH_IMPORT_ERROR", "RichMessageError",
    "heading", "paragraph", "compact_table", "button_row", "video",
    "divider", "spacer", "quote", "code", "markdown",
    "bullet_list", "checklist", "photo", "animation", "details", "spoiler",
    "button_grid", "rich_callback_button", "rich_url_button",
    "rich_send", "rich_replace", "rich_send_or", "rich_replace_or",
    "rich_message_id", "send_blocks", "edit_blocks", "delete_message",
    "rich_metrics_report", "get_block_type_counts", "success_card",
    "error_card", "progress_card", "stats_card", "info_card", "confirm_card",
    "wizard_card", "section_card", "tracked_send_or", "tracked_replace_or",
    "blocks_to_plain_text",
]
