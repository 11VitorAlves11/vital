import { FlaskConical, TriangleAlert } from "lucide-react";
import { useTranslation } from "react-i18next";

import { BiomarkerCard } from "../components/domain/BiomarkerCard";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorState } from "../components/ui/ErrorState";
import { LinkButton } from "../components/ui/LinkButton";
import { Skeleton } from "../components/ui/Skeleton";
import { dashboard } from "../lib/api";
import type { Dashboard as DashboardData, DashboardItem } from "../lib/api/types";
import { formatDate } from "../lib/format";
import { useAsync } from "../lib/useAsync";

/** Everything currently outside its interval, worst-first within a panel.
 *
 * Derived rather than fetched: the rule is "the flag is not normal", the data
 * is already on the page, and a second endpoint would be a second place for
 * "needs attention" to be defined. */
function outOfRange(data: DashboardData): DashboardItem[] {
  return data.categories
    .flatMap((group) => group.items)
    .filter((item) => item.flag === "low" || item.flag === "high");
}

export function Dashboard() {
  const { t, i18n } = useTranslation();
  const locale = i18n.resolvedLanguage ?? "pt-PT";
  const { data, loading, error, reload } = useAsync(() => dashboard.read());
  const flagged = data ? outOfRange(data) : [];

  return (
    <section>
      <header className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-1">
        <h1 className="font-display text-2xl leading-tight font-medium text-ink">
          {t("dashboard.title")}
        </h1>
        {data ? (
          <p className="text-sm text-ink">
            {data.last_report_on ? (
              <>
                {t("dashboard.lastReport")}{" "}
                <span className="data">{formatDate(data.last_report_on, locale)}</span>
                <span className="text-ink-muted">
                  {" · "}
                  {t("dashboard.reportCount", { count: data.report_count })}
                </span>
              </>
            ) : (
              <span className="text-ink-muted">{t("dashboard.never")}</span>
            )}
          </p>
        ) : null}
      </header>

      <div className="mt-8">
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

        {/* What is out of range, before the panels — it is the reason most
            sessions are opened, and hunting for it across nine panels is the
            work the dashboard exists to remove. The cards are the same ones,
            repeated here rather than moved, so a panel never has a hole in it. */}
        {flagged.length > 0 ? (
          <section className="mb-12">
            <h2 className="mb-4 flex items-center gap-2 border-b border-border pb-2 font-display text-lg font-medium text-ink">
              <TriangleAlert size={20} aria-hidden="true" className="text-flag-alert" />
              {t("dashboard.outOfRange", { count: flagged.length })}
            </h2>
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
              {flagged.map((item) => (
                <BiomarkerCard key={`flagged-${item.biomarker.id}`} item={item} />
              ))}
            </div>
          </section>
        ) : null}

        {/* Each panel is separated far more than the cards inside it, so the
            grouping reads before any single card does. */}
        {data?.categories.map((group) => (
          <section key={group.category} className="mt-12 first:mt-0">
            <h2 className="mb-4 border-b border-border pb-2 font-display text-lg font-medium text-ink">
              {t(`categories.${group.category}`)}
            </h2>
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
              {group.items.map((item) => (
                <BiomarkerCard key={item.biomarker.id} item={item} />
              ))}
            </div>
          </section>
        ))}
      </div>
    </section>
  );
}
