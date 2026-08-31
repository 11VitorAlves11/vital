import { useTranslation } from "react-i18next";
import { useParams } from "react-router-dom";

import { TrendChart } from "../components/domain/TrendChart";
import { Card } from "../components/ui/Card";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorState } from "../components/ui/ErrorState";
import { FlagChip } from "../components/ui/FlagChip";
import { LinkButton } from "../components/ui/LinkButton";
import { Skeleton } from "../components/ui/Skeleton";
import { biomarkers } from "../lib/api";
import type { BiomarkerPoint } from "../lib/api/types";
import { formatDate, formatRange, formatValue, toNumber } from "../lib/format";
import { useAsync } from "../lib/useAsync";
import { useIsDesktop } from "../lib/useMediaQuery";

export function BiomarkerDetail() {
  const { id } = useParams();
  const { t, i18n } = useTranslation();
  const locale = i18n.resolvedLanguage ?? "pt-PT";
  const isDesktop = useIsDesktop();
  const biomarkerId = Number(id);
  const { data, loading, error, reload } = useAsync(
    () => biomarkers.series(biomarkerId),
    [biomarkerId],
  );

  if (loading) return <Skeleton lines={8} label={t("common.loading")} />;
  if (error || !data) return <ErrorState onRetry={reload} />;

  const { biomarker, points, interventions } = data;
  // The whole series is plotted on one scale, whatever unit each report used.
  const unit = data.unit;
  const canonical = formatRange(biomarker.ref_min, biomarker.ref_max, locale);
  const newestFirst = [...points].reverse();
  // A point in a unit the catalogue cannot convert has no place on that scale,
  // so it is left out of the line rather than plotted at the wrong height.
  const plotted = points.filter((point) => point.canonical_value !== null);

  const flagLabel = (point: BiomarkerPoint) =>
    point.flag ? t(`flags.${point.flag}`) : t("flags.unclassified");

  /** What the reference column says, which depends on the shape of the interval. */
  const referenceLabel = (point: BiomarkerPoint) => {
    if (point.reference_kind === "ordinal_bands") return point.band_label;
    return formatRange(point.ref_min, point.ref_max, locale);
  };

  return (
    <section className="flex flex-col gap-6">
      <header className="flex flex-col gap-1">
        <h1 className="font-display text-2xl leading-tight font-medium text-ink">{biomarker.name}</h1>
        <p className="text-sm text-ink-muted">
          {t(`categories.${biomarker.category}`)}
          {/* A marker read on a named scale has no single range to quote: the
              steps are the reference, and they are drawn on the chart below. */}
          {biomarker.reference_bands
            ? ` · ${t("biomarker.ordinalScale")}: ${biomarker.reference_bands
                .map((band) => band.label)
                .join(" · ")}`
            : canonical
              ? ` · ${t("biomarker.canonicalRange")}: ${canonical} ${biomarker.canonical_unit}`
              : ""}
        </p>
        {biomarker.notes ? <p className="text-sm text-ink-muted">{biomarker.notes}</p> : null}
      </header>

      {points.length === 0 ? (
        <EmptyState
          title={t("biomarker.emptyTitle")}
          description={t("biomarker.emptyDescription")}
          action={<LinkButton to="/reports">{t("reports.new")}</LinkButton>}
        />
      ) : (
        <>
          <Card title={t("biomarker.trendTitle")}>
            <TrendChart
              name={biomarker.name}
              unit={unit}
              canonicalMin={biomarker.ref_min === null ? null : toNumber(biomarker.ref_min)}
              canonicalMax={biomarker.ref_max === null ? null : toNumber(biomarker.ref_max)}
              bands={biomarker.reference_bands}
              interventions={interventions}
              points={plotted.map((point) => ({
                timestamp: new Date(point.date).getTime(),
                value: toNumber(point.canonical_value),
                refMin: point.canonical_ref_min === null ? null : toNumber(point.canonical_ref_min),
                refMax: point.canonical_ref_max === null ? null : toNumber(point.canonical_ref_max),
              }))}
            />
            {data.has_unconverted_points ? (
              <p className="mt-2 text-sm text-ink-muted">
                {t("biomarker.unconvertedPoints", {
                  count: points.length - plotted.length,
                  unit,
                })}
              </p>
            ) : null}
            {interventions.length > 0 ? (
              <p className="mt-2 text-sm text-ink-muted">
                {t("chart.interventions")}:{" "}
                {interventions.map((intervention) => intervention.name).join(" · ")}
              </p>
            ) : null}
          </Card>

          {/* The history is the chart's textual alternative, not an optional extra —
              a dense table on a desktop, stacked cards on a phone, never both at once. */}
          <Card title={t("biomarker.history")}>
            {isDesktop ? (
              <div className="overflow-x-auto">
                <table className="w-full text-left">
                  <thead className="text-sm text-ink-muted">
                    <tr>
                      <th scope="col" className="py-2">
                        {t("biomarker.date")}
                      </th>
                      <th scope="col" className="py-2">
                        {t("biomarker.value")}
                      </th>
                      <th scope="col" className="py-2">
                        {t("biomarker.reference")}
                      </th>
                      <th scope="col" className="py-2">
                        {t("biomarker.lab")}
                      </th>
                      <th scope="col" className="py-2">
                        {t("biomarker.flag")}
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {newestFirst.map((point) => (
                      <tr key={point.report_id} className="border-t border-border">
                        <td className="py-2">{formatDate(point.date, locale)}</td>
                        <td className="data py-2">
                          {formatValue(point.value, locale)} {point.unit}
                        </td>
                        <td className="py-2 text-ink-muted">
                          {referenceLabel(point) ? (
                            <span className={point.band_label ? undefined : "data"}>
                              {referenceLabel(point)}
                            </span>
                          ) : (
                            t("biomarker.noRange")
                          )}
                        </td>
                        <td className="py-2 text-ink-muted">{point.lab_name}</td>
                        <td className="py-2">
                          <FlagChip flag={point.flag} label={flagLabel(point)} />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <ul className="flex flex-col gap-3">
                {newestFirst.map((point) => (
                  <li key={point.report_id} className="border-t border-border pt-3">
                    <div className="flex items-center justify-between gap-2">
                      <span className="data text-lg text-ink">
                        {formatValue(point.value, locale)} {point.unit}
                      </span>
                      <FlagChip flag={point.flag} label={flagLabel(point)} />
                    </div>
                    <p className="text-sm text-ink-muted">
                      {formatDate(point.date, locale)} · {point.lab_name}
                      {point.band_label ? ` · ${point.band_label}` : ""}
                    </p>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </>
      )}
    </section>
  );
}
