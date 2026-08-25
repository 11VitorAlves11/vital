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
    <section className="flex flex-col gap-6">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="font-display text-2xl text-ink">{t("reports.title")}</h1>
        <Button icon={<Plus size={20} aria-hidden="true" />} onClick={() => setCreating(true)}>
          {t("reports.new")}
        </Button>
      </header>

      <div className="grid grid-cols-2 gap-3 md:max-w-md">
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

      {loading ? <Skeleton lines={4} label={t("common.loading")} /> : null}
      {error ? <ErrorState onRetry={reload} /> : null}

      {data && data.length === 0 ? (
        <EmptyState
          title={t("reports.emptyTitle")}
          description={t("reports.emptyDescription")}
          action={<Button onClick={() => setCreating(true)}>{t("reports.new")}</Button>}
        />
      ) : null}

      <ul className="flex flex-col gap-3">
        {data?.map((report) => (
          <li key={report.id}>
            <Card>
              <Link
                to={`/reports/${report.id}`}
                className="flex flex-wrap items-baseline justify-between gap-2"
              >
                <span className="font-display text-lg text-ink">
                  {formatDate(report.collected_on, locale)}
                </span>
                <span className="text-ink-muted">{report.lab_name}</span>
                <span className="text-sm text-ink-muted">
                  {t("reports.resultCount", { count: report.result_count })}
                </span>
              </Link>
            </Card>
          </li>
        ))}
      </ul>

      <ReportCreate open={creating} onOpenChange={setCreating} onCreated={reload} />
    </section>
  );
}
