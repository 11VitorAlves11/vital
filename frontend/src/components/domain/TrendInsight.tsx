import { ArrowDownRight, ArrowRight, ArrowUpRight } from "lucide-react";
import { useTranslation } from "react-i18next";

import { formatDate, formatValue } from "../../lib/format";
import { FlagChip, type Flag } from "../ui/FlagChip";

type Props = {
  value: number;
  unit: string;
  date: string;
  previousValue?: number;
  flag?: Flag;
  flagLabel?: string | null;
};

export function TrendInsight({ value, unit, date, previousValue, flag = null, flagLabel }: Props) {
  const { t, i18n } = useTranslation();
  const locale = i18n.resolvedLanguage ?? "pt-PT";
  const delta = previousValue === undefined ? null : value - previousValue;
  const percent = previousValue && delta !== null ? (delta / Math.abs(previousValue)) * 100 : null;
  const Direction = delta === null || delta === 0 ? ArrowRight : delta < 0 ? ArrowDownRight : ArrowUpRight;

  return (
    <div className="mb-6 grid gap-4 rounded-[var(--radius-lg)] bg-band p-4 sm:grid-cols-[1fr_auto] sm:items-center">
      <div>
        <p className="text-sm text-ink-muted">{t("chart.latestReading", { date: formatDate(date, locale) })}</p>
        <div className="mt-1 flex flex-wrap items-center gap-3">
          <span className="metric text-3xl font-semibold text-ink">{formatValue(value, locale)} <span className="text-base font-medium">{unit}</span></span>
          {flagLabel ? <FlagChip flag={flag} label={flagLabel} /> : null}
        </div>
      </div>
      {delta !== null ? (
        <div className="flex items-center gap-2 sm:text-right">
          <Direction size={22} className="text-primary" aria-hidden="true" />
          <div>
            <p className="metric font-semibold text-ink">{delta > 0 ? "+" : ""}{formatValue(delta, locale)} {unit}</p>
            <p className="text-sm text-ink-muted">{percent === null ? t("chart.sincePrevious") : t("chart.changeSincePrevious", { percent: formatValue(Math.abs(percent), locale) })}</p>
          </div>
        </div>
      ) : <p className="text-sm text-ink-muted">{t("chart.firstReading")}</p>}
    </div>
  );
}
