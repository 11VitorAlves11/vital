import { ArrowDownRight, ArrowUpRight, CalendarClock, CheckCircle2, FlaskConical, Star, X } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { Card } from "../components/ui/Card";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorState } from "../components/ui/ErrorState";
import { FlagChip } from "../components/ui/FlagChip";
import { LinkButton } from "../components/ui/LinkButton";
import { Skeleton } from "../components/ui/Skeleton";
import { Sparkline } from "../components/ui/Sparkline";
import { useToast } from "../components/ui/Toast";
import { dashboard, repeats } from "../lib/api";
import type { Dashboard as DashboardData, DashboardItem } from "../lib/api/types";
import { formatDate, formatMonthYear, formatValue, toNumber } from "../lib/format";
import { useAsync } from "../lib/useAsync";

type Change = { item: DashboardItem; kind: "outside" | "returned" | "changed" };

const itemsOf = (data: DashboardData) => data.categories.flatMap((group) => group.items);

function notableChanges(data: DashboardData): Change[] {
  const items = itemsOf(data);
  const priority: Change[] = items
    .filter((item) => item.flag === "low" || item.flag === "high")
    .map((item) => ({ item, kind: "outside" }));
  priority.push(
    ...items
      .filter(
        (item) =>
          item.flag === "normal" &&
          (item.previous_flag === "low" || item.previous_flag === "high"),
      )
      .map((item): Change => ({ item, kind: "returned" })),
  );
  const used = new Set(priority.map(({ item }) => item.biomarker.id));
  priority.push(
    ...items
      .filter((item) => item.percent_change != null && !used.has(item.biomarker.id))
      .sort((a, b) => Math.abs(toNumber(b.percent_change)) - Math.abs(toNumber(a.percent_change)))
      .slice(0, 3)
      .map((item): Change => ({ item, kind: "changed" })),
  );
  return priority.slice(0, 6);
}

function LatestValue({ item }: { item: DashboardItem }) {
  const { t, i18n } = useTranslation();
  const locale = i18n.resolvedLanguage ?? "pt-PT";
  return (
    <div className="flex shrink-0 items-center gap-3">
      <span className="metric text-lg font-medium text-ink">
        {formatValue(item.value, locale)} <span className="text-sm">{item.unit}</span>
      </span>
      <FlagChip flag={item.flag} label={item.flag ? t(`flags.${item.flag}`) : t("flags.unclassified")} />
    </div>
  );
}

export function Dashboard() {
  const { t, i18n } = useTranslation();
  const locale = i18n.resolvedLanguage ?? "pt-PT";
  const notify = useToast();
  const { data, loading, error, reload } = useAsync(() => dashboard.read());
  const [favorites, setFavorites] = useState<number[]>([]);
  const storageKey = "vital-favorites";

  useEffect(() => {
    try {
      setFavorites(JSON.parse(localStorage.getItem(storageKey) ?? "[]") as number[]);
    } catch {
      setFavorites([]);
    }
  }, []);

  const changes = useMemo(() => (data ? notableChanges(data) : []), [data]);
  const favoriteItems = data ? itemsOf(data).filter((item) => favorites.includes(item.biomarker.id)) : [];

  function toggleFavorite(id: number) {
    const next = favorites.includes(id) ? favorites.filter((item) => item !== id) : [...favorites, id];
    setFavorites(next);
    localStorage.setItem(storageKey, JSON.stringify(next));
  }

  async function cancelRepeat(id: string) {
    await repeats.remove(id);
    notify(t("repeats.deleted"));
    reload();
  }

  return (
    <section className="mx-auto w-full max-w-5xl">
      <header className="flex flex-wrap items-end justify-between gap-x-6 gap-y-2">
        <div>
          <h1 className="font-display text-2xl font-semibold leading-tight text-ink">{t("dashboard.title")}</h1>
          <p className="mt-1 text-ink-muted">{t("dashboard.summaryIntro")}</p>
        </div>
        {data ? (
          <p className="text-sm text-ink-muted">
            {data.last_report_on
              ? `${t("dashboard.lastReport")} ${formatDate(data.last_report_on, locale)} · ${t("dashboard.reportCount", { count: data.report_count })}`
              : t("dashboard.never")}
          </p>
        ) : null}
      </header>

      <div className="mt-8 flex flex-col gap-10">
        {loading ? <Skeleton lines={6} label={t("common.loading")} /> : null}
        {error ? <ErrorState onRetry={reload} /> : null}
        {data && data.categories.length === 0 ? (
          <EmptyState
            icon={<FlaskConical size={24} aria-hidden="true" className="text-ink-muted" />}
            title={t("dashboard.emptyTitle")}
            description={t("dashboard.emptyDescription")}
            action={<LinkButton to="/reports">{t("reports.new")}</LinkButton>}
          />
        ) : null}

        {data && data.categories.length > 0 ? (
          <section aria-labelledby="changes-title">
            <h2 id="changes-title" className="font-display text-xl font-semibold text-ink">{t("dashboard.sinceLast")}</h2>
            <p className="mt-1 text-sm text-ink-muted">{t("dashboard.sinceLastHint")}</p>
            <Card className="mt-4 p-0 shadow-none">
              {changes.length ? (
                <ul className="divide-y divide-border">
                  {changes.map(({ item, kind }) => {
                    const percent = item.percent_change == null ? null : toNumber(item.percent_change);
                    const Direction = percent !== null && percent < 0 ? ArrowDownRight : ArrowUpRight;
                    return (
                      <li key={item.biomarker.id} className="flex flex-wrap items-center gap-3 px-4 py-3">
                        {kind === "returned" ? (
                          <CheckCircle2 size={20} className="text-flag-normal" aria-hidden="true" />
                        ) : (
                          <Direction size={20} className={kind === "outside" ? "text-flag-alert" : "text-primary"} aria-hidden="true" />
                        )}
                        <div className="min-w-0 flex-1">
                          <Link to={`/biomarkers/${item.biomarker.id}`} className="font-medium text-ink underline-offset-4 hover:text-primary hover:underline">{item.biomarker.name}</Link>
                          <p className="text-sm text-ink-muted">{t(`dashboard.change.${kind}`, { percent: percent === null ? "" : formatValue(Math.abs(percent), locale) })}</p>
                        </div>
                        <LatestValue item={item} />
                      </li>
                    );
                  })}
                </ul>
              ) : <p className="p-4 text-ink-muted">{t("dashboard.noNotableChanges")}</p>}
            </Card>
          </section>
        ) : null}

        {favoriteItems.length ? (
          <section aria-labelledby="favorites-title">
            <h2 id="favorites-title" className="font-display text-xl font-semibold text-ink">{t("dashboard.favorites")}</h2>
            <Card className="mt-4 p-0 shadow-none">
              <ul className="divide-y divide-border">
                {favoriteItems.map((item) => (
                  <li key={item.biomarker.id} className="grid items-center gap-3 px-4 py-3 sm:grid-cols-[1fr_9rem_auto]">
                    <Link to={`/biomarkers/${item.biomarker.id}`} className="font-medium text-ink hover:text-primary">{item.biomarker.name}</Link>
                    <Sparkline values={item.sparkline.map((point) => toNumber(point.value))} summary={t("dashboard.sparklineSummary", { count: item.sparkline.length, name: item.biomarker.name, first: formatValue(item.sparkline[0]?.value, locale), last: formatValue(item.sparkline.at(-1)?.value, locale), unit: item.unit })} />
                    <LatestValue item={item} />
                  </li>
                ))}
              </ul>
            </Card>
          </section>
        ) : null}

        {data && data.due_repeats.length > 0 ? (
          <section aria-labelledby="repeats-title">
            <h2 id="repeats-title" className="flex items-center gap-2 font-display text-xl font-semibold text-ink"><CalendarClock size={20} aria-hidden="true" className="text-flag-warn" />{t("repeats.dueCount", { count: data.due_repeats.length })}</h2>
            <Card className="mt-4 p-0 shadow-none"><ul className="divide-y divide-border">{data.due_repeats.map((item) => (
              <li key={item.id} className="flex flex-wrap items-center justify-between gap-3 px-4 py-3"><div className="min-w-0 flex-1"><Link to={`/biomarkers/${item.biomarker_id}`} className="font-medium text-ink hover:text-primary">{item.biomarker_name}</Link><p className="text-sm text-ink-muted">{t("repeats.targetLabel", { month: formatMonthYear(item.target_year, item.target_month, locale) })}{item.note ? ` · ${item.note}` : ""}</p></div><button type="button" aria-label={t("repeats.cancel")} onClick={() => void cancelRepeat(item.id)} className="inline-flex size-[var(--touch-target)] items-center justify-center rounded-[var(--radius-md)] text-ink-muted hover:bg-band"><X size={20} aria-hidden="true" /></button></li>
            ))}</ul></Card>
          </section>
        ) : null}

        {data && data.categories.length > 0 ? (
          <section aria-labelledby="all-results-title">
            <h2 id="all-results-title" className="font-display text-xl font-semibold text-ink">{t("dashboard.allResults")}</h2>
            <p className="mt-1 text-sm text-ink-muted">{t("dashboard.favoriteHint")}</p>
            <div className="mt-4 divide-y divide-border border-y border-border">
              {data.categories.map((group) => (
                <details key={group.category} className="group">
                  <summary className="flex min-h-[var(--touch-target)] cursor-pointer items-center justify-between gap-3 py-3 font-medium text-ink marker:text-primary"><span>{t(`categories.${group.category}`)}</span><span className="text-sm font-normal text-ink-muted">{group.items.length}</span></summary>
                  <ul className="pb-3">{group.items.map((item) => {
                    const selected = favorites.includes(item.biomarker.id);
                    return <li key={item.biomarker.id} className="flex items-center gap-3 border-t border-border py-2 pl-3"><button type="button" aria-pressed={selected} aria-label={selected ? t("dashboard.removeFavorite", { name: item.biomarker.name }) : t("dashboard.addFavorite", { name: item.biomarker.name })} onClick={() => toggleFavorite(item.biomarker.id)} className="inline-flex size-[var(--touch-target)] shrink-0 items-center justify-center rounded-[var(--radius-md)] text-ink-muted hover:bg-band hover:text-primary"><Star size={19} fill={selected ? "currentColor" : "none"} aria-hidden="true" /></button><Link to={`/biomarkers/${item.biomarker.id}`} className="min-w-0 flex-1 font-medium text-ink hover:text-primary">{item.biomarker.name}</Link><LatestValue item={item} /></li>;
                  })}</ul>
                </details>
              ))}
            </div>
          </section>
        ) : null}
      </div>
    </section>
  );
}
