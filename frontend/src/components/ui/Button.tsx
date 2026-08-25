import type { ButtonHTMLAttributes, ReactNode } from "react";

import { cn } from "../../lib/cn";

export type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant;
  /** Rendered before the label; decorative icons must carry aria-hidden themselves. */
  icon?: ReactNode;
  loading?: boolean;
};

const VARIANTS: Record<ButtonVariant, string> = {
  primary: "bg-primary text-on-primary hover:bg-primary-deep",
  secondary: "border border-border-strong text-ink hover:bg-band",
  ghost: "text-ink hover:bg-band",
  danger: "border border-flag-alert text-flag-alert hover:bg-flag-alert hover:text-on-primary",
};

/** Shared so a link that acts as a button looks like one without becoming one. */
export function buttonClasses(variant: ButtonVariant = "primary", className?: string): string {
  return cn(
    // The 44px floor is the mobile touch target, not a visual preference.
    "inline-flex min-h-[var(--touch-target)] items-center justify-center gap-2",
    "rounded-[var(--radius-md)] px-4 text-base font-medium",
    "transition-colors duration-[var(--duration-fast)] ease-standard",
    "disabled:cursor-not-allowed disabled:opacity-60",
    VARIANTS[variant],
    className,
  );
}

export function Button({
  variant = "primary",
  icon,
  loading = false,
  className,
  children,
  disabled,
  type = "button",
  ...props
}: ButtonProps) {
  return (
    <button
      type={type}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      className={buttonClasses(variant, className)}
      {...props}
    >
      {icon}
      {children}
    </button>
  );
}
