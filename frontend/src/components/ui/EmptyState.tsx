import type { ReactNode } from "react";

type EmptyStateProps = {
  title: string;
  /** The next action, spelled out — "no data" on its own is a dead end. */
  description?: string;
  action?: ReactNode;
  icon?: ReactNode;
};

export function EmptyState({ title, description, action, icon }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center gap-3 rounded-[var(--radius-lg)] border border-dashed border-border-strong p-8 text-center">
      {icon}
      <h3 className="font-display text-lg text-ink">{title}</h3>
      {description ? <p className="max-w-prose text-ink-muted">{description}</p> : null}
      {action}
    </div>
  );
}
