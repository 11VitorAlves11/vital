import { CalendarDays, Pill } from "lucide-react";
import { useTranslation } from "react-i18next";

import type { Intervention } from "../../lib/api/types";
import { formatDate } from "../../lib/format";
import type { TrendMoment } from "./TrendChart";

type Props = {
  interventions: Intervention[];
  moments: TrendMoment[];
  start: number;
  end: number;
};

export function InterventionRail({ interventions, moments, start, end }: Props) {
  const { t, i18n } = useTranslation();
  const locale = i18n.resolvedLanguage ?? "pt-PT";
  const visibleInterventions = interventions.filter((item) => {
    const itemStart = Date.parse(item.started_on);
    const itemEnd = item.ended_on ? Date.parse(item.ended_on) : end;
    return itemStart <= end && itemEnd >= start;
  });
  const visibleMoments = moments.filter((item) => item.timestamp >= start && item.timestamp <= end);
  const span = Math.max(end - start, 1);

  if (visibleInterventions.length === 0 && visibleMoments.length === 0) return null;

  return (
    <section className="mt-5 border-t border-border pt-4" aria-labelledby="events-title">
      <h3 id="events-title" className="text-sm font-semibold text-ink">{t("chart.context")}</h3>
      <ul className="mt-3 grid gap-2 sm:grid-cols-2">
        {visibleInterventions.map((item) => (
          <li key={item.id} className="rounded-[var(--radius-md)] bg-band px-3 py-2.5">
            <div className="relative mb-2 h-1.5 overflow-hidden rounded-full bg-border" aria-hidden="true"><span className="absolute h-full rounded-full bg-primary" style={{ left: `${Math.max(0, (Date.parse(item.started_on) - start) / span * 100)}%`, width: `${Math.max(2, (Math.min(item.ended_on ? Date.parse(item.ended_on) : end, end) - Math.max(Date.parse(item.started_on), start)) / span * 100)}%` }} /></div>
            <div className="flex gap-3">
            <Pill size={18} className="mt-0.5 shrink-0 text-primary" aria-hidden="true" />
            <div className="min-w-0 text-sm">
              <p className="font-medium text-ink">{item.name}{item.dose ? ` · ${item.dose}` : ""}</p>
              <p className="text-ink-muted">
                {formatDate(item.started_on, locale)} — {item.ended_on ? formatDate(item.ended_on, locale) : t("interventions.ongoing")}
              </p>
            </div></div>
          </li>
        ))}
      </ul>
      {visibleMoments.length > 0 ? (
        <details className="mt-3 rounded-[var(--radius-md)] border border-border px-3 py-2.5">
          <summary className="flex min-h-8 cursor-pointer items-center gap-2 text-sm font-medium text-ink">
            <CalendarDays size={18} className="shrink-0 text-ink-muted" aria-hidden="true" />
            {t("chart.momentCount", { count: visibleMoments.length })}
          </summary>
          <ul className="mt-2 grid gap-x-6 gap-y-1 border-t border-border pt-2 text-sm text-ink-muted sm:grid-cols-2">
            {visibleMoments.map((item) => <li key={item.id}>{formatDate(new Date(item.timestamp).toISOString(), locale)} · {item.label}</li>)}
          </ul>
        </details>
      ) : null}
    </section>
  );
}
