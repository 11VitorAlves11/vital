import { Plus } from "lucide-react";
import { useState } from "react";
import type { FormEvent } from "react";
import { useTranslation } from "react-i18next";

import { SubNav } from "../components/layout/SubNav";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorState } from "../components/ui/ErrorState";
import { FormSurface } from "../components/ui/FormSurface";
import { Input } from "../components/ui/Input";
import { Select } from "../components/ui/Select";
import { Skeleton } from "../components/ui/Skeleton";
import { useToast } from "../components/ui/Toast";
import { interventions as api } from "../lib/api";
import { ApiError } from "../lib/api/client";
import type { InterventionKind } from "../lib/api/types";
import { formatDate, todayInputValue } from "../lib/format";
import { useAsync } from "../lib/useAsync";

const KINDS: InterventionKind[] = ["suplemento", "medicacao", "dieta", "treino", "outro"];

export function Interventions() {
  const { t, i18n } = useTranslation();
  const locale = i18n.resolvedLanguage ?? "pt-PT";
  const notify = useToast();
  const [kindFilter, setKindFilter] = useState<InterventionKind | "">("");
  const [creating, setCreating] = useState(false);
  const { data, loading, error, reload } = useAsync(
    () => api.list(kindFilter || undefined),
    [kindFilter],
  );

  const [kind, setKind] = useState<InterventionKind>("suplemento");
  const [name, setName] = useState("");
  const [dose, setDose] = useState("");
  const [startedOn, setStartedOn] = useState(todayInputValue());
  const [formError, setFormError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setFormError(null);
    setBusy(true);
    try {
      await api.create({ kind, name, dose: dose || null, started_on: startedOn });
      notify(t("interventions.created"));
      setName("");
      setDose("");
      setCreating(false);
      reload();
    } catch (cause) {
      setFormError(cause instanceof ApiError ? cause.message : t("errors.generic"));
    } finally {
      setBusy(false);
    }
  }

  async function end(id: string) {
    await api.update(id, { ended_on: todayInputValue() });
    notify(t("interventions.ended"));
    reload();
  }

  async function remove(id: string) {
    await api.remove(id);
    notify(t("interventions.deleted"));
    reload();
  }

  return (
    <section>
      <SubNav
        label={t("nav.timelineSection")}
        items={[
          { to: "/timeline", label: t("timeline.title") },
          { to: "/interventions", label: t("interventions.title") },
        ]}
      />

      <header className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="font-display text-2xl leading-tight font-medium text-ink">
          {t("interventions.title")}
        </h1>
        <Button icon={<Plus size={20} aria-hidden="true" />} onClick={() => setCreating(true)}>
          {t("interventions.new")}
        </Button>
      </header>

      <div className="mt-6 md:max-w-xs">
        <Select
          label={t("interventions.filterKind")}
          placeholder={t("interventions.all")}
          value={kindFilter}
          onChange={(event) => setKindFilter(event.target.value as InterventionKind | "")}
          options={KINDS.map((value) => ({ value, label: t(`kinds.${value}`) }))}
        />
      </div>

      <div className="mt-8">
        {loading ? <Skeleton lines={4} label={t("common.loading")} /> : null}
        {error ? <ErrorState onRetry={reload} /> : null}

        {data && data.length === 0 ? (
          <EmptyState
            title={t("interventions.emptyTitle")}
            description={t("interventions.emptyDescription")}
            action={<Button onClick={() => setCreating(true)}>{t("interventions.new")}</Button>}
          />
        ) : null}

        {data && data.length > 0 ? (
          <Card className="p-0">
            <ul>
              {data.map((intervention) => (
                <li
                  key={intervention.id}
                  className="flex flex-wrap items-center justify-between gap-3 border-t border-border px-4 py-3 first:border-t-0"
                >
                  <div className="min-w-0">
                    <p className="flex flex-wrap items-baseline gap-x-2">
                      <span className="font-medium text-ink">{intervention.name}</span>
                      {intervention.dose ? (
                        <span className="data text-sm text-ink">{intervention.dose}</span>
                      ) : null}
                    </p>
                    <p className="text-sm text-ink-muted">
                      {t(`kinds.${intervention.kind}`)} ·{" "}
                      <span className="data">{formatDate(intervention.started_on, locale)}</span>
                      {" – "}
                      {intervention.ended_on ? (
                        <span className="data">{formatDate(intervention.ended_on, locale)}</span>
                      ) : (
                        <span className="text-ink">{t("interventions.ongoing")}</span>
                      )}
                    </p>
                  </div>
                  <div className="flex gap-2">
                    {intervention.ended_on ? null : (
                      <Button variant="secondary" onClick={() => end(intervention.id)}>
                        {t("actions.end")}
                      </Button>
                    )}
                    <Button variant="danger" onClick={() => remove(intervention.id)}>
                      {t("actions.delete")}
                    </Button>
                  </div>
                </li>
              ))}
            </ul>
          </Card>
        ) : null}
      </div>

      <FormSurface open={creating} onOpenChange={setCreating} title={t("interventions.new")}>
        <form className="flex flex-col gap-4" onSubmit={submit} noValidate>
          <Select
            label={t("interventions.kind")}
            value={kind}
            onChange={(event) => setKind(event.target.value as InterventionKind)}
            options={KINDS.map((value) => ({ value, label: t(`kinds.${value}`) }))}
          />
          <Input
            label={t("interventions.name")}
            required
            value={name}
            onChange={(event) => setName(event.target.value)}
          />
          <Input
            label={`${t("interventions.dose")} (${t("common.optional")})`}
            value={dose}
            onChange={(event) => setDose(event.target.value)}
          />
          <Input
            label={t("interventions.startedOn")}
            type="date"
            required
            value={startedOn}
            onChange={(event) => setStartedOn(event.target.value)}
          />
          {formError ? (
            <p role="alert" className="text-sm text-flag-alert">
              {formError}
            </p>
          ) : null}
          <div className="flex gap-2">
            <Button type="submit" loading={busy}>
              {t("actions.save")}
            </Button>
            <Button variant="ghost" onClick={() => setCreating(false)}>
              {t("actions.cancel")}
            </Button>
          </div>
        </form>
      </FormSurface>
    </section>
  );
}
