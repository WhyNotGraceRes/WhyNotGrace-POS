import { type SelectHTMLAttributes, forwardRef } from "react";
import { cn } from "@/lib/cn";

interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  invalid?: boolean;
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(
  ({ className, invalid, children, ...props }, ref) => {
    return (
      <select
        ref={ref}
        className={cn(
          "h-10 w-full rounded-lg border bg-white px-3 text-sm text-stone-900",
          "transition-colors focus-ring",
          invalid ? "border-danger-500" : "border-stone-300 hover:border-stone-400",
          "disabled:cursor-not-allowed disabled:bg-stone-100 disabled:text-stone-400",
          className
        )}
        {...props}
      >
        {children}
      </select>
    );
  }
);

Select.displayName = "Select";
