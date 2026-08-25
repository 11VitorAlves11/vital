import { FlaskConical } from "lucide-react";
import { useTranslation } from "react-i18next";

import { BiomarkerCard } from "../components/domain/BiomarkerCard";
import { LinkButton } from "../components/ui/LinkButton";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorState } from "../components/ui/ErrorState";
import { Skeleton } from "../components/ui/Skeleton";
import { dashboard } from "../lib/api";
import { formatDate } from "../lib/format";
import { useAsync } from "../lib/useAsync";

export function Dashboard() {
  const { t, i18n } = useTranslation();
  const locale = i18n.resolvedLanguage ?? "pt-PT";
  const { data, loading, error, reload } = useAsync(() => dashboard.read());

  return (
    <section className="flex flex-col gap-6">
      <header className="flex flex-wrap items-baseline justify-between gap-2">
        <h1 className="font-display text-2xl text-ink">{t("dashboard.title")}</h1>
        {data ? (
          <p className="text-sm text-ink-muted">
            {t("dashboard.lastReport")}:{" "}
            {data.last_report_on ? formatDate(data.last_report_on, locale) : t("dashboard.never")}
          </p>
        ) : null}
      </header>

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

      {data?.categories.map((group) => (
        <section key={group.category} className="flex flex-col gap-3">
          <h2 className="font-display text-lg text-ink-muted">{t(`categories.${group.category}`)}</h2>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
            {group.items.map((item) => (
              <BiomarkerCard key={item.biomarker.id} item={item} />
            ))}
          </div>
        </section>
      ))}
    </section>
  );
}
