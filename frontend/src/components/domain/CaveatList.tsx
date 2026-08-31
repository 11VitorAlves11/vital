import { Info } from "lucide-react";
import { useTranslation } from "react-i18next";

import type { Caveat } from "../../lib/api/types";
import { cn } from "../../lib/cn";

/**
 * Why a number may not mean what it appears to: the fast nobody recorded, the
 * draw at the wrong hour, the assay that changed between this collection and the
 * last.
 *
 * Deliberately quiet. None of these say the value is wrong — a red warning
 * beside a normal result would be read as an alert, and within a week the real
 * alerts would be read as this.
 */
export function CaveatList({ caveats, className }: { caveats?: Caveat[]; className?: string }) {
  const { t } = useTranslation();
  if (!caveats || caveats.length === 0) return null;

  return (
    <ul className={cn("flex flex-col gap-1", className)}>
      {caveats.map((caveat) => (
        <li key={caveat.code} className="flex items-start gap-1.5 text-sm text-ink-muted">
          <Info size={16} aria-hidden="true" className="mt-0.5 shrink-0" />
          {/* An unknown code still says something: the server may know a caveat
              this build does not, and silence would be the worst of the options. */}
          <span>{t([`caveats.${caveat.code}`, "caveats.unknown"], caveat.values)}</span>
        </li>
      ))}
    </ul>
  );
}
