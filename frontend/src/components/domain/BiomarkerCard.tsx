import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";

import type { DashboardItem } from "../../lib/api/types";
import { formatDate, formatRange, formatValue, toNumber } from "../../lib/format";
import { Card } from "../ui/Card";
import { FlagChip } from "../ui/FlagChip";
import { Sparkline } from "../ui/Sparkline";

export function BiomarkerCard({ item }: { item: DashboardItem }) {
  const { t, i18n } = useTranslation();
  const locale = i18n.resolvedLanguage ?? "pt-PT";
  const values = item.sparkline.map((point) => toNumber(point.value));
  const range = formatRange(item.biomarker.ref_min, item.biomarker.ref_max, locale);

  return (
    <Card className="flex flex-col gap-3">
      <div className="flex items-start justify-between gap-3">
        <Link
          to={`/biomarkers/${item.biomarker.id}`}
          className="font-display text-lg text-ink hover:text-primary"
        >
          {item.biomarker.name}
        </Link>
        <FlagChip
          flag={item.flag}
          label={item.flag ? t(`flags.${item.flag}`) : t("flags.unclassified")}
        />
      </div>

      <p className="flex items-baseline gap-2">
        <span className="data text-2xl text-ink">{formatValue(item.value, locale)}</span>
        <span className="text-sm text-ink-muted">{item.unit}</span>
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

      <p className="text-sm text-ink-muted">
        {formatDate(item.collected_on, locale)}
        {range ? ` · ${t("biomarker.reference")} ${range}` : ""}
      </p>
    </Card>
  );
}
