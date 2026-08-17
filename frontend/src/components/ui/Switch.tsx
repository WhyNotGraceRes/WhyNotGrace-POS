import { cn } from "@/lib/cn";

export function Switch({
  checked,
  onChange,
  disabled,
  label,
}: {
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
  label?: string;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className={cn(
        "relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors focus-ring",
        checked ? "bg-brand-600" : "bg-stone-200",
        disabled && "cursor-not-allowed opacity-50"
      )}
    >
      <span
        className={cn(
          "inline-block h-4 w-4 transform rounded-full bg-white shadow transition-transform",
          checked ? "transtone-x-6" : "transtone-x-1"
        )}
      />
    </button>
  );
}
