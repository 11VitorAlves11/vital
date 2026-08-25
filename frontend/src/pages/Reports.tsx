import { Plus } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorState } from "../components/ui/ErrorState";
import { Input } from "../components/ui/Input";
import { Skeleton } from "../components/ui/Skeleton";
import { reports } from "../lib/api";
import { formatDate } from "../lib/format";
import { useAsync } from "../lib/useAsync";
import { ReportCreate } from "./ReportCreate";

export function Reports() {
  const { t, i18n } = useTranslation();
  const locale = i18n.resolvedLanguage ?? "pt-PT";
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [creating, setCreating] = useState(false);
  const { data, loading, error, reload } = useAsync(
    () => reports.list({ from: from || undefined, to: to || undefined }),
    [from, to],
  );

  return (
    <section>
      <header className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="font-display text-2xl leading-tight font-medium text-ink">
          {t("reports.title")}
        </h1>
        <Button icon={<Plus size={20} aria-hidden="true" />} onClick={() => setCreating(true)}>
          {t("reports.new")}
        </Button>
      </header>

      <div className="mt-6 grid grid-cols-2 gap-3 md:max-w-md">
        <Input
          label={t("reports.filterFrom")}
          type="date"
          value={from}
          onChange={(event) => setFrom(event.target.value)}
        />
        <Input
          label={t("reports.filterTo")}
          type="date"
          value={to}
          onChange={(event) => setTo(event.target.value)}
        />
      </div>

      <div className="mt-8">
        {loading ? <Skeleton lines={4} label={t("common.loading")} /> : null}
        {error ? <ErrorState onRetry={reload} /> : null}

        {data && data.length === 0 ? (
          <EmptyState
            title={t("reports.emptyTitle")}
            description={t("reports.emptyDescription")}
            action={<Button onClick={() => setCreating(true)}>{t("reports.new")}</Button>}
          />
        ) : null}

        {/* One surface holding a divided list, rather than a card per row: at this
            density the repeated card chrome was most of what the page showed. */}
        {data && data.length > 0 ? (
          <Card className="p-0">
            <ul>
              {data.map((report) => (
                <li key={report.id} className="border-t border-border first:border-t-0">
                  <Link
                    to={`/reports/${report.id}`}
                    className="flex min-h-[var(--touch-target)] flex-wrap items-baseline gap-x-4 gap-y-1 px-4 py-3 hover:bg-band"
                  >
                    <span className="data font-medium text-ink">
                      {formatDate(report.collected_on, locale)}
                    </span>
                    <span className="flex-1 text-ink">{report.lab_name}</span>
                    <span className="text-sm text-ink-muted">
                      {t("reports.resultCount", { count: report.result_count })}
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          </Card>
        ) : null}
      </div>

      <ReportCreate open={creating} onOpenChange={setCreating} onCreated={reload} />
    </section>
  );
}
