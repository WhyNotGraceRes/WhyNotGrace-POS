"""The canonical receipt document.

One structure, several outputs. A receipt has to reach a browser's print
dialog, a thermal printer's byte stream, and (later) a PDF for WhatsApp —
and the layout decisions are the same in all three: what is centred, what is
emphasised, where the divider goes, how an item line splits between name and
amount.

Building the layout once and rendering it three ways is the whole point of
this module. The alternative — writing HTML now and ESC/POS later — means
either reimplementing every layout decision or, more likely, quietly letting
the two drift until the thermal bill and the browser bill disagree about
what the guest paid.

The document is deliberately dumb: it knows nothing about bills, tax, or
kitchens. Builders in receipt_builder.py turn domain objects into these
lines; renderers turn these lines into output. Neither knows about the
other.
"""
from dataclasses import dataclass, field
from enum import StrEnum


class Align(StrEnum):
    LEFT = "LEFT"
    CENTER = "CENTER"
    RIGHT = "RIGHT"


class Emphasis(StrEnum):
    NORMAL = "NORMAL"
    BOLD = "BOLD"
    # Double-height on thermal, larger type in HTML. Used sparingly — the
    # business name and the grand total, essentially.
    LARGE = "LARGE"
    BOLD_LARGE = "BOLD_LARGE"


class LineKind(StrEnum):
    TEXT = "TEXT"
    # Label on the left, value hard right, dot-filled between on thermal.
    PAIR = "PAIR"
    # Name, quantity, rate and amount — wraps the name when it is too long
    # rather than truncating it, since the guest needs to recognise the dish.
    ITEM = "ITEM"
    DIVIDER = "DIVIDER"
    SPACER = "SPACER"


@dataclass(frozen=True)
class Line:
    kind: LineKind
    text: str = ""
    value: str = ""
    align: Align = Align.LEFT
    emphasis: Emphasis = Emphasis.NORMAL
    # ITEM only.
    quantity: str = ""
    rate: str = ""
    # Rendered smaller/indented under its parent — option names, variant
    # names, special instructions.
    sub: bool = False


@dataclass
class ReceiptDocument:
    """A complete receipt, ready to render.

    `width` is in characters and only means anything to the text and ESC/POS
    renderers; HTML sizes itself with CSS. 32 is the standard for 58mm paper
    and 48 for 80mm, which is what nearly every restaurant counter uses.
    """

    lines: list[Line] = field(default_factory=list)
    width: int = 48
    # Drives the ESC/POS drawer-kick command. Only true for a settled bill —
    # a kitchen ticket or a preview must never pop the till.
    open_cash_drawer: bool = False
    # Used as the HTML document title, which is what a browser puts in the
    # print dialog and in the filename when someone prints to PDF.
    title: str = "Receipt"

    # --- composition helpers -------------------------------------------
    # Builders read far better as a sequence of intent ("centre this, rule
    # off, now the items") than as a list of dataclass literals.

    def text(self, text: str = "", *, align: Align = Align.LEFT,
             emphasis: Emphasis = Emphasis.NORMAL, sub: bool = False) -> "ReceiptDocument":
        self.lines.append(Line(LineKind.TEXT, text=text, align=align, emphasis=emphasis, sub=sub))
        return self

    def pair(self, label: str, value: str, *, emphasis: Emphasis = Emphasis.NORMAL) -> "ReceiptDocument":
        self.lines.append(Line(LineKind.PAIR, text=label, value=value, emphasis=emphasis))
        return self

    def item(self, name: str, quantity: str, rate: str, amount: str) -> "ReceiptDocument":
        self.lines.append(Line(LineKind.ITEM, text=name, quantity=quantity, rate=rate, value=amount))
        return self

    def sub_text(self, text: str) -> "ReceiptDocument":
        return self.text(text, sub=True)

    def divider(self) -> "ReceiptDocument":
        self.lines.append(Line(LineKind.DIVIDER))
        return self

    def spacer(self) -> "ReceiptDocument":
        self.lines.append(Line(LineKind.SPACER))
        return self
