import { useId } from "react";
import { useTranslation } from "react-i18next";

import { cn } from "../../lib/cn";

/**
 * The two strokes of the "V". The lighter one crosses the deeper one and the
 * dot finishes the "i", so the symbol reads "Vi" before it reads as a mark.
 */
const DEEP_STROKE =
  "M0.6 14.1L87.1 171.4C91.2 178.9 104.8 188.2 123.3 188.2C141.8 188.2 157.8 178.9 " +
  "153.6 171.4L69.8 19C62.6 5.9 52.1 1.1 26.1 1.1C13.3 1.1 -3.8 6 0.6 14.1Z";
const LIGHT_STROKE =
  "M145.2 78.8L94.3 171.3C89.8 179.5 105.3 188.2 123.3 188.2C141.3 188.2 155.4 179.5 " +
  "159.9 171.3L217.2 67C221.6 59 203.7 55.4 190.3 55.4C167.9 55.4 152.1 66.3 145.2 78.8Z";

/**
 * The symbol on its own — decorative, so it carries no accessible name. Pair it
 * with the wordmark (`Logo`) or with a label of your own wherever it stands in
 * for the product.
 */
export function LogoMark({ className }: { className?: string }) {
  const clipId = useId();
  return (
    <svg
      viewBox="0 0 234.75 188.25"
      className={className}
      aria-hidden="true"
      focusable="false"
    >
      <defs>
        <clipPath id={clipId}>
          <path d={DEEP_STROKE} />
        </clipPath>
      </defs>
      <path d={DEEP_STROKE} fill="var(--logo-deep)" />
      <path d={LIGHT_STROKE} fill="var(--logo-light)" />
      {/* Where the strokes cross, the deep blue shows through the lighter one.
          One opacity keeps the mark on two tokens: a third, blended colour
          would have to be re-measured by hand for every theme. */}
      <g clipPath={`url(#${clipId})`}>
        <path d={LIGHT_STROKE} fill="var(--logo-deep)" fillOpacity="0.35" />
      </g>
      <circle cx="213.85" cy="20.98" r="20.9" fill="var(--logo-deep)" />
    </svg>
  );
}

/** Symbol plus wordmark — the horizontal lockup used across the app chrome. */
export function Logo({ className }: { className?: string }) {
  const { t } = useTranslation();
  return (
    // The mark stands about 1.6x the cap height of the wordmark: matched to it
    // instead, the dot and the foot of the "V" read as a typographic accident.
    <span className={cn("inline-flex items-center gap-3", className)}>
      <LogoMark className="h-7 w-auto shrink-0" />
      <span className="font-display text-xl leading-none font-medium text-primary">
        {t("app.name")}
      </span>
    </span>
  );
}
