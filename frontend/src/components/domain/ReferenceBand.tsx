import type { ReactElement } from "react";
import { Area, ReferenceArea, ReferenceLine } from "recharts";

import type { Intervention } from "../../lib/api/types";

type BandOptions = {
  /** Per-point range the lab reported, plotted as a shaded area. */
  hasLabRange: boolean;
  /** Catalogue range for the user's sex, drawn as dashed limit lines. */
  canonicalMin: number | null;
  canonicalMax: number | null;
  minLabel: (value: number) => string;
  maxLabel: (value: number) => string;
};

/**
 * The signature element. Returned as an array of Recharts elements rather than a
 * component, because Recharts identifies its children by type and would not look
 * inside a wrapper of ours.
 *
 * The shading sits at 1.12:1 against the surface — decoration, not the signal.
 * The limits are therefore also drawn as labelled lines, so the range stays
 * readable without telling the shade apart from the background.
 */
export function referenceBandElements({
  hasLabRange,
  canonicalMin,
  canonicalMax,
  minLabel,
  maxLabel,
}: BandOptions): ReactElement[] {
  const elements: ReactElement[] = [];

  if (hasLabRange) {
    elements.push(
      <Area
        key="lab-range"
        type="monotone"
        dataKey="range"
        stroke="none"
        fill="var(--color-band)"
        isAnimationActive={false}
        activeDot={false}
        legendType="none"
      />,
    );
  }

  for (const [key, value, label] of [
    ["canonical-min", canonicalMin, minLabel],
    ["canonical-max", canonicalMax, maxLabel],
  ] as const) {
    if (value === null || Number.isNaN(value)) continue;
    elements.push(
      <ReferenceLine
        key={key}
        y={value}
        stroke="var(--color-border-strong)"
        strokeDasharray="6 4"
        label={{
          value: label(value),
          position: "insideTopLeft",
          fill: "var(--color-ink-muted)",
          fontSize: 12,
        }}
      />,
    );
  }

  return elements;
}

type OverlayOptions = {
  interventions: Intervention[];
  domainStart: number;
  domainEnd: number;
};

/** Vertical bands for the interventions running over the plotted period, each
 * with a visible label — the correlation cannot depend on recognising a colour. */
export function interventionOverlayElements({
  interventions,
  domainStart,
  domainEnd,
}: OverlayOptions): ReactElement[] {
  // A single data point gives the axis no width, and a zero-width band is a
  // floating label pretending to be a period.
  if (domainEnd <= domainStart) return [];

  return interventions.map((intervention, index) => {
    const start = Math.max(new Date(intervention.started_on).getTime(), domainStart);
    const end = Math.min(
      intervention.ended_on ? new Date(intervention.ended_on).getTime() : domainEnd,
      domainEnd,
    );
    return (
      <ReferenceArea
        key={intervention.id}
        x1={start}
        x2={end}
        fill="var(--color-primary)"
        // Overlapping periods stack their fills, so each one stays faint enough
        // that four at once do not paint over the reference band underneath.
        fillOpacity={0.06}
        stroke="var(--color-primary)"
        strokeOpacity={0.35}
        label={{
          value: intervention.dose
            ? `${intervention.name} · ${intervention.dose}`
            : intervention.name,
          // Anchored to where the period starts and stepped down per band:
          // centred on a shared top edge, concurrent labels overwrite each other
          // into an unreadable smear, and the overlay stops being a signal.
          position: "insideTopLeft",
          dy: (index % 4) * 14,
          dx: 4,
          fill: "var(--color-ink-muted)",
          fontSize: 11,
        }}
      />
    );
  });
}
