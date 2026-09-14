"""Pure rich block validation helpers."""
from rich_message import RichMessageError

_VALID_BLOCK_TYPES = {
    "heading", "paragraph", "table", "video", "photo", "buttons",
    "divider", "spacer", "quote", "code", "list", "checklist",
    "details", "spoiler", "markdown", "animation", "audio", "document",
}
_TRANSIENT_MARKERS = (
    "connection reset", "connection aborted", "temporarily unavailable",
    "timed out", "timeout", "bad gateway", "gateway timeout",
    "service unavailable", "too many requests",
)
_STRIPPABLE_BLOCK_TYPES = ("video", "photo", "animation", "audio")

def validate_blocks(blocks) -> list:
    """FIX_PM_104: fail fast on malformed blocks before Telegram."""
    errors = []
    for i, b in enumerate(blocks):
        if not isinstance(b, dict):
            errors.append(f"block[{i}]: not a dict ({type(b).__name__})")
            continue
        t = b.get("type")
        if not isinstance(t, str):
            errors.append(f"block[{i}]: missing/!str type")
            continue
        if t not in _VALID_BLOCK_TYPES:
            errors.append(f"block[{i}]: unknown type {t!r}")
    return errors

def _is_transient(exc) -> bool:
    if isinstance(exc, RichMessageError):
        msg = str(exc).lower()
        if any(m in msg for m in _TRANSIENT_MARKERS):
            return True
        if "http 5" in msg or "http 429" in msg:
            return True
    if isinstance(exc, (ConnectionError, TimeoutError, OSError)):
        return True
    return False
