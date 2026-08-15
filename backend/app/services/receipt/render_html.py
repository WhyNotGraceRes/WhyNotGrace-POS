"""HTML renderer — for the browser's print dialog.

Styled to 80mm so what comes out of an ordinary printer looks like a till
receipt rather than a web page on A4. `@page { size: 80mm auto }` is what
makes a browser use roll-paper geometry; printers that cannot honour it fall
back to their default sheet, which still prints correctly, just with wide
margins.

The document is fully self-contained — inline CSS, no external anything —
because it is injected into a hidden frame on a counter machine whose
internet may well be down.
"""
from html import escape

from app.services.receipt.document import Align, Emphasis, LineKind, ReceiptDocument

_ALIGN_CSS = {Align.LEFT: "left", Align.CENTER: "center", Align.RIGHT: "right"}

_STYLE = """
:root { color-scheme: light; }
* { box-sizing: border-box; }
body {
  margin: 0; padding: 4mm;
  font-family: "Menlo", "Consolas", "Courier New", monospace;
  font-size: 11px; line-height: 1.35; color: #000; background: #fff;
  width: 80mm;
}
.r-line { white-space: pre-wrap; word-break: break-word; }
.r-bold { font-weight: 700; }
.r-large { font-size: 15px; line-height: 1.25; }
.r-bold.r-large { font-weight: 700; }
.r-sub { padding-left: 8px; color: #333; font-size: 10px; }
.r-divider { border-top: 1px dashed #000; margin: 3px 0; }
.r-spacer { height: 6px; }
.r-pair, .r-item-head { display: flex; justify-content: space-between; gap: 8px; }
.r-pair > span:last-child, .r-item-head > span:last-child { white-space: nowrap; }
.r-item-detail { padding-left: 8px; color: #333; font-size: 10px; }
@page { size: 80mm auto; margin: 0; }
@media print {
  body { padding: 2mm; width: auto; }
  /* Nothing on a receipt should be split across two pieces of paper. */
  .r-line, .r-pair, .r-item { break-inside: avoid; }
}
"""


def _classes(emphasis: Emphasis, *extra: str) -> str:
    names = list(extra)
    if emphasis in (Emphasis.BOLD, Emphasis.BOLD_LARGE):
        names.append("r-bold")
    if emphasis in (Emphasis.LARGE, Emphasis.BOLD_LARGE):
        names.append("r-large")
    return " ".join(names)


def render_html(doc: ReceiptDocument) -> str:
    parts: list[str] = []

    for line in doc.lines:
        if line.kind == LineKind.DIVIDER:
            parts.append('<div class="r-divider"></div>')
        elif line.kind == LineKind.SPACER:
            parts.append('<div class="r-spacer"></div>')
        elif line.kind == LineKind.PAIR:
            parts.append(
                f'<div class="{_classes(line.emphasis, "r-pair")}">'
                f"<span>{escape(line.text)}</span><span>{escape(line.value)}</span></div>"
            )
        elif line.kind == LineKind.ITEM:
            detail = ""
            if line.quantity or line.rate:
                detail = (
                    f'<div class="r-item-detail">{escape(line.quantity)} &times; '
                    f"{escape(line.rate)}</div>"
                )
            parts.append(
                '<div class="r-item">'
                f'<div class="r-item-head"><span>{escape(line.text)}</span>'
                f"<span>{escape(line.value)}</span></div>{detail}</div>"
            )
        else:
            style = f' style="text-align:{_ALIGN_CSS[line.align]}"' if line.align != Align.LEFT else ""
            klass = _classes(line.emphasis, "r-line", *(["r-sub"] if line.sub else []))
            parts.append(f'<div class="{klass}"{style}>{escape(line.text)}</div>')

    body = "\n".join(parts)
    return (
        "<!DOCTYPE html><html><head><meta charset=\"utf-8\">"
        f"<title>{escape(doc.title)}</title><style>{_STYLE}</style></head>"
        f"<body>{body}</body></html>"
    )
