# Billing counter — build plan

Status: agreed 2026-08-16, not yet started. Execution begins next session.

The ordering side of this system is ahead of the Indian mid-market
(Petpooja, Posist, Rista): one order engine across six channels, one bill per
table visit however many rounds it took, prices resolved server-side. The
counter side is behind all of them. This plan closes that gap.

## What a counter needs that we don't have

Confirmed by reading the code, not assumed:

| | competitors | here |
|---|---|---|
| Sequential invoice series | per financial year, gapless | timestamp + random |
| Bill / KOT printing | yes, with station routing | no print code at all |
| Shift, cash drawer, day-end | yes | none |
| Void bill or item, with reason | yes | `BillStatus.CANCELLED` never set |
| Refunds | yes | `PaymentStatus.REFUNDED` never set |
| Reprint audit | yes | none |
| Split / merge / transfer table | yes | none |
| Round-off, NC bills | yes | none |

## Decisions taken

**Printing renders from one canonical document.** The server produces an
ordered list of typed receipt lines; renderers turn that into HTML (browser
print) and ESC/POS (thermal). Both are built in the same block. This is the
decision that matters most — an HTML-only implementation would have to be
rewritten for thermal, and a shared document also makes a PDF renderer for
WhatsApp receipts nearly free later.

**Invoice numbers are allocated at settlement, not at bill creation.** Today
`generate_or_refresh_bill` assigns `bill_number` immediately, so a bill that
is generated and then abandoned burns a number and leaves a gap in the
series — exactly what the rule forbids. The bill keeps an internal reference
from creation; the invoice number is allocated when it is finalised.

**Voided invoices keep their number.** A void is a recorded event in the
series, not a deletion. Deleting would create the gap we are trying to avoid.

**No inventory, no purchase/vendor, no captain app, no payment-terminal
integration in this phase.** The terminal integration in particular needs
hardware in hand; card payments can be recorded manually until then.

## Known verification limit

There is a pilot restaurant but no thermal printer confirmed yet. The ESC/POS
renderer will therefore be **written and unit-tested at the byte level, but
not verified against real hardware**. It ships marked as such. The pilot can
run on browser printing in the meantime, which is the reason both renderers
are being built together rather than sequentially.

Before trusting ESC/POS in production: print one bill and one KOT on the
actual printer, confirm the cash drawer kick fires, and confirm paper width
and character-per-line settings match the model.

## Block 1 — Invoice integrity

Everything else depends on this, and it is small, so it goes first.

- `invoice_counters` keyed by (business, financial year, series), incremented
  under a row lock. Restaurant volume makes contention irrelevant — 2,000
  bills a day is nothing.
- Number format inside 16 characters, alphanumeric plus `-` and `/`, per
  CGST Rule 46. Confirm the final format with the client's CA.
- Allocation moves to settlement.
- Void: reason required, role-gated, number retained, audit logged.
- Reprint: counted, and any reprint after the first is marked DUPLICATE on
  the printed output. This is the standard control against printing two
  "originals" of the same bill.
- Refund path, so `PaymentStatus.REFUNDED` stops being decoration.

## Block 2 — Printing

- Canonical receipt document built server-side from the bill (or KOT).
- HTML renderer: 80mm-styled, printed from a hidden frame.
- ESC/POS renderer: byte output, cash-drawer kick, cut.
- KOT station routing: menu item → station → printer, so tandoor, Chinese
  and bar tickets separate.
- Bill layout must carry GSTIN, the CGST/SGST split lines, invoice number,
  and DUPLICATE marking when reprinted.

## Block 3 — Shift and day-end

This is the block owners actually buy a POS for: it is how theft is detected.

- `ShiftSession`: who opened it, opening float, closed_at, declared cash,
  expected cash, variance.
- Every `Payment` gains a `shift_id`. Without that link a Z-report is
  guesswork.
- Z-report at close: sales by payment method, voids, discounts, variance.

## Block 4 — Counter operations

- Split bill: by item, by amount, equally.
- Merge tables, transfer table, transfer item.
- Void item with reason and role gate.
- NC / complimentary bills.
- Round-off line.
- Split tender UI (partial payments already work server-side).

## Still open

- Final invoice number format, to confirm with the client's CA.
- Whether discounts need approval limits per role, or whether reason plus
  audit is enough for this client.
- HSN/SAC codes per menu item — needed for a fully compliant invoice, not
  yet scoped.
