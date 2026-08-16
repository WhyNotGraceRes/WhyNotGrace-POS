import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import toast from "react-hot-toast";

import { Dialog } from "@/components/ui/Dialog";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Label } from "@/components/ui/Label";
import { Select } from "@/components/ui/Select";
import { FieldError } from "@/components/ui/FieldError";
import { parseApiError } from "@/api/errors";
import { useProvisionBusiness } from "@/features/platform/hooks";

// Mirrors backend/app/models/enums.py BusinessType.
const BUSINESS_TYPES = ["RESTAURANT", "HOTEL", "RESORT", "LODGE", "LOUNGE", "CAFE", "CLOUD_KITCHEN", "OTHER"] as const;

const schema = z.object({
  business_name: z.string().min(2).max(200),
  business_type: z.enum(BUSINESS_TYPES),
  owner_first_name: z.string().min(1).max(100),
  owner_last_name: z.string().min(1).max(100),
  owner_email: z.string().email(),
  owner_mobile: z
    .string()
    .min(7)
    .max(20)
    .refine((v) => /^[0-9+\-\s]+$/.test(v), "Digits, spaces, + or - only"),
  owner_password: z.string().min(8).max(128),
});
type FormValues = z.infer<typeof schema>;

export function ProvisionBusinessDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const provision = useProvisionBusiness();
  const [error, setError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<FormValues>({ resolver: zodResolver(schema), defaultValues: { business_type: "RESTAURANT" } });

  const close = () => {
    reset();
    setError(null);
    onClose();
  };

  const onSubmit = handleSubmit(async (values) => {
    setError(null);
    try {
      const result = await provision.mutateAsync(values);
      toast.success(`${values.business_name} provisioned — owner login: ${result.owner_email}`);
      close();
    } catch (err) {
      setError(parseApiError(err).message);
    }
  });

  return (
    <Dialog open={open} onClose={close} title="Provision a new business" size="md">
      <form onSubmit={onSubmit} className="space-y-4" noValidate>
        {error && (
          <p className="rounded-lg border border-danger-500/30 bg-danger-50 px-3 py-2 text-sm text-danger-700">
            {error}
          </p>
        )}

        <div>
          <Label htmlFor="business_name">Business name</Label>
          <Input id="business_name" invalid={Boolean(errors.business_name)} {...register("business_name")} />
          <FieldError message={errors.business_name?.message} />
        </div>

        <div>
          <Label htmlFor="business_type">Type</Label>
          <Select id="business_type" {...register("business_type")}>
            {BUSINESS_TYPES.map((type) => (
              <option key={type} value={type}>
                {type.replace(/_/g, " ")}
              </option>
            ))}
          </Select>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <Label htmlFor="owner_first_name">Owner first name</Label>
            <Input id="owner_first_name" invalid={Boolean(errors.owner_first_name)} {...register("owner_first_name")} />
            <FieldError message={errors.owner_first_name?.message} />
          </div>
          <div>
            <Label htmlFor="owner_last_name">Owner last name</Label>
            <Input id="owner_last_name" invalid={Boolean(errors.owner_last_name)} {...register("owner_last_name")} />
            <FieldError message={errors.owner_last_name?.message} />
          </div>
        </div>

        <div>
          <Label htmlFor="owner_email">Owner email</Label>
          <Input id="owner_email" type="email" invalid={Boolean(errors.owner_email)} {...register("owner_email")} />
          <FieldError message={errors.owner_email?.message} />
        </div>

        <div>
          <Label htmlFor="owner_mobile">Owner mobile</Label>
          <Input id="owner_mobile" invalid={Boolean(errors.owner_mobile)} {...register("owner_mobile")} />
          <FieldError message={errors.owner_mobile?.message} />
        </div>

        <div>
          <Label htmlFor="owner_password">Owner password</Label>
          <Input
            id="owner_password"
            type="password"
            invalid={Boolean(errors.owner_password)}
            {...register("owner_password")}
          />
          <FieldError message={errors.owner_password?.message} />
          <p className="mt-1 text-xs text-slate-500">
            Share this with the owner directly — the account is created active, ready to log in immediately.
          </p>
        </div>

        <div className="flex justify-end gap-2 pt-2">
          <Button type="button" variant="ghost" onClick={close}>
            Cancel
          </Button>
          <Button type="submit" isLoading={provision.isPending}>
            Provision
          </Button>
        </div>
      </form>
    </Dialog>
  );
}
