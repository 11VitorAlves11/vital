import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";

import type { DashboardItem } from "../../lib/api/types";
import { formatDate, formatRange, formatValue, toNumber } from "../../lib/format";
import { Card } from "../ui/Card";
import { FlagChip } from "../ui/FlagChip";
import { Sparkline } from "../ui/Sparkline";

/**
 * Three tiers, read in this order: the measurement, the interval it is judged
 * against, and where it came from. Everything competing at one weight was what
 * made the grid unreadable.
 */
export function BiomarkerCard({ item }: { item: DashboardItem }) {
  const { t, i18n } = useTranslation();
  const locale = i18n.resolvedLanguage ?? "pt-PT";
  const values = item.sparkline.map((point) => toNumber(point.value));
  // On a named scale the step is the reference — "insuficiência" says more than
  // the two numbers around it, and the numbers alone would say the wrong thing.
  const range =
    item.band_label ?? formatRange(item.biomarker.ref_min, item.biomarker.ref_max, locale);

  return (
    <Card className="flex flex-col gap-3">
      <div className="flex items-start justify-between gap-3">
        <Link
          to={`/biomarkers/${item.biomarker.id}`}
          className="text-base font-medium text-ink underline-offset-4 hover:text-primary hover:underline"
        >
          {item.biomarker.name}
        </Link>
        <FlagChip
          flag={item.flag}
          label={item.flag ? t(`flags.${item.flag}`) : t("flags.unclassified")}
        />
      </div>

      {/* The datum, at the scale it deserves on a page of measurements. */}
      <p className="flex items-baseline gap-1.5">
        <span className="metric text-3xl leading-none font-medium text-ink">
          {formatValue(item.value, locale)}
        </span>
        <span className="text-sm text-ink">{item.unit}</span>
      </p>

      <Sparkline
        values={values}
        summary={t("dashboard.sparklineSummary", {
          count: values.length,
          name: item.biomarker.name,
          first: formatValue(item.sparkline[0]?.value, locale),
          last: formatValue(item.sparkline[item.sparkline.length - 1]?.value, locale),
          unit: item.unit,
        })}
      />

      <div className="mt-auto flex flex-wrap items-baseline justify-between gap-x-3 border-t border-border pt-3 text-sm">
        {range ? (
          <span className="text-ink">
            {t("biomarker.reference")}{" "}
            <span className={item.band_label ? undefined : "metric"}>{range}</span>
          </span>
        ) : (
          <span className="text-ink-muted">{t("biomarker.noRange")}</span>
        )}
        <span className="text-ink-muted">{formatDate(item.collected_on, locale)}</span>
      </div>
    </Card>
  );
}
