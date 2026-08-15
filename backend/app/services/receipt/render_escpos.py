"""ESC/POS renderer — bytes for a thermal printer.

**Verification status: not tested against real hardware.** No thermal printer
was available while this was written, so every command below is asserted at
the byte level in tests against the ESC/POS command set as documented by
Epson, and nothing here has met real paper. Before trusting it in
production, print one bill and one kitchen ticket on the actual machine and
confirm: the cut happens in the right place, the drawer kick fires, and the
characters-per-line matches the paper width configured here.

That caveat is the reason browser printing exists alongside this — a pilot
can run on HTML output while this half stays unproven.

Only the widely-supported subset is used. ESC/POS is a family of dialects
rather than one standard, and the commands here (initialise, alignment,
emphasis, double-height, feed, partial cut, drawer pulse) are the ones
essentially every printer implements. Barcode and image commands, which vary
much more between manufacturers, are deliberately left out.
"""
from app.services.receipt.document import Align, Emphasis, ReceiptDocument
from app.services.receipt.render_text import _item, _pair
from app.services.receipt.document import LineKind

ESC = b"\x1b"
GS = b"\x1d"

INIT = ESC + b"@"                    # ESC @  — reset to a known state
ALIGN_LEFT = ESC + b"a\x00"
ALIGN_CENTER = ESC + b"a\x01"
ALIGN_RIGHT = ESC + b"a\x02"
BOLD_ON = ESC + b"E\x01"
BOLD_OFF = ESC + b"E\x00"
# GS ! n — n encodes width in the high nibble and height in the low nibble.
SIZE_NORMAL = GS + b"!\x00"
SIZE_DOUBLE_HEIGHT = GS + b"!\x01"
FEED_AND_CUT = GS + b"V\x42\x03"     # GS V B n — partial cut after feeding n
# ESC p m t1 t2 — pulse the drawer connected to pin 2.
DRAWER_KICK = ESC + b"p\x00\x19\xfa"


def _emphasis_bytes(emphasis: Emphasis) -> tuple[bytes, bytes]:
    """Returns (prefix, suffix) so every line restores the default state.

    Leaving a printer in bold or double-height leaks into whatever prints
    next, which on a busy counter is the following guest's bill.
    """
    if emphasis == Emphasis.BOLD:
        return BOLD_ON, BOLD_OFF
    if emphasis == Emphasis.LARGE:
        return SIZE_DOUBLE_HEIGHT, SIZE_NORMAL
    if emphasis == Emphasis.BOLD_LARGE:
        return BOLD_ON + SIZE_DOUBLE_HEIGHT, SIZE_NORMAL + BOLD_OFF
    return b"", b""


_ALIGNMENT = {
    Align.LEFT: ALIGN_LEFT,
    Align.CENTER: ALIGN_CENTER,
    Align.RIGHT: ALIGN_RIGHT,
}


def render_escpos(doc: ReceiptDocument, *, encoding: str = "cp437") -> bytes:
    """Bytes ready to write to a printer.

    cp437 is the default character set on virtually every thermal printer.
    Characters outside it — the rupee sign, and any Devanagari in a dish
    name — are replaced rather than raising, because a bill that prints with
    "Rs" where it wanted "₹" is still a usable bill, whereas one that fails
    to print at all stops the counter. Devanagari on thermal paper needs a
    printer with the font loaded and a code page selected for it; that is a
    per-model decision this renderer cannot make.
    """
    out = bytearray()
    out += INIT

    width = doc.width
    for line in doc.lines:
        if line.kind == LineKind.DIVIDER:
            body = "-" * width
            align = Align.LEFT
            emphasis = Emphasis.NORMAL
        elif line.kind == LineKind.SPACER:
            out += b"\n"
            continue
        elif line.kind == LineKind.PAIR:
            body = _pair(line.text, line.value, width)
            align = Align.LEFT
            emphasis = line.emphasis
        elif line.kind == LineKind.ITEM:
            body = "\n".join(_item(line, width))
            align = Align.LEFT
            emphasis = Emphasis.NORMAL
        else:
            body = f"  {line.text}" if line.sub else line.text
            align = line.align
            emphasis = line.emphasis

        prefix, suffix = _emphasis_bytes(emphasis)
        out += _ALIGNMENT[align]
        out += prefix
        out += body.encode(encoding, errors="replace")
        out += suffix
        out += b"\n"

    out += ALIGN_LEFT
    if doc.open_cash_drawer:
        # Before the cut, so the drawer opens as the paper is delivered
        # rather than a beat later.
        out += DRAWER_KICK
    out += FEED_AND_CUT
    return bytes(out)
