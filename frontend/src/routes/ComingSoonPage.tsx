import { useTranslation } from "react-i18next";
import { Construction } from "lucide-react";
import { PageHeader } from "@/components/PageHeader";
import { Card } from "@/components/ui/Card";

/** Reused for every nav section not yet built (POS, Orders, Tables, Rooms,
 * Kitchen, Menu, Customers, Loyalty, Billing, Reports, Staff, Settings,
 * Integrations, Delivery). Phase 2 only builds the shell + navigation +
 * dashboard; each of these lands in its own later phase. */
export function ComingSoonPage({ titleKey }: { titleKey: string }) {
  const { t } = useTranslation();
  const title = t(titleKey);

  return (
    <div>
      <PageHeader title={title} />
      <Card className="flex flex-col items-center gap-3 p-12 text-center">
        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-slate-100 text-slate-400">
          <Construction size={22} />
        </div>
        <p className="font-semibold text-slate-700">{t("comingSoon.title")}</p>
        <p className="max-w-sm text-sm text-slate-500">{t("comingSoon.body", { section: title })}</p>
      </Card>
    </div>
  );
}
