import { useTranslation } from "react-i18next";
import { useParams } from "react-router-dom";

import { TrendChart } from "../components/domain/TrendChart";
import { Card } from "../components/ui/Card";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorState } from "../components/ui/ErrorState";
import { FlagChip } from "../components/ui/FlagChip";
import { Skeleton } from "../components/ui/Skeleton";
import { body } from "../lib/api";
import { formatDateTime, formatValue, toNumber } from "../lib/format";
import { useAsync } from "../lib/useAsync";

export function BodyMetricDetail() {
  const { id } = useParams();
  const { t, i18n } = useTranslation();
  const locale = i18n.resolvedLanguage ?? "pt-PT";
  const metricId = Number(id);
  const { data, loading, error, reload } = useAsync(() => body.series(metricId), [metricId]);

  if (loading) return <Skeleton lines={8} label={t("common.loading")} />;
  if (error || !data) return <ErrorState onRetry={reload} />;

  const { metric, points, interventions } = data;
  // The "normal" band gives the shaded range; the rest are drawn as history rows.
  const normalBand = metric.bands?.find((band) => band.flag === "normal") ?? null;

  return (
    <section className="flex flex-col gap-6">
      <header className="flex flex-col gap-1">
        <h1 className="font-display text-2xl text-ink">{metric.name}</h1>
        <p className="text-sm text-ink-muted">
          {metric.unit}
          {metric.source ? ` · ${metric.source}` : ` · ${t("body.noClinicalReference")}`}
        </p>
        {metric.bands === null ? (
          <p className="text-sm text-ink-muted">{t("body.trendOnlyHint")}</p>
        ) : null}
      </header>

      {points.length === 0 ? (
        <EmptyState title={t("body.emptyTitle")} description={t("body.emptyDescription")} />
      ) : (
        <>
          <Card title={t("biomarker.trendTitle")}>
            <TrendChart
              name={metric.name}
              unit={metric.unit}
              canonicalMin={normalBand?.min ?? null}
              canonicalMax={normalBand?.max ?? null}
              interventions={interventions}
              points={points.map((point) => ({
                timestamp: new Date(point.date).getTime(),
                value: toNumber(point.value),
                refMin: normalBand?.min ?? null,
                refMax: normalBand?.max ?? null,
              }))}
            />
            {interventions.length > 0 ? (
              <p className="mt-2 text-sm text-ink-muted">
                {t("chart.interventions")}:{" "}
                {interventions.map((intervention) => intervention.name).join(" · ")}
              </p>
            ) : null}
          </Card>

          <Card title={t("biomarker.history")}>
            <ul className="flex flex-col">
              {[...points].reverse().map((point) => (
                <li
                  key={point.scan_id}
                  className="flex flex-wrap items-center justify-between gap-2 border-t border-border py-3"
                >
                  <span className="text-ink-muted">{formatDateTime(point.date, locale)}</span>
                  <span className="flex items-center gap-3">
                    <span className="data text-ink">
                      {formatValue(point.value, locale)} {metric.unit}
                    </span>
                    {point.label ? <FlagChip flag={point.flag} label={point.label} /> : null}
                  </span>
                </li>
              ))}
            </ul>
          </Card>
        </>
      )}
    </section>
  );
}
