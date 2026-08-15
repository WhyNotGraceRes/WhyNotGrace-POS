import { useState } from "react";
import { useTranslation } from "react-i18next";
import toast from "react-hot-toast";
import { Eye, Printer } from "lucide-react";

import { Button } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";
import { parseApiError } from "@/api/errors";
import { previewBill, printBill } from "@/lib/printReceipt";
import type { BillOut } from "@/types/models";

export function PrintBillButtons({ bill }: { bill: BillOut }) {
  const { t } = useTranslation();
  const [printing, setPrinting] = useState(false);
  const [previewHtml, setPreviewHtml] = useState<string | null>(null);

  const handlePrint = async () => {
    setPrinting(true);
    try {
      await printBill(bill.id);
    } catch (err) {
      toast.error(parseApiError(err).message);
    } finally {
      setPrinting(false);
    }
  };

  const handlePreview = async () => {
    try {
      setPreviewHtml(await previewBill(bill.id));
    } catch (err) {
      toast.error(parseApiError(err).message);
    }
  };

  return (
    <>
      <div className="flex flex-wrap items-center gap-2">
        <Button onClick={() => void handlePrint()} isLoading={printing}>
          <Printer size={15} />
          {/* The count is shown on the button itself, so a cashier can see
              this bill has been printed before without opening anything. */}
          {bill.print_count > 0
            ? t("billing.printAgain", { count: bill.print_count })
            : t("billing.print")}
        </Button>
        <Button variant="secondary" onClick={() => void handlePreview()}>
          <Eye size={15} /> {t("billing.preview")}
        </Button>
      </div>

      {bill.print_count > 0 && (
        <p className="mt-1.5 text-xs text-amber-700">{t("billing.reprintWarning")}</p>
      )}

      <Dialog
        open={previewHtml !== null}
        onClose={() => setPreviewHtml(null)}
        title={t("billing.previewTitle")}
        size="sm"
      >
        {/* srcDoc, not innerHTML: the receipt carries its own stylesheet and
            must not inherit the dashboard's, and an iframe is also what keeps
            its markup out of this document. Sandboxed because it is rendered
            content, even though we produced it. */}
        <iframe
          title={t("billing.previewTitle")}
          srcDoc={previewHtml ?? ""}
          sandbox=""
          className="h-[60vh] w-full rounded border border-slate-200 bg-white"
        />
      </Dialog>
    </>
  );
}
