import { FileText, GitCompareArrows } from "lucide-react";
import { useTranslation } from "react-i18next";
import { useNavigate, useParams } from "react-router-dom";

import { NoteEditor } from "../components/domain/NoteEditor";
import { ResultRow } from "../components/domain/ResultRow";
import { Button, buttonClasses } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { ErrorState } from "../components/ui/ErrorState";
import { LinkButton } from "../components/ui/LinkButton";
import { Skeleton } from "../components/ui/Skeleton";
import { useToast } from "../components/ui/Toast";
import { reports } from "../lib/api";
import { formatDate, formatTime } from "../lib/format";
import { useAsync } from "../lib/useAsync";

export function ReportDetail() {
  const { id = "" } = useParams();
  const { t, i18n } = useTranslation();
  const locale = i18n.resolvedLanguage ?? "pt-PT";
  const navigate = useNavigate();
  const notify = useToast();
  const { data, loading, error, reload } = useAsync(() => reports.read(id), [id]);
  // Only to know whether there is anything to compare this draw against; the
  // comparison page picks the collection next to it in time.
  const { data: history } = useAsync(() => reports.list());

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
          <h1 className="font-display text-2xl leading-tight font-medium text-ink">
            {t("reports.detailTitle", { date: formatDate(data.collected_on, locale) })}
          </h1>
          {/* The collection context, in one line: where, at what hour, in what
              state. An unrecorded hour or fast is simply absent — the caveats
              beside the results it matters for say so where it means something. */}
          <p className="text-ink-muted">
            {[
              data.lab_name,
              data.doctor_name,
              data.collected_at ? formatTime(data.collected_at, locale) : null,
              data.fasting_state === "unknown" ? null : t(`fastingStates.${data.fasting_state}`),
              data.fasting_hours === null
                ? null
                : t("reports.fastingHoursShort", { count: data.fasting_hours }),
            ]
              .filter(Boolean)
              .join(" · ")}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {history && history.length > 1 ? (
            <LinkButton to={`/reports/compare?b=${data.id}`} variant="secondary">
              <GitCompareArrows size={20} aria-hidden="true" />
              {t("compare.open")}
            </LinkButton>
          ) : null}
          {/* A plain link, not fetch: the browser renders the PDF itself, and
              the session cookie rides along the way it does everywhere else. */}
          {data.has_file ? (
            <a
              href={`/api/reports/${data.id}/file`}
              target="_blank"
              rel="noreferrer"
              className={buttonClasses("secondary")}
            >
              <FileText size={20} aria-hidden="true" />
              {t("reports.openFile")}
            </a>
          ) : null}
          <Button variant="danger" onClick={remove}>
            {t("actions.delete")}
          </Button>
        </div>
      </header>

      {/* The interpretive note on the collection as a whole, above the values it
          is about — as against the note on a single result, which sits with it. */}
      <Card title={t("reports.notes")}>
        <NoteEditor
          note={data.notes}
          noteAt={data.notes_at}
          label={t("reports.notes")}
          placeholder={t("notes.reportPlaceholder")}
          onSave={async (notes) => {
            await reports.update(id, { notes });
            reload();
          }}
        />
      </Card>

      <Card title={t("reports.results")}>
        {data.results.map((result) => {
          const resultId = result.id;
          return (
            <ResultRow
              key={resultId ?? `derived-${result.biomarker_id}`}
              result={result}
              onAnnotate={
                resultId
                  ? async (note) => {
                      await reports.annotate(id, resultId, note);
                      reload();
                    }
                  : undefined
              }
            />
          );
        })}
      </Card>
    </section>
  );
}
