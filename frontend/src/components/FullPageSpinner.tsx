import { Spinner } from "@/components/ui/Spinner";

export function FullPageSpinner() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50">
      <Spinner size={28} className="text-brand-600" />
    </div>
  );
}
