import { type InputHTMLAttributes, forwardRef } from "react";
import { cn } from "@/lib/cn";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  invalid?: boolean;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className, invalid, ...props }, ref) => {
    return (
      <input
        ref={ref}
        className={cn(
          "h-10 w-full rounded-lg border bg-white px-3 text-sm text-slate-900 placeholder:text-slate-400",
          "transition-colors focus-ring",
          invalid ? "border-danger-500" : "border-slate-300 hover:border-slate-400",
          "disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-400",
          className
        )}
        {...props}
      />
    );
  }
);

Input.displayName = "Input";
