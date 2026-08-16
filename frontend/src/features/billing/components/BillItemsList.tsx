import { useState } from "react";
import { useTranslation } from "react-i18next";
import toast from "react-hot-toast";
import { Ban, Gift, Undo2 } from "lucide-react";

import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { parseApiError } from "@/api/errors";
import { formatCurrency } from "@/lib/format";
import { useCompBillItem, useUncompBillItem, useVoidBillItem } from "@/features/billing/hooks";
import type { BillItemOut, BillOut } from "@/types/models";

/** Void and comp are separate acts, not two settings of one control: a void
 * says the dish was never supplied, a comp says it was supplied and given
 * away. The row offers both and never collapses them into one button. */
type PendingAction = { itemId: string; kind: "void" | "comp" };

export function BillItemsList({ bill }: { bill: BillOut }) {
  const [pending, setPending] = useState<PendingAction | null>(null);

  const isOpen = bill.status !== "PAID" && bill.status !== "CANCELLED";

  return (
    <ul className="divide-y divide-slate-100 rounded-lg border border-slate-100">
      {bill.items.map((item) =>
        pending?.itemId === item.id ? (
          <ConfirmRow
            key={item.id}
            bill={bill}
            item={item}
            kind={pending.kind}
            onDone={() => setPending(null)}
            onCancel={() => setPending(null)}
          />
        ) : (
          <ItemRow
            key={item.id}
            bill={bill}
            item={item}
            isOpen={isOpen}
            onVoid={() => setPending({ itemId: item.id, kind: "void" })}
            onComp={() => setPending({ itemId: item.id, kind: "comp" })}
          />
        )
      )}
    </ul>
  );
}

function ItemRow({
  bill,
  item,
  isOpen,
  onVoid,
  onComp,
}: {
  bill: BillOut;
  item: BillItemOut;
  isOpen: boolean;
  onVoid: () => void;
  onComp: () => void;
}) {
  const { t } = useTranslation();
  const uncomp = useUncompBillItem();

  const struck = Boolean(item.voided_at);
  const comped = Boolean(item.comped_at);

  return (
    <li className="flex items-center justify-between gap-2 px-3 py-2 text-sm">
      <span className={struck ? "text-slate-400 line-through" : "text-slate-700"}>
        {item.quantity} × {item.item_name_snapshot}
      </span>

      <span className="flex items-center gap-2">
        {struck && (
          // The struck line stays visible to the cashier. It is not on the
          // guest's printed bill and not in the total, but a line that
          // vanished entirely would look like the void had failed.
          <Badge tone="slate">
            {item.void_reason ? `${t("billing.voided")}: ${item.void_reason}` : t("billing.voided")}
          </Badge>
        )}
        {comped && (
          <Badge tone="brand">
            {item.comp_reason ? `${t("billing.nc")}: ${item.comp_reason}` : t("billing.nc")}
          </Badge>
        )}

        <span
          className={
            struck || comped ? "text-slate-400 line-through" : "font-semibold text-slate-800"
          }
        >
          {formatCurrency(item.line_total)}
        </span>

        {isOpen && !struck && !comped && (
          <>
            <IconButton onClick={onComp} label={t("billing.compItem")} tone="brand">
              <Gift size={15} />
            </IconButton>
            <IconButton onClick={onVoid} label={t("billing.voidItem")} tone="danger">
              <Ban size={15} />
            </IconButton>
          </>
        )}

        {/* A comp is reversible where a void is not — it is only a pricing
            decision, and the manager who made it may change their mind
            before the guest pays. Hidden on an NC bill, where the comp
            belongs to the bill-level mark rather than to this line. */}
        {isOpen && comped && !bill.nc_at && (
          <IconButton
            label={t("billing.uncompItem")}
            tone="slate"
            disabled={uncomp.isPending}
            onClick={() =>
              uncomp.mutate(
                { billId: bill.id, itemId: item.id },
                { onError: (err) => toast.error(parseApiError(err).message) }
              )
            }
          >
            <Undo2 size={15} />
          </IconButton>
        )}
      </span>
    </li>
  );
}

function ConfirmRow({
  bill,
  item,
  kind,
  onDone,
  onCancel,
}: {
  bill: BillOut;
  item: BillItemOut;
  kind: "void" | "comp";
  onDone: () => void;
  onCancel: () => void;
}) {
  const { t } = useTranslation();
  const voidItem = useVoidBillItem();
  const compItem = useCompBillItem();
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string | null>(null);

  const mutation = kind === "void" ? voidItem : compItem;
  const label = `${item.quantity} × ${item.item_name_snapshot}`;

  // Whether a reason is mandatory, and whether this user is senior enough,
  // are both decided by the server according to the counter's toggles — and
  // void and comp are governed by different ones. The form always offers the
  // field and surfaces whatever the server says, rather than keeping a second
  // copy of those rules here that could drift.
  const submit = () => {
    setError(null);
    mutation.mutate(
      { billId: bill.id, itemId: item.id, reason: reason.trim() || undefined },
      {
        onSuccess: () => {
          toast.success(kind === "void" ? t("billing.itemVoided") : t("billing.itemComped"));
          onDone();
        },
        onError: (err) => setError(parseApiError(err).message),
      }
    );
  };

  return (
    <li className="space-y-2 bg-slate-50 px-3 py-2.5 text-sm">
      <p className="text-slate-700">
        {kind === "void"
          ? t("billing.voidItemConfirm", { item: label })
          : t("billing.compItemConfirm", { item: label })}
      </p>
      {error && <p className="text-xs text-danger-600">{error}</p>}
      <Input
        value={reason}
        autoFocus
        placeholder={
          kind === "void" ? t("billing.voidReasonPlaceholder") : t("billing.compReasonPlaceholder")
        }
        onChange={(e) => setReason(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter") submit();
          if (e.key === "Escape") onCancel();
        }}
      />
      <div className="flex gap-2">
        <Button
          size="sm"
          variant={kind === "void" ? "danger" : "primary"}
          isLoading={mutation.isPending}
          onClick={submit}
        >
          {kind === "void" ? t("billing.voidItem") : t("billing.compItem")}
        </Button>
        <Button size="sm" variant="ghost" onClick={onCancel}>
          {t("common.cancel")}
        </Button>
      </div>
    </li>
  );
}

function Badge({ children, tone }: { children: React.ReactNode; tone: "slate" | "brand" }) {
  return (
    <span
      className={
        "rounded px-1.5 py-0.5 text-xs font-medium " +
        (tone === "brand" ? "bg-brand-50 text-brand-700" : "bg-slate-100 text-slate-500")
      }
    >
      {children}
    </span>
  );
}

function IconButton({
  children,
  label,
  tone,
  onClick,
  disabled,
}: {
  children: React.ReactNode;
  label: string;
  tone: "slate" | "brand" | "danger";
  onClick: () => void;
  disabled?: boolean;
}) {
  const hover =
    tone === "danger"
      ? "hover:bg-danger-50 hover:text-danger-600"
      : tone === "brand"
        ? "hover:bg-brand-50 hover:text-brand-700"
        : "hover:bg-slate-100 hover:text-slate-700";
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      aria-label={label}
      title={label}
      className={`rounded p-1 text-slate-400 disabled:opacity-40 ${hover}`}
    >
      {children}
    </button>
  );
}
