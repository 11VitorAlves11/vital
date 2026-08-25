import { FlaskConical } from "lucide-react";
import { useTranslation } from "react-i18next";

import { BiomarkerCard } from "../components/domain/BiomarkerCard";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorState } from "../components/ui/ErrorState";
import { LinkButton } from "../components/ui/LinkButton";
import { Skeleton } from "../components/ui/Skeleton";
import { dashboard } from "../lib/api";
import { formatDate } from "../lib/format";
import { useAsync } from "../lib/useAsync";

export function Dashboard() {
  const { t, i18n } = useTranslation();
  const locale = i18n.resolvedLanguage ?? "pt-PT";
  const { data, loading, error, reload } = useAsync(() => dashboard.read());

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
