"""Preset rich card builders."""
from .blocks import (
    heading, paragraph, compact_table, button_row, divider, bullet_list,
    rich_callback_button, rich_url_button,
)

def _normalize_buttons(buttons):
    """Accept button-row blocks, tuple buttons, or lists of tuples.
    FIX_PM_111: builders accept the simple tuple form so handler code stays readable.
    """
    if not buttons:
        return []
    # FIX_PM_114: allow a single (label, data, style) tuple directly.
    if (isinstance(buttons, tuple)
            and len(buttons) >= 2
            and isinstance(buttons[0], str)):
        buttons = [buttons]
    out = []
    for entry in buttons:
        if isinstance(entry, dict) and entry.get("type") == "buttons":
            out.append(entry)
            continue
        if isinstance(entry, (list, tuple)):
            row = []
            if len(entry) >= 2 and not isinstance(entry[0], (dict, list, tuple)):
                label, data = entry[0], entry[1]
                style = entry[2] if len(entry) > 2 else "primary"
                row.append(rich_callback_button(label, data, style))
            else:
                for item in entry:
                    if isinstance(item, dict):
                        row.append(item)
                    elif isinstance(item, (list, tuple)) and len(item) >= 2:
                        label, data = item[0], item[1]
                        style = item[2] if len(item) > 2 else "primary"
                        row.append(rich_callback_button(label, data, style))
            if row:
                out.append(button_row(row))
    return out

def success_card(title, body, buttons=None, footer=None):
    blocks = [heading(f"✅ {title}"), paragraph(str(body))]
    if footer:
        blocks.append(paragraph(str(footer)))
    if buttons:
        blocks.extend(_normalize_buttons(buttons))
    return blocks

def error_card(title, body, hint=None, buttons=None, retry=None):
    blocks = [heading(f"❌ {title}"), paragraph(str(body))]
    if hint:
        blocks.append(paragraph(f"💡 {hint}"))
    if retry:
        label, data, style = retry
        blocks.append(button_row([rich_callback_button(label, data, style or "primary")]))
    if buttons:
        blocks.extend(_normalize_buttons(buttons))
    return blocks

def progress_card(title, rows, buttons=None):
    blocks = [heading(f"⏳ {title}"), compact_table(["Field", "Value"], rows)]
    if buttons:
        blocks.extend(_normalize_buttons(buttons))
    return blocks

def stats_card(title, rows, buttons=None):
    blocks = [heading(title), compact_table(["Metric", "Value"], rows)]
    if buttons:
        blocks.extend(_normalize_buttons(buttons))
    return blocks

def info_card(title, body, bullets=None, buttons=None):
    blocks = [heading(title), paragraph(str(body))]
    if bullets:
        blocks.append(bullet_list(bullets))
    if buttons:
        blocks.extend(_normalize_buttons(buttons))
    return blocks

def confirm_card(title, body, yes_label, yes_data,
                 no_label="❌ Cancel", no_data="task_cancel"):
    return [
        heading(title),
        paragraph(str(body)),
        button_row([
            rich_callback_button(yes_label, yes_data, "success"),
            rich_callback_button(no_label, no_data, "danger"),
        ]),
    ]

def wizard_card(step, total, title, body, buttons=None, progress=None):
    blocks = [heading(title), paragraph(f"Step {step}/{total} · {body}")]
    if progress is not None:
        blocks.append(compact_table(["Field", "Value"], [
            ["Progress", f"{step}/{total}"],
            ["Status", str(progress)],
        ]))
    if buttons:
        blocks.extend(_normalize_buttons(buttons))
    return blocks

def section_card(title, description, markup_or_buttons, tail=None):
    blocks = [heading(title), divider(), paragraph(str(description))]
    if tail:
        blocks.append(paragraph(str(tail)))
    if markup_or_buttons is not None:
        if hasattr(markup_or_buttons, "inline_keyboard"):
            for _row in markup_or_buttons.inline_keyboard:
                _row_btns = []
                for _b in _row:
                    if getattr(_b, "url", None):
                        _row_btns.append(rich_url_button(_b.text, _b.url, "primary"))
                    else:
                        _row_btns.append(rich_callback_button(
                            _b.text, _b.callback_data or "menu", "primary"
                        ))
                if _row_btns:
                    blocks.append(button_row(_row_btns))
        else:
            blocks.extend(_normalize_buttons(markup_or_buttons))
    return blocks
