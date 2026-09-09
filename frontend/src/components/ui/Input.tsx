import * as Label from "@radix-ui/react-label";
import { useId } from "react";
import type { InputHTMLAttributes, ReactNode } from "react";

import { cn } from "../../lib/cn";

type InputProps = InputHTMLAttributes<HTMLInputElement> & {
  /** Always visible: a placeholder is not a label. */
  label: string;
  hint?: string;
  error?: string;
  /** Unit shown beside the value, as it would be on a lab report. */
  unit?: ReactNode;
};

export function Input({ label, hint, error, unit, className, id, ...props }: InputProps) {
  const generatedId = useId();
  const inputId = id ?? generatedId;
  const hintId = `${inputId}-hint`;
  const errorId = `${inputId}-error`;

  return (
    <div className="flex flex-col gap-1">
      <Label.Root htmlFor={inputId} className="text-sm font-medium text-ink">
        {label}
      </Label.Root>
      <div className="flex items-center gap-2">
        <input
          id={inputId}
          aria-invalid={error ? true : undefined}
          aria-describedby={cn(hint && hintId, error && errorId) || undefined}
          className={cn(
            "min-h-[var(--touch-target)] w-full rounded-[var(--radius-md)] px-3",
            "border bg-surface-raised text-ink placeholder:text-ink-muted",
            error ? "border-flag-alert" : "border-border-strong",
            "font-body [font-variant-numeric:tabular-nums]",
            className,
          )}
          {...props}
        />
        {unit ? <span className="shrink-0 text-sm text-ink-muted">{unit}</span> : null}
      </div>
      {hint ? (
        <p id={hintId} className="text-sm text-ink-muted">
          {hint}
        </p>
      ) : null}
      {/* Beside the field that failed, never only in a summary at the top. */}
      {error ? (
        <p id={errorId} role="alert" className="text-sm text-flag-alert">
          {error}
        </p>
      ) : null}
    </div>
  );
}
