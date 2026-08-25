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
    <section>
      <header className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="font-display text-2xl leading-tight font-medium text-ink">
          {t("body.title")}
        </h1>
        <Button icon={<Plus size={20} aria-hidden="true" />} onClick={() => setRecording(true)}>
          {t("body.newScan")}
        </Button>
      </header>
      <p className="mt-2 max-w-prose text-sm text-ink-muted">{t("body.estimateWarning")}</p>

      <div className="mt-8 flex flex-col gap-6">
        {/* Bands are sex-specific: without it the server declines to classify, and
            saying so is more useful than values with no flag and no reason. */}
        {user && user.sex === null ? (
          <Card>
            <h2 className="font-display text-lg font-medium text-ink">{t("body.setSexTitle")}</h2>
            <p className="mt-1 max-w-prose text-ink-muted">{t("body.setSexDescription")}</p>
            <div className="mt-4">
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

        {data && data.length > 0 ? (
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
            {data.map((entry) => (
              <Card key={entry.metric.id} className="flex flex-col gap-3">
                <div className="flex items-start justify-between gap-3">
                  <Link
                    to={`/body/${entry.metric.id}`}
                    className="text-base font-medium text-ink underline-offset-4 hover:text-primary hover:underline"
                  >
                    {entry.metric.name}
                  </Link>
                  {entry.latest.label ? (
                    <FlagChip flag={entry.latest.flag} label={entry.latest.label} />
                  ) : null}
                </div>

                <p className="flex items-baseline gap-1.5">
                  <span className="metric text-3xl leading-none font-medium text-ink">
                    {formatValue(entry.latest.value, locale)}
                  </span>
                  <span className="text-sm text-ink">{entry.metric.unit}</span>
                </p>

                <Sparkline
                  values={entry.sparkline.map((point) => toNumber(point.value))}
                  summary={t("dashboard.sparklineSummary", {
                    count: entry.sparkline.length,
                    name: entry.metric.name,
                    first: formatValue(entry.sparkline[0]?.value, locale),
                    last: formatValue(
                      entry.sparkline[entry.sparkline.length - 1]?.value,
                      locale,
                    ),
                    unit: entry.metric.unit,
                  })}
                />

                <div className="mt-auto flex flex-wrap items-baseline justify-between gap-x-3 border-t border-border pt-3 text-sm">
                  <span className={entry.metric.source ? "text-ink" : "text-ink-muted"}>
                    {entry.metric.source ?? t("body.noClinicalReference")}
                  </span>
                  <span className="text-ink-muted">
                    {formatDateTime(entry.measured_at, locale)}
                  </span>
                </div>
              </Card>
            ))}
          </div>
        ) : null}
      </div>

      <BodyScanForm open={recording} onOpenChange={setRecording} onCreated={reload} />
    </section>
  );
}
