import { useTranslation } from "react-i18next";
import { useNavigate, useParams } from "react-router-dom";

import { ResultRow } from "../components/domain/ResultRow";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { ErrorState } from "../components/ui/ErrorState";
import { Skeleton } from "../components/ui/Skeleton";
import { useToast } from "../components/ui/Toast";
import { reports } from "../lib/api";
import { formatDate } from "../lib/format";
import { useAsync } from "../lib/useAsync";

export function ReportDetail() {
  const { id = "" } = useParams();
  const { t, i18n } = useTranslation();
  const locale = i18n.resolvedLanguage ?? "pt-PT";
  const navigate = useNavigate();
  const notify = useToast();
  const { data, loading, error, reload } = useAsync(() => reports.read(id), [id]);

  if (loading) return <Skeleton lines={6} label={t("common.loading")} />;
  if (error || !data) return <ErrorState onRetry={reload} />;

  async function remove() {
    await reports.remove(id);
    notify(t("reports.deleted"));
    navigate("/reports");
  }

  return (
    <section className="flex flex-col gap-6">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="font-display text-2xl text-ink">
            {t("reports.detailTitle", { date: formatDate(data.collected_on, locale) })}
          </h1>
          <p className="text-ink-muted">
            {data.lab_name}
            {data.fasting === null ? "" : ` · ${t("reports.fasting")}: ${data.fasting ? t("common.yes") : t("common.no")}`}
          </p>
        </div>
        <Button variant="danger" onClick={remove}>
          {t("actions.delete")}
        </Button>
      </header>

      {data.notes ? <p className="text-ink-muted">{data.notes}</p> : null}

      <Card title={t("reports.results")}>
        {data.results.map((result) => (
          <ResultRow key={result.id} result={result} />
        ))}
      </Card>
    </section>
  );
}
