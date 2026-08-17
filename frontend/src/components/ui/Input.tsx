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
          "h-10 w-full rounded-lg border bg-white px-3 text-sm text-stone-900 placeholder:text-stone-400",
          "transition-colors focus-ring",
          invalid ? "border-danger-500" : "border-stone-300 hover:border-stone-400",
          "disabled:cursor-not-allowed disabled:bg-stone-100 disabled:text-stone-400",
          className
        )}
        {...props}
      />
    );
  }
);

Input.displayName = "Input";
