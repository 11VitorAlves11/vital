import * as Label from "@radix-ui/react-label";
import { useId } from "react";
import type { SelectHTMLAttributes } from "react";

import { cn } from "../../lib/cn";

export type SelectOption = { value: string; label: string };

type SelectProps = Omit<SelectHTMLAttributes<HTMLSelectElement>, "children"> & {
  label: string;
  options: SelectOption[];
  error?: string;
  placeholder?: string;
};

/**
 * A native select on purpose: it is the control every mobile browser already
 * knows how to present, and it stays searchable by typing without extra code.
 */
export function Select({
  label,
  options,
  error,
  placeholder,
  className,
  id,
  ...props
}: SelectProps) {
  const generatedId = useId();
  const selectId = id ?? generatedId;
  const errorId = `${selectId}-error`;

  return (
    <div className="flex flex-col gap-1">
      <Label.Root htmlFor={selectId} className="text-sm font-medium text-ink">
        {label}
      </Label.Root>
      <select
        id={selectId}
        aria-invalid={error ? true : undefined}
        aria-describedby={error ? errorId : undefined}
        className={cn(
          "min-h-[var(--touch-target)] w-full rounded-[var(--radius-md)] px-3",
          "border bg-surface-raised text-ink",
          error ? "border-flag-alert" : "border-border-strong",
          className,
        )}
        {...props}
      >
        {placeholder ? <option value="">{placeholder}</option> : null}
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
      {error ? (
        <p id={errorId} role="alert" className="text-sm text-flag-alert">
          {error}
        </p>
      ) : null}
    </div>
  );
}
