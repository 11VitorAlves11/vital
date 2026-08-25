import type { HTMLAttributes, ReactNode } from "react";

import { cn } from "../../lib/cn";

type CardProps = HTMLAttributes<HTMLDivElement> & {
  title?: ReactNode;
  action?: ReactNode;
};

export function Card({ title, action, className, children, ...props }: CardProps) {
  return (
    <div
      className={cn(
        "rounded-[var(--radius-lg)] border border-border bg-surface-raised p-4",
        "shadow-[var(--shadow-card)]",
        className,
      )}
      {...props}
    >
      {title || action ? (
        <div className="mb-3 flex items-start justify-between gap-2">
          {title ? <h2 className="font-display text-lg text-ink">{title}</h2> : <span />}
          {action}
        </div>
      ) : null}
      {children}
    </div>
  );
}
