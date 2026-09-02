import { Plus, Sigma, Users } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { BodyScanForm } from "../components/domain/BodyScanForm";
import { SubNav } from "../components/layout/SubNav";
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
import { classifies, referenceLabel } from "../lib/reference";
import { useSession } from "../lib/session";
import { useAsync } from "../lib/useAsync";

export function Body() {
  const { t, i18n } = useTranslation();
  const locale = i18n.resolvedLanguage ?? "pt-PT";
  const { user } = useSession();
  const [recording, setRecording] = useState(false);
  const { data, loading, error, reload } = useAsync(() => body.summary());
  // The name of a derived index's source, so the card can say "from fat-free
  // mass" rather than repeating a slug at the reader.
  const metricNames = new Map((data ?? []).map((item) => [item.metric.slug, item.metric.name]));

  return (
    <section>
      <SubNav
        label={t("nav.bodySection")}
        items={[
          { to: "/body", label: t("body.title") },
          { to: "/photos", label: t("photos.title") },
        ]}
      />

      <header className="mt-6 flex flex-wrap items-center justify-between gap-3">
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

                {/* A computed index says so. It is as real as a measurement, but
                    it moves when the height on the profile does, and a reader
                    comparing it to what the scale showed deserves to know why. */}
                {entry.latest.derived_from ? (
                  <p className="flex items-center gap-1.5 text-sm text-ink-muted">
                    <Sigma size={14} aria-hidden="true" className="shrink-0" />
                    {t("profile.derived", {
                      source:
                        metricNames.get(entry.latest.derived_from) ?? entry.latest.derived_from,
                    })}
                  </p>
                ) : null}

                {/* Names without judging (D1/DT8): a percentile against people
                    the reader's own age and sex, from a reference the card
                    also names — never a second flag competing with the first. */}
                {entry.latest.age_context ? (
                  <p className="flex items-center gap-1.5 text-sm text-ink-muted">
                    <Users size={14} aria-hidden="true" className="shrink-0" />
                    {entry.latest.age_context}
                  </p>
                ) : null}

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

                {/* The standard when one classifies, and otherwise the reason
                    none does — stacked rather than side by side, because the
                    reasons are sentences and a date pushed onto a second line
                    by some cards and not others makes a ragged grid. */}
                <div className="mt-auto flex flex-col gap-0.5 border-t border-border pt-3 text-sm">
                  <span className={classifies(entry.metric) ? "text-ink" : "text-ink-muted"}>
                    {referenceLabel(entry.metric) ?? t("body.noClinicalReference")}
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
