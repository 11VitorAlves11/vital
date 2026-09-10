import { ArrowLeft, GitMerge, Trash2 } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorState } from "../components/ui/ErrorState";
import { LinkButton } from "../components/ui/LinkButton";
import { Skeleton } from "../components/ui/Skeleton";
import { useToast } from "../components/ui/Toast";
import { matchRules } from "../lib/api";
import { useAsync } from "../lib/useAsync";

export function MatchRules() {
  const { t } = useTranslation();
  const notify = useToast();
  const [removing, setRemoving] = useState<string | null>(null);
  const { data, loading, error, reload } = useAsync(() => matchRules.list());

  async function remove(id: string) {
    setRemoving(id);
    try {
      await matchRules.remove(id);
      notify(t("matchRules.deleted"));
      reload();
    } finally {
      setRemoving(null);
    }
  }

  return (
    <section>
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="font-display text-2xl leading-tight font-medium text-ink">
            {t("matchRules.title")}
          </h1>
          <p className="mt-2 max-w-2xl text-ink-muted">{t("matchRules.description")}</p>
        </div>
        <LinkButton to="/reports" variant="secondary">
          <ArrowLeft size={20} aria-hidden="true" />
          {t("matchRules.back")}
        </LinkButton>
      </header>

      <div className="mt-8">
        {loading ? <Skeleton lines={5} label={t("common.loading")} /> : null}
        {error ? <ErrorState onRetry={reload} /> : null}
        {data && data.length === 0 ? (
          <EmptyState
            icon={<GitMerge size={28} className="text-ink-muted" aria-hidden="true" />}
            title={t("matchRules.emptyTitle")}
            description={t("matchRules.emptyDescription")}
          />
        ) : null}
        {data && data.length > 0 ? (
          <Card className="overflow-hidden p-0">
            <div className="hidden grid-cols-[1fr_1.2fr_2rem_1.2fr_auto] gap-4 border-b border-border bg-band px-4 py-3 text-sm font-medium text-ink-muted md:grid">
              <span>{t("matchRules.lab")}</span>
              <span>{t("matchRules.source")}</span>
              <span aria-hidden="true" />
              <span>{t("matchRules.destination")}</span>
              <span className="sr-only">{t("actions.delete")}</span>
            </div>
            <ul>
              {data.map((rule) => (
                <li
                  key={rule.id}
                  className="grid gap-2 border-t border-border px-4 py-4 first:border-t-0 md:grid-cols-[1fr_1.2fr_2rem_1.2fr_auto] md:items-center md:gap-4"
                >
                  <span className="text-sm font-medium text-ink">{rule.lab_name}</span>
                  <span className="min-w-0">
                    <span className="block truncate text-ink">{rule.source_name}</span>
                    <span className="data text-sm text-ink-muted">
                      {rule.source_unit ?? t("matchRules.noUnit")}
                    </span>
                  </span>
                  <span className="hidden text-center text-ink-muted md:block" aria-hidden="true">
                    →
                  </span>
                  <span className="min-w-0">
                    <span className="block truncate font-medium text-ink">{rule.biomarker_name}</span>
                    <span className="data text-sm text-ink-muted">{rule.biomarker_unit}</span>
                  </span>
                  <Button
                    variant="ghost"
                    className="justify-self-start px-3 md:justify-self-end"
                    icon={<Trash2 size={18} aria-hidden="true" />}
                    loading={removing === rule.id}
                    onClick={() => void remove(rule.id)}
                    aria-label={t("matchRules.deleteLabel", { source: rule.source_name })}
                  >
                    <span className="md:sr-only">{t("actions.delete")}</span>
                  </Button>
                </li>
              ))}
            </ul>
          </Card>
        ) : null}
      </div>
    </section>
  );
}
