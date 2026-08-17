import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Plus, Search } from "lucide-react";
import toast from "react-hot-toast";

import { Dialog } from "@/components/ui/Dialog";
import { Input } from "@/components/ui/Input";
import { Label } from "@/components/ui/Label";
import { Button } from "@/components/ui/Button";
import { Spinner } from "@/components/ui/Spinner";
import { parseApiError } from "@/api/errors";
import { useCustomers, useCreateCustomer } from "@/features/customers/hooks";

export function CustomerPickerDialog({
  open,
  onClose,
  onSelect,
}: {
  open: boolean;
  onClose: () => void;
  onSelect: (id: string, label: string) => void;
}) {
  const { t } = useTranslation();
  const { data: customers, isLoading } = useCustomers();
  const createCustomer = useCreateCustomer();
  const [query, setQuery] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [firstName, setFirstName] = useState("");
  const [mobile, setMobile] = useState("");
  const [error, setError] = useState<string | null>(null);

  const filtered = useMemo(() => {
    if (!customers) return [];
    const q = query.trim().toLowerCase();
    if (!q) return customers;
    return customers.filter((c) => c.first_name.toLowerCase().includes(q) || c.mobile.includes(q));
  }, [customers, query]);

  const handleCreate = () => {
    setError(null);
    if (!firstName.trim() || mobile.trim().length < 7) {
      setError(t("customers.createInvalid"));
      return;
    }
    createCustomer.mutate(
      { first_name: firstName.trim(), mobile: mobile.trim() },
      {
        onSuccess: (customer) => {
          toast.success(t("customers.created"));
          onSelect(customer.id, `${customer.first_name} (${customer.mobile})`);
          setShowCreate(false);
          setFirstName("");
          setMobile("");
          onClose();
        },
        onError: (err) => setError(parseApiError(err).message),
      }
    );
  };

  return (
    <Dialog open={open} onClose={onClose} title={t("pos.selectCustomerTitle")} size="sm">
      {!showCreate ? (
        <>
          <div className="relative mb-3">
            <Search size={16} className="pointer-events-none absolute left-3 top-1/2 -transtone-y-1/2 text-stone-400" />
            <Input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={t("customers.searchPlaceholder")}
              className="pl-9"
            />
          </div>

          {isLoading && (
            <div className="flex justify-center py-6">
              <Spinner className="text-brand-600" />
            </div>
          )}

          {!isLoading && (
            <ul className="max-h-64 space-y-1 overflow-y-auto">
              {filtered.map((customer) => (
                <li key={customer.id}>
                  <button
                    type="button"
                    onClick={() => {
                      onSelect(customer.id, `${customer.first_name} (${customer.mobile})`);
                      onClose();
                    }}
                    className="flex w-full items-center justify-between rounded-lg px-3 py-2 text-left text-sm hover:bg-stone-50"
                  >
                    <span className="font-medium text-stone-800">{customer.first_name}</span>
                    <span className="text-stone-500">{customer.mobile}</span>
                  </button>
                </li>
              ))}
              {filtered.length === 0 && <p className="py-4 text-center text-sm text-stone-400">{t("customers.empty")}</p>}
            </ul>
          )}

          <Button variant="secondary" className="mt-3 w-full" onClick={() => setShowCreate(true)}>
            <Plus size={16} />
            {t("customers.addCustomer")}
          </Button>
        </>
      ) : (
        <div className="space-y-3">
          {error && <p className="text-xs text-danger-600">{error}</p>}
          <div>
            <Label htmlFor="picker-first-name">{t("customers.firstName")}</Label>
            <Input id="picker-first-name" value={firstName} onChange={(e) => setFirstName(e.target.value)} />
          </div>
          <div>
            <Label htmlFor="picker-mobile">{t("customers.mobile")}</Label>
            <Input id="picker-mobile" value={mobile} onChange={(e) => setMobile(e.target.value)} />
          </div>
          <div className="flex gap-2">
            <Button isLoading={createCustomer.isPending} onClick={handleCreate}>
              {t("customers.create")}
            </Button>
            <Button variant="ghost" onClick={() => setShowCreate(false)}>
              {t("common.back")}
            </Button>
          </div>
        </div>
      )}
    </Dialog>
  );
}
