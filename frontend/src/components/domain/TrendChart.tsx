import { useTranslation } from "react-i18next";
import {
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { Intervention, ReferenceBand } from "../../lib/api/types";
import { formatDate, formatValue } from "../../lib/format";
import {
  interventionOverlayElements,
  momentElements,
  referenceBandElements,
} from "./ReferenceBand";

/** A point event drawn as a vertical rule: a weigh-in, a photo, anything that
 *  happened inside the plotted period but is not a point of this series. */
export type TrendMoment = { id: string; timestamp: number; label: string };

/** The step boundaries near enough to the data to be worth an axis.
 *
 * Every edge would stretch the axis over a scale the reader is nowhere near:
 * vitamin D's "suficiência" runs to 100 ng/mL, and a history sitting between 18
 * and 38 would be squeezed into the bottom third of the plot to make room for a
 * limit it never approaches. One data range's worth of headroom keeps the
 * boundaries the values are actually near — which is the only reason the scale
 * is on the chart — and drops the ones they are not.
 */
function nearbyBandEdges(values: number[], bands: ReferenceBand[]): number[] {
  if (values.length === 0) return [];
  const low = Math.min(...values);
  const high = Math.max(...values);
  const reach = high - low || Math.abs(high) || 1;
  return bands
    .flatMap((band) => [band.min, band.max])
    .filter((edge): edge is number => edge !== null && edge >= low - reach && edge <= high + reach);
}

/** Pads the range, then rounds outward to a round step, so the axis reads
 * "10" and "16" rather than "10,05" and "15,45". */
function paddedDomain(low: number, high: number): [number, number] {
  const spread = high - low || Math.abs(high) || 1;
  const step = 10 ** Math.floor(Math.log10(spread * 0.2));
  // Padding must not invent a negative axis under measurements that cannot be
  // negative — it reads as an error and wastes half the plot.
  const padded = low >= 0 ? Math.max(low - spread * 0.1, 0) : low - spread * 0.1;
  return [Math.floor(padded / step) * step, Math.ceil((high + spread * 0.1) / step) * step];
}

export type TrendPoint = {
  /** Milliseconds, so intervention overlays land on a real time axis. */
  timestamp: number;
  value: number;
  refMin: number | null;
  refMax: number | null;
  label?: string | null;
};

type TrendChartProps = {
  name: string;
  unit: string;
  points: TrendPoint[];
  interventions: Intervention[];
  canonicalMin?: number | null;
  canonicalMax?: number | null;
  /** An ordinal scale, drawn instead of the range when the marker has one. */
  bands?: ReferenceBand[] | null;
  moments?: TrendMoment[];
};

export function TrendChart({
  name,
  unit,
  points,
  interventions,
  canonicalMin = null,
  canonicalMax = null,
  bands = null,
  moments = [],
}: TrendChartProps) {
  const { t, i18n } = useTranslation();
  const locale = i18n.resolvedLanguage ?? "pt-PT";

  const data = points.map((point) => ({
    ...point,
    // Recharts draws a shaded area from a [low, high] pair.
    range:
      point.refMin !== null && point.refMax !== null
        ? ([point.refMin, point.refMax] as [number, number])
        : null,
  }));

  const first = points[0];
  const last = points[points.length - 1];
  const summary = t("chart.trendSummary", {
    name,
    unit,
    count: points.length,
    first: formatValue(first?.value, locale),
    last: formatValue(last?.value, locale),
    firstDate: first ? formatDate(new Date(first.timestamp).toISOString(), locale) : "",
    lastDate: last ? formatDate(new Date(last.timestamp).toISOString(), locale) : "",
  });

  const domainStart = first?.timestamp ?? 0;
  const domainEnd = last?.timestamp ?? 0;

  // The reference band is the signature element, so the axis has to contain it:
  // scaled to the values alone, a limit outside their spread is simply not drawn.
  const values = points.map((point) => point.value);
  const bounds = [
    ...values,
    ...points.flatMap((point) => [point.refMin, point.refMax]),
    canonicalMin,
    canonicalMax,
    ...(bands ? nearbyBandEdges(values, bands) : []),
  ].filter((value): value is number => value !== null && Number.isFinite(value));
  const yDomain = paddedDomain(Math.min(...bounds), Math.max(...bounds));

  return (
    <div
      role="img"
      aria-label={summary}
      tabIndex={0}
      className="h-72 w-full rounded-[var(--radius-md)] focus-visible:outline-2"
    >
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={data} margin={{ top: 24, right: 16, bottom: 8, left: 0 }}>
          <CartesianGrid stroke="var(--color-border)" strokeDasharray="3 3" vertical={false} />
          <XAxis
            dataKey="timestamp"
            type="number"
            scale="time"
            domain={["dataMin", "dataMax"]}
            tickFormatter={(value: number) => formatDate(new Date(value).toISOString(), locale)}
            stroke="var(--color-border-strong)"
            tick={{ fill: "var(--color-ink-muted)", fontSize: 12 }}
          />
          <YAxis
            stroke="var(--color-border-strong)"
            tick={{ fill: "var(--color-ink-muted)", fontSize: 12 }}
            width={56}
            domain={yDomain}
            tickFormatter={(value: number) => formatValue(value, locale)}
          />
          {interventionOverlayElements({ interventions, domainStart, domainEnd })}
          {momentElements(moments, domainStart, domainEnd)}
          {referenceBandElements({
            hasLabRange: data.some((point) => point.range !== null),
            canonicalMin,
            canonicalMax,
            minLabel: (value) => t("chart.min", { value: formatValue(value, locale) }),
            maxLabel: (value) => t("chart.max", { value: formatValue(value, locale) }),
            bands,
            domain: yDomain,
          })}
          <Line
            type="monotone"
            dataKey="value"
            stroke="var(--color-primary)"
            strokeWidth={2}
            dot={{ r: 3, fill: "var(--color-primary)" }}
            activeDot={{ r: 5 }}
            isAnimationActive={false}
          />
          <Tooltip
            contentStyle={{
              background: "var(--color-surface-raised)",
              border: "1px solid var(--color-border-strong)",
              borderRadius: "var(--radius-md)",
              color: "var(--color-ink)",
            }}
            labelFormatter={(value) => formatDate(new Date(Number(value)).toISOString(), locale)}
            formatter={(value: number | string) => [`${formatValue(value, locale)} ${unit}`, name]}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
