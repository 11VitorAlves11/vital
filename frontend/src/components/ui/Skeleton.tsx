import { cn } from "../../lib/cn";

type SkeletonProps = {
  className?: string;
  /** How many bars to stack — shape the placeholder like the content it replaces. */
  lines?: number;
  label?: string;
};

/** Loading placeholder. Never a full-screen spinner, never a blank screen. */
export function Skeleton({ className, lines = 3, label }: SkeletonProps) {
  return (
    <div aria-busy="true" aria-live="polite" className={cn("flex flex-col gap-2", className)}>
      <span className="sr-only">{label ?? "A carregar…"}</span>
      {Array.from({ length: lines }, (_, index) => (
        <span
          key={index}
          aria-hidden="true"
          className="h-4 w-full animate-pulse rounded-[var(--radius-sm)] bg-border"
        />
      ))}
    </div>
  );
}
