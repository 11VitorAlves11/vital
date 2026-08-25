import { Plus } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { BodyScanForm } from "../components/domain/BodyScanForm";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorState } from "../components/ui/ErrorState";
import { FlagChip } from "../components/ui/FlagChip";
import { LinkButton } from "../components/ui/LinkButton";
import { Skeleton } from "../components/ui/Skeleton";
import { Sparkline } from "../components/ui/Sparkline";
import { body } from "../lib/api";
import { formatDateTime, formatValue, toNumber } from "../lib/format";
import { useSession } from "../lib/session";
import { useAsync } from "../lib/useAsync";

export function Body() {
  const { t, i18n } = useTranslation();
  const locale = i18n.resolvedLanguage ?? "pt-PT";
  const { user } = useSession();
  const [recording, setRecording] = useState(false);
  const { data, loading, error, reload } = useAsync(() => body.summary());

  return (
    <section className="flex flex-col gap-6">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="font-display text-2xl text-ink">{t("body.title")}</h1>
        <Button icon={<Plus size={20} aria-hidden="true" />} onClick={() => setRecording(true)}>
          {t("body.newScan")}
        </Button>
      </header>

      <p className="text-sm text-ink-muted">{t("body.estimateWarning")}</p>

      {/* Bands are sex-specific: without it the server declines to classify, and
          saying so is more useful than showing values with no flag and no reason. */}
      {user && user.sex === null ? (
        <Card>
          <h2 className="font-display text-lg text-ink">{t("body.setSexTitle")}</h2>
          <p className="mt-1 text-ink-muted">{t("body.setSexDescription")}</p>
          <div className="mt-3">
            <LinkButton to="/profile" variant="secondary">
              {t("profile.title")}
            </LinkButton>
          </div>
        </Card>
      ) : null}

      {loading ? <Skeleton lines={5} label={t("common.loading")} /> : null}
      {error ? <ErrorState onRetry={reload} /> : null}

      {data && data.length === 0 ? (
        <EmptyState
          title={t("body.emptyTitle")}
          description={t("body.emptyDescription")}
          action={<Button onClick={() => setRecording(true)}>{t("body.newScan")}</Button>}
        />
      ) : null}

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
        {data?.map((entry) => (
          <Card key={entry.metric.id} className="flex flex-col gap-3">
            <div className="flex items-start justify-between gap-3">
              <Link
                to={`/body/${entry.metric.id}`}
                className="font-display text-lg text-ink hover:text-primary"
              >
                {entry.metric.name}
              </Link>
              {entry.latest.label ? (
                <FlagChip flag={entry.latest.flag} label={entry.latest.label} />
              ) : (
                <span className="text-sm text-ink-muted">{t("body.noClinicalReference")}</span>
              )}
            </div>

            <p className="flex items-baseline gap-2">
              <span className="data text-2xl text-ink">
                {formatValue(entry.latest.value, locale)}
              </span>
              <span className="text-sm text-ink-muted">{entry.metric.unit}</span>
            </p>

            <Sparkline
              values={entry.sparkline.map((point) => toNumber(point.value))}
              summary={t("dashboard.sparklineSummary", {
                count: entry.sparkline.length,
                name: entry.metric.name,
                first: formatValue(entry.sparkline[0]?.value, locale),
                last: formatValue(entry.sparkline[entry.sparkline.length - 1]?.value, locale),
                unit: entry.metric.unit,
              })}
            />

            <p className="text-sm text-ink-muted">
              {t("body.lastMeasured", { date: formatDateTime(entry.measured_at, locale) })}
              {entry.metric.source ? ` · ${entry.metric.source}` : ""}
            </p>
          </Card>
        ))}
      </div>

      <BodyScanForm open={recording} onOpenChange={setRecording} onCreated={reload} />
    </section>
  );
}
