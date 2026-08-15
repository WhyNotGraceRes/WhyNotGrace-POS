import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import toast from "react-hot-toast";
import { AlertTriangle, Plus } from "lucide-react";

import { PageHeader } from "@/components/PageHeader";
import { Card } from "@/components/ui/Card";
import { Spinner } from "@/components/ui/Spinner";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Label } from "@/components/ui/Label";
import { Dialog } from "@/components/ui/Dialog";
import { MenuSearch } from "@/features/pos/components/MenuSearch";
import { parseApiError } from "@/api/errors";
import { useCustomers, useCreateCustomer } from "@/features/customers/hooks";
import { CustomerDetailDialog } from "@/features/customers/components/CustomerDetailDialog";
import type { CustomerOut } from "@/types/models";

export function CustomersPage() {
  const { t } = useTranslation();
  const { data: customers, isLoading, isError } = useCustomers();
  const createCustomer = useCreateCustomer();

  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState<CustomerOut | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [firstName, setFirstName] = useState("");
  const [mobile, setMobile] = useState("");
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);

  const filtered = useMemo(() => {
    if (!customers) return [];
    const q = search.trim().toLowerCase();
    if (!q) return customers;
    return customers.filter((c) => c.first_name.toLowerCase().includes(q) || c.mobile.includes(q));
  }, [customers, search]);

  const handleCreate = () => {
    setError(null);
    if (!firstName.trim() || mobile.trim().length < 7) {
      setError(t("customers.createInvalid"));
      return;
    }
    createCustomer.mutate(
      { first_name: firstName.trim(), mobile: mobile.trim(), email: email.trim() || undefined },
      {
        onSuccess: () => {
          toast.success(t("customers.created"));
          setCreateOpen(false);
          setFirstName("");
          setMobile("");
          setEmail("");
        },
        onError: (err) => setError(parseApiError(err).message),
      }
    );
  };

  return (
    <div>
      <PageHeader
        title={t("nav.customers")}
        subtitle={t("customers.subtitle")}
        actions={
          <Button onClick={() => setCreateOpen(true)}>
            <Plus size={16} />
            {t("customers.addCustomer")}
          </Button>
        }
      />

      <div className="mb-4 max-w-sm">
        <MenuSearch value={search} onChange={setSearch} placeholder={t("customers.searchPlaceholder")} />
      </div>

      {isLoading && (
        <div className="flex justify-center py-16">
          <Spinner className="text-brand-600" />
        </div>
      )}

      {isError && (
        <div className="flex flex-col items-center gap-2 py-16 text-danger-600">
          <AlertTriangle size={22} />
          <p className="text-sm font-medium">{t("customers.loadError")}</p>
        </div>
      )}

      {!isLoading && !isError && filtered.length === 0 && (
        <p className="py-16 text-center text-sm text-slate-400">
          {search ? t("customers.noSearchResults", { query: search }) : t("customers.empty")}
        </p>
      )}

      {!isLoading && !isError && filtered.length > 0 && (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {filtered.map((customer) => (
            <Card
              key={customer.id}
              className="cursor-pointer p-4 transition-shadow hover:shadow-popover"
              onClick={() => setSelected(customer)}
            >
              <p className="font-semibold text-slate-800">{customer.first_name}</p>
              <p className="text-sm text-slate-500">{customer.mobile}</p>
              {customer.email && <p className="truncate text-xs text-slate-400">{customer.email}</p>}
            </Card>
          ))}
        </div>
      )}

      <CustomerDetailDialog customer={selected} onClose={() => setSelected(null)} />

      <Dialog open={createOpen} onClose={() => setCreateOpen(false)} title={t("customers.addCustomer")} size="sm">
        <div className="space-y-3">
          {error && <p className="text-xs text-danger-600">{error}</p>}
          <div>
            <Label htmlFor="cust-first-name">{t("customers.firstName")}</Label>
            <Input id="cust-first-name" value={firstName} onChange={(e) => setFirstName(e.target.value)} />
          </div>
          <div>
            <Label htmlFor="cust-mobile">{t("customers.mobile")}</Label>
            <Input id="cust-mobile" value={mobile} onChange={(e) => setMobile(e.target.value)} />
          </div>
          <div>
            <Label htmlFor="cust-email">{t("customers.email")}</Label>
            <Input id="cust-email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
          </div>
          <Button className="w-full" isLoading={createCustomer.isPending} onClick={handleCreate}>
            {t("customers.create")}
          </Button>
        </div>
      </Dialog>
    </div>
  );
}
