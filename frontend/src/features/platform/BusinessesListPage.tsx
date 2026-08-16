import { useState } from "react";
import { Link } from "react-router-dom";
import { AlertTriangle, Plus } from "lucide-react";

import { PageHeader } from "@/components/PageHeader";
import { Card } from "@/components/ui/Card";
import { Spinner } from "@/components/ui/Spinner";
import { Button } from "@/components/ui/Button";
import { usePlatformBusinesses } from "@/features/platform/hooks";
import { ProvisionBusinessDialog } from "@/features/platform/components/ProvisionBusinessDialog";

export function BusinessesListPage() {
  const { data: businesses, isLoading, isError } = usePlatformBusinesses();
  const [dialogOpen, setDialogOpen] = useState(false);

  return (
    <div>
      <PageHeader
        title="Businesses"
        subtitle="Every client provisioned on WhyNotGrace."
        actions={
          <Button onClick={() => setDialogOpen(true)}>
            <Plus size={16} />
            Provision business
          </Button>
        }
      />

      {isLoading && (
        <div className="flex justify-center py-16">
          <Spinner className="text-brand-600" />
        </div>
      )}

      {isError && (
        <div className="flex flex-col items-center gap-2 py-16 text-danger-600">
          <AlertTriangle size={22} />
          <p className="text-sm font-medium">Couldn't load businesses.</p>
        </div>
      )}

      {!isLoading && !isError && businesses && businesses.length === 0 && (
        <Card className="p-8 text-center text-sm text-slate-500">
          No businesses yet. Provision the first one to get started.
        </Card>
      )}

      {!isLoading && !isError && businesses && businesses.length > 0 && (
        <Card className="divide-y divide-slate-100">
          {businesses.map((business) => (
            <Link
              key={business.id}
              to={`/platform/businesses/${business.id}`}
              className="flex items-center justify-between gap-4 px-4 py-3.5 hover:bg-slate-50"
            >
              <div>
                <p className="text-sm font-semibold text-slate-800">{business.name}</p>
                <p className="text-xs text-slate-500">
                  {business.business_type.replace(/_/g, " ")} · {business.slug}
                </p>
              </div>
              <span
                className={
                  "rounded-full px-2.5 py-0.5 text-xs font-semibold " +
                  (business.is_active ? "bg-success-50 text-success-700" : "bg-danger-50 text-danger-600")
                }
              >
                {business.is_active ? "Active" : "Suspended"}
              </span>
            </Link>
          ))}
        </Card>
      )}

      <ProvisionBusinessDialog open={dialogOpen} onClose={() => setDialogOpen(false)} />
    </div>
  );
}
