"""PDF Mitra Pro rich-message package public facade."""
from rich_message import (
    RichMessageError,
    send_blocks, edit_blocks, delete_message,
    blocks_to_plain_text,
)
from .blocks import (
    heading, paragraph, video, compact_table, button_row,
    divider, spacer, quote, code, markdown,
    bullet_list, checklist, photo, animation, details, spoiler,
    button_grid, rich_callback_button, rich_url_button,
)
from .metrics import (
    RichMetrics, METRICS, rich_metrics_report, get_block_type_counts,
)
from .validator import validate_blocks
from .transport import rich_send, rich_replace
from .builders import (
    success_card, error_card, progress_card, stats_card,
    info_card, confirm_card, wizard_card, section_card,
)
from .lifecycle import (
    rich_message_id, rich_send_or, rich_replace_or,
    tracked_send_or, tracked_replace_or,
)

__all__ = [
    "RichMessageError",
    "heading", "paragraph", "compact_table", "button_row", "video",
    "divider", "spacer", "quote", "code", "markdown",
    "bullet_list", "checklist", "photo", "animation", "details", "spoiler",
    "button_grid",
    "rich_callback_button", "rich_url_button",
    "rich_send", "rich_replace",
    "rich_send_or", "rich_replace_or", "rich_message_id",
    "send_blocks", "edit_blocks", "delete_message",
    "rich_metrics_report", "get_block_type_counts",
    "success_card", "error_card", "progress_card", "stats_card",
    "info_card", "confirm_card", "wizard_card", "section_card",
    "tracked_send_or", "tracked_replace_or", "blocks_to_plain_text",
]
