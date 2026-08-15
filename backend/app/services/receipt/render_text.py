"""Plain-text renderer — the reference output.

Its real job is not printing. It is that a receipt can be read in a test
assertion, a log line, or a support conversation without a printer or a
browser, which makes every layout bug visible in the cheapest possible
place. It is also what the ESC/POS renderer's line-fitting is built on, so
the two stay consistent by construction.
"""
import textwrap

from app.services.receipt.document import Align, Line, LineKind, ReceiptDocument


def _align(text: str, width: int, align: Align) -> str:
    text = text[:width]
    if align == Align.CENTER:
        return text.center(width)
    if align == Align.RIGHT:
        return text.rjust(width)
    return text


def _pair(label: str, value: str, width: int) -> str:
    """Label left, value hard right, spaces between.

    When the two cannot fit on one line the value wins its space and the
    label is truncated — an amount that silently loses a digit is far worse
    than a shortened description of it.
    """
    value = value[:width]
    room = width - len(value) - 1
    if room < 1:
        return value.rjust(width)
    label = label[:room]
    return label + " " * (width - len(label) - len(value)) + value


def _item(line: Line, width: int) -> list[str]:
    """Name on the left, amount on the right, quantity x rate underneath.

    The name wraps rather than truncating: a guest checking their bill needs
    to recognise the dish, and "Paneer Butter Mas" helps nobody.
    """
    amount = line.value
    name_width = max(width - len(amount) - 1, 10)
    wrapped = textwrap.wrap(line.text, name_width) or [""]

    out = [wrapped[0] + " " * (width - len(wrapped[0]) - len(amount)) + amount]
    out.extend(wrapped[1:])
    if line.quantity or line.rate:
        detail = f"  {line.quantity} x {line.rate}".rstrip()
        out.append(detail[:width])
    return out


def render_text(doc: ReceiptDocument) -> str:
    width = doc.width
    out: list[str] = []

    for line in doc.lines:
        if line.kind == LineKind.DIVIDER:
            out.append("-" * width)
        elif line.kind == LineKind.SPACER:
            out.append("")
        elif line.kind == LineKind.PAIR:
            out.append(_pair(line.text, line.value, width))
        elif line.kind == LineKind.ITEM:
            out.extend(_item(line, width))
        else:
            body = f"  {line.text}" if line.sub else line.text
            # Long free text wraps instead of being cut off — the same
            # reasoning as item names.
            for chunk in (textwrap.wrap(body, width) or [""]):
                out.append(_align(chunk, width, line.align))

    return "\n".join(out)
