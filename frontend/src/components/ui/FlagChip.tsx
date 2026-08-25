import { cn } from "../../lib/cn";

/** Lab results are low/normal/high; body composition adds the intermediate warn. */
export type Flag = "low" | "normal" | "high" | "warn" | "alert" | null;

type FlagChipProps = {
  flag: Flag;
  /** Always shown. Colour reinforces it; it never carries the meaning alone. */
  label: string;
  className?: string;
};

const TONE: Record<string, string> = {
  normal: "border-flag-normal text-flag-normal",
  warn: "border-flag-warn text-flag-warn",
  alert: "border-flag-alert text-flag-alert",
};

const DOT: Record<string, string> = {
  normal: "bg-flag-normal",
  warn: "bg-flag-warn",
  alert: "bg-flag-alert",
};

function toneOf(flag: Flag): "normal" | "warn" | "alert" | "muted" {
  if (flag === "normal") return "normal";
  if (flag === "warn") return "warn";
  if (flag === "low" || flag === "high" || flag === "alert") return "alert";
  return "muted";
}

export function FlagChip({ flag, label, className }: FlagChipProps) {
  const tone = toneOf(flag);
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-[var(--radius-sm)] border px-2 py-0.5 text-sm",
        tone === "muted" ? "border-border-strong text-ink-muted" : TONE[tone],
        className,
      )}
    >
      <span
        aria-hidden="true"
        className={cn("size-2 rounded-full", tone === "muted" ? "bg-ink-muted" : DOT[tone])}
      />
      {label}
    </span>
  );
}
