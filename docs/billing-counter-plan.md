# Billing counter — build plan

Status as of 2026-08-16: **Blocks 1–3 done. Block 4 remains.**

The ordering side of this system was already ahead of the Indian mid-market
(Petpooja, Posist, Rista): one order engine across six channels, one bill per
table visit however many rounds it took, prices resolved server-side. The
counter side was behind all of them. Blocks 1–3 closed most of that gap.

## Block 1 — Invoice integrity ✅ done

Commit `76781f9`, plus `2a58d98` finishing the toggles.

- Sequential per-business, per-financial-year invoice series, allocated at
  **settlement** so an abandoned bill cannot burn a serial. A locked counter
  row rather than a Postgres sequence, because a sequence is not gapless.
- Void with reason and role gate; the voided invoice keeps its number and
  stays in the series.
- Reprint counting; any copy after the first is marked DUPLICATE.
- Refunds recorded as their own event against a specific payment.
- Round-off applied after tax, never folded into the taxable value.
- A code-side toggle registry with a per-business override table, splitting
  **preferences** (owner-editable) from **entitlements** (plan-controlled).
  Adding a switch costs one line and no migration.

## Block 2 — Printing ✅ done

Commit `f6fd109`.

- One canonical receipt document rendered three ways: text, 80mm HTML, and
  ESC/POS bytes. Builders turn domain objects into lines; renderers turn
  lines into output; neither knows about the other.
- Bill carries GSTIN, FSSAI, invoice number, CGST/SGST split, round-off,
  DUPLICATE marking.
- Preview and print are separate verbs, so the duplicate count reflects
  paper actually produced.
- Cash drawer kicks on a real first print only.
- Kitchen tickets carry no prices and route per station.

## Block 3 — Shift and day-end ✅ done

Commit `eef6e53`.

- One open drawer per cashier, enforced by a partial unique index.
- Blind cash counting: the expected figure is withheld until a count is
  committed, including from the printed report.
- Payments and refunds carry `shift_id`, so the Z-report is not derived from
  a time window.
- Drawer counts cash only, less cash refunded; gross takings still show
  every method.
- Z-report prints through the Block 2 document.

## Block 4 — Counter operations 🔶 in progress

The last block in the original plan. Being worked in dependency order rather
than the order first written down: voiding a line establishes the "recompute a
bill after its lines change" behaviour that comping and splitting both need,
so it went first and the rest get smaller.

- **Void an individual item** with reason and role gate — ✅ done, commit
  `94485e0`. Lines are soft-voided (kept, marked, excluded from totals, not
  printed on the guest copy) because the bill refresh re-adds any order item
  the bill does not already carry, so a deleted line would come back.
- **NC / complimentary bills** — ✅ done, commit `fe401ee`. A comp is kept
  distinct from a void throughout: a void was never supplied and leaves the
  bill, a comp was supplied and given away so it prints marked NC. Comps are
  reversible, voids are not, and comping has its own two toggles. A fully-NC
  bill takes no payment row and no tax invoice number (see below).
- **Split tender UI** — next. Partial payments already work server-side, but
  nothing in the UI lets a cashier take ₹300 cash and ₹200 card on one bill.
- **Merge tables**, **transfer table**, **transfer item**.
- **Split bill** — by item, by amount, equally. `OrderSession` is the right
  foundation and none of the operations exist. Last, and largest.

## Loose ends outside the blocks

Carried forward honestly rather than quietly dropped.

**~~A real bug, still unfixed.~~ Fixed.** `reports_service` filtered
`created_at <= end_date` against a date-only value that parses to midnight, so
the last day of any selected range was always missing and the Reports page
showed ₹0 for a range including today while the dashboard showed the real
figure. All six report queries now resolve their range once, through
`_resolve_range`, into a half-open interval `[start, end)` whose upper bound is
the first moment of the day *after* the end date.

The range is computed in the restaurant's own timezone (`BusinessSettings.
timezone`, default `Asia/Kolkata`), matching what the receipt builder already
does, so a bill settled at 00:30 falls on the date its receipt shows rather
than on the previous UTC day. The endpoints now declare these parameters as
`date` rather than `datetime`, which is what the frontend has always sent.

Note for whoever picks this up: `dashboard_service._today_start_utc()` still
defines "today" as a UTC day, so the dashboard's today-figures begin at 05:30
IST and miss after-midnight trade. Reports and the dashboard therefore still
disagree at the edges, in the other direction now. Small, separate, worth
doing.

**An NC bill does not consume a tax invoice number.** This was a judgement
call taken while building Block 4, and it is worth an accountant's eye. The
reasoning: Block 1 made `invoice_number` specifically the GST serial, distinct
from the internal `bill_number`; food given away for no consideration is not a
taxable supply; so numbering a zero-value NC bill would put a zero-value
invoice into the return and consume a serial for a document that is not an
invoice. The receipt labels it "No-charge bill" instead. A partly-comped bill
is still a real supply and numbers normally at settlement. If the client's
accountant would rather every printed document carry a serial, this is a
one-line change in `mark_bill_nc` — but the series would then contain
zero-value entries.

**A settled table can be billed again.** `OrderSession.is_closed` is only ever
read, never written, though its own docstring says it should close when the
bill is paid. So after any settlement — cash or NC — the session stays open,
the table stays on the Billing list, and generating again mints a second bill
containing the same order items. Pre-existing, found while testing Block 4.
The fix needs care: closing the session on first settlement would break
ordering another round after the bill is printed, which relies on the session
staying open.

**ESC/POS has never met a printer.** Byte sequences are asserted against the
documented command set; that is not the same as paper. Before trusting it:
print one bill and one kitchen ticket on the real machine and confirm the cut
lands right, the drawer fires, and characters-per-line matches the paper.

**Refunds are not GST credit notes.** Reversing a supply formally needs a
credit note with its own document series. The invoice-series machinery would
make that cheap to add; the data to raise one is already recorded.

**No HSN/SAC codes per menu item.** Required for a fully compliant invoice.

**Entitlement toggles cannot be changed by anyone**, because there is no
platform-superadmin surface. Every shipped toggle is currently a preference,
so nothing is stranded — but the moment a function is sold separately, that
surface has to exist.

**The test suite never runs the migrations.** `conftest` builds the schema
with `create_all()` from the models, so a model/migration divergence is
invisible. This already bit once, when a `FeatureModule` enum value was added
in Python but not to the Postgres type — every test passed and the migrated
database failed on first use. A test that runs `alembic upgrade head` against
a clean database would have caught it.

**One pre-existing test failure.**
`test_pool_drains_after_genuine_concurrent_timeout_exhaustion` fails
reproducibly — it expects a 500 from pool exhaustion but the auth rate limiter
returns 429 first, so it never reproduces the contention it is testing. It
predates all of this work.

**No shift history screen.** The API lists past shifts; nothing renders them.

**No kitchen print button.** Station routing and ticket endpoints work and
are tested; nothing in the kitchen UI calls them.

## Still to decide

- Final invoice number format, to confirm with the client's CA.
- Whether discounts need approval limits per role, or reason plus audit is
  enough for this client.
