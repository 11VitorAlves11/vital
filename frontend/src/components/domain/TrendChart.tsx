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

import type { Intervention } from "../../lib/api/types";
import { formatDate, formatValue } from "../../lib/format";
import { interventionOverlayElements, referenceBandElements } from "./ReferenceBand";

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
};

export function TrendChart({
  name,
  unit,
  points,
  interventions,
  canonicalMin = null,
  canonicalMax = null,
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
            domain={["auto", "auto"]}
          />
          {interventionOverlayElements({ interventions, domainStart, domainEnd })}
          {referenceBandElements({
            hasLabRange: data.some((point) => point.range !== null),
            canonicalMin,
            canonicalMax,
            minLabel: (value) => t("chart.min", { value: formatValue(value, locale) }),
            maxLabel: (value) => t("chart.max", { value: formatValue(value, locale) }),
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
