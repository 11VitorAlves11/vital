import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { CartesianGrid, ComposedChart, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import type { Intervention, ReferenceBand } from "../../lib/api/types";
import { formatDate, formatValue } from "../../lib/format";
import { InterventionRail } from "./InterventionRail";
import { referenceBandElements } from "./ReferenceBand";

export type TrendMoment = { id: string; timestamp: number; label: string };

function nearbyBandEdges(values: number[], bands: ReferenceBand[]): number[] {
  if (values.length === 0) return [];
  const low = Math.min(...values);
  const high = Math.max(...values);
  const reach = high - low || Math.abs(high) || 1;
  return bands.flatMap((band) => [band.min, band.max]).filter((edge): edge is number => edge !== null && edge >= low - reach && edge <= high + reach);
}

function paddedDomain(low: number, high: number): [number, number] {
  const spread = high - low || Math.abs(high) || 1;
  const step = 10 ** Math.floor(Math.log10(spread * 0.2));
  const padded = low >= 0 ? Math.max(low - spread * 0.1, 0) : low - spread * 0.1;
  return [Math.floor(padded / step) * step, Math.ceil((high + spread * 0.1) / step) * step];
}

export type TrendPoint = { timestamp: number; value: number; refMin: number | null; refMax: number | null; label?: string | null };
type Range = "6m" | "1y" | "all";
type TrendChartProps = { name: string; unit: string; points: TrendPoint[]; interventions: Intervention[]; canonicalMin?: number | null; canonicalMax?: number | null; bands?: ReferenceBand[] | null; moments?: TrendMoment[] };

export function TrendChart({ name, unit, points, interventions, canonicalMin = null, canonicalMax = null, bands = null, moments = [] }: TrendChartProps) {
  const { t, i18n } = useTranslation();
  const locale = i18n.resolvedLanguage ?? "pt-PT";
  const [range, setRange] = useState<Range>("all");
  const sorted = useMemo(() => [...points].sort((a, b) => a.timestamp - b.timestamp), [points]);
  const seriesEnd = sorted.at(-1)?.timestamp ?? Date.now();
  const cutoff = range === "6m" ? seriesEnd - 183 * 86400000 : range === "1y" ? seriesEnd - 365 * 86400000 : -Infinity;
  const visible = sorted.filter((point) => point.timestamp >= cutoff);
  const first = visible[0];
  const last = visible.at(-1);
  const domainStart = first?.timestamp ?? seriesEnd;
  const domainEnd = last?.timestamp ?? seriesEnd;
  const data = visible.map((point) => ({ ...point, range: point.refMin !== null && point.refMax !== null ? [point.refMin, point.refMax] as [number, number] : null }));
  const values = visible.map((point) => point.value);
  const bounds = [...values, ...visible.flatMap((point) => [point.refMin, point.refMax]), canonicalMin, canonicalMax, ...(bands ? nearbyBandEdges(values, bands) : [])].filter((value): value is number => value !== null && Number.isFinite(value));
  const yDomain = bounds.length ? paddedDomain(Math.min(...bounds), Math.max(...bounds)) : [0, 1] as [number, number];
  const summary = t("chart.trendSummary", { name, unit, count: visible.length, first: formatValue(first?.value, locale), last: formatValue(last?.value, locale), firstDate: first ? formatDate(new Date(first.timestamp).toISOString(), locale) : "", lastDate: last ? formatDate(new Date(last.timestamp).toISOString(), locale) : "" });
  const delta = first && last ? last.value - first.value : 0;

  return <div>
    <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
      <div className="flex items-center gap-4 text-xs text-ink-muted" aria-label={t("chart.legend")}>
        <span className="flex items-center gap-2"><span className="h-0.5 w-5 bg-primary" />{t("chart.result")}</span>
        {(canonicalMin !== null || canonicalMax !== null || data.some((point) => point.range !== null) || bands) ? <span className="flex items-center gap-2"><span className="size-3 rounded-sm bg-[var(--color-band)]" />{t("chart.referenceBand")}</span> : null}
      </div>
      <div className="inline-flex rounded-[var(--radius-md)] border border-border p-1" aria-label={t("chart.period")}>{(["6m", "1y", "all"] as Range[]).map((option) => <button key={option} type="button" aria-pressed={range === option} onClick={() => setRange(option)} className="min-h-[var(--touch-target)] rounded-[var(--radius-sm)] px-3 text-sm font-medium text-ink-muted hover:text-ink aria-pressed:bg-primary aria-pressed:text-on-primary">{t(`chart.ranges.${option}`)}</button>)}</div>
    </div>
    {visible.length < 4 ? <div role="img" aria-label={summary} tabIndex={0} className="rounded-[var(--radius-lg)] border border-border px-5 py-6 focus-visible:outline-2">
      <p className="text-sm text-ink-muted">{t("chart.limitedHistory", { count: visible.length })}</p>
      <div className="mt-4 flex flex-wrap items-end justify-between gap-4"><p className="metric text-3xl font-semibold text-ink">{formatValue(last?.value, locale)} <span className="text-base">{unit}</span></p>{visible.length > 1 ? <p className="text-sm text-ink-muted">{t(delta < 0 ? "chart.decreasedInPeriod" : delta > 0 ? "chart.increasedInPeriod" : "chart.unchangedInPeriod", { value: formatValue(Math.abs(delta), locale), unit })}</p> : null}</div>
    </div> : <div role="img" aria-label={summary} tabIndex={0} className="h-72 w-full rounded-[var(--radius-md)] focus-visible:outline-2">
      <ResponsiveContainer width="100%" height="100%"><ComposedChart data={data} margin={{ top: 20, right: 12, bottom: 8, left: 0 }}>
        <CartesianGrid stroke="var(--color-border)" strokeDasharray="3 3" vertical={false} />
        <XAxis dataKey="timestamp" type="number" scale="time" domain={["dataMin", "dataMax"]} tickFormatter={(value: number) => formatDate(new Date(value).toISOString(), locale)} stroke="var(--color-border-strong)" tick={{ fill: "var(--color-ink-muted)", fontSize: 12, fontFamily: "Atkinson Hyperlegible" }} />
        <YAxis stroke="var(--color-border-strong)" tick={{ fill: "var(--color-ink-muted)", fontSize: 12, fontFamily: "Atkinson Hyperlegible" }} width={56} domain={yDomain} tickFormatter={(value: number) => formatValue(value, locale)} />
        {referenceBandElements({ hasLabRange: data.some((point) => point.range !== null), canonicalMin, canonicalMax, minLabel: (value) => t("chart.min", { value: formatValue(value, locale) }), maxLabel: (value) => t("chart.max", { value: formatValue(value, locale) }), bands, domain: yDomain })}
        <Line type="monotone" dataKey="value" stroke="var(--color-primary)" strokeWidth={2.5} dot={{ r: 3, fill: "var(--color-primary)" }} activeDot={{ r: 5 }} isAnimationActive={false} />
        <Tooltip contentStyle={{ background: "var(--color-surface-raised)", border: "1px solid var(--color-border-strong)", borderRadius: "var(--radius-md)", color: "var(--color-ink)", fontFamily: "Atkinson Hyperlegible" }} labelFormatter={(value) => formatDate(new Date(Number(value)).toISOString(), locale)} formatter={(value: number | string) => [`${formatValue(value, locale)} ${unit}`, name]} />
      </ComposedChart></ResponsiveContainer>
    </div>}
    <InterventionRail interventions={interventions} moments={moments} start={domainStart} end={domainEnd} />
  </div>;
}
