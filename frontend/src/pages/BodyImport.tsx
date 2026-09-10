import { ScanLine, Trash2, Upload } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import type { ChangeEvent, FormEvent } from "react";
import { useTranslation } from "react-i18next";

import { Button } from "../components/ui/Button";
import { FormSurface } from "../components/ui/FormSurface";
import { Input } from "../components/ui/Input";
import { Select } from "../components/ui/Select";
import { Skeleton } from "../components/ui/Skeleton";
import { useToast } from "../components/ui/Toast";
import { bodyExtractions, catalogue } from "../lib/api";
import { ApiError } from "../lib/api/client";
import type { BodyExtractionJob } from "../lib/api/types";
import { toLocalInputValue } from "../lib/format";
import { useAsync } from "../lib/useAsync";

const POLL_INTERVAL = 2000;

type Row = {
  key: number;
  metricId: string;
  sourceName: string;
  sourceUnit: string;
  value: string;
  warnings: string[];
};

type BodyImportProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCreated: () => void;
};

function rowsFrom(job: BodyExtractionJob): Row[] {
  return (job.preview?.results ?? []).map((result, index) => ({
    key: index,
    metricId: result.metric_id === null ? "" : String(result.metric_id),
    sourceName: result.source_name,
    sourceUnit: result.source_unit ?? "",
    value: result.value ?? "",
    warnings: result.warnings,
  }));
}

export function BodyImport({ open, onOpenChange, onCreated }: BodyImportProps) {
  const { t } = useTranslation();
  const notify = useToast();
  const { data: metrics } = useAsync(() => catalogue.bodyMetrics());
  const [job, setJob] = useState<BodyExtractionJob | null>(null);
  const [rows, setRows] = useState<Row[]>([]);
  const [measuredAt, setMeasuredAt] = useState(() => toLocalInputValue(new Date()));
  const [device, setDevice] = useState("");
  const [uploading, setUploading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInput = useRef<HTMLInputElement>(null);
  const waiting = job !== null && ["pending", "processing"].includes(job.status);

  function messageFor(cause: unknown): string {
    if (!(cause instanceof ApiError)) return t("errors.generic");
    const key = {
      409: "alreadyImported",
      413: "tooLarge",
      415: "invalidFile",
      503: "notConfigured",
    }[cause.status];
    return key ? t(`bodyImport.errors.${key}`) : t("errors.generic");
  }

  useEffect(() => {
    if (!waiting || job === null) return;
    const timer = window.setInterval(() => {
      void bodyExtractions
        .read(job.id)
        .then(setJob)
        .catch(() => setError(t("errors.generic")));
    }, POLL_INTERVAL);
    return () => window.clearInterval(timer);
  }, [waiting, job, t]);

  useEffect(() => {
    if (job?.status !== "preview" || job.preview === null) return;
    setRows(rowsFrom(job));
    setDevice(job.preview.device ?? "");
    if (job.preview.measured_at) {
      const parsed = new Date(job.preview.measured_at);
      if (!Number.isNaN(parsed.getTime())) setMeasuredAt(toLocalInputValue(parsed));
    }
  }, [job?.id, job?.status]); // eslint-disable-line react-hooks/exhaustive-deps

  const options = (metrics ?? []).map((metric) => ({
    value: String(metric.id),
    label: `${metric.name} (${metric.unit})`,
  }));

  function update(key: number, patch: Partial<Row>) {
    setRows((current) => current.map((row) => (row.key === key ? { ...row, ...patch } : row)));
  }

  function reset() {
    setJob(null);
    setRows([]);
    setDevice("");
    setMeasuredAt(toLocalInputValue(new Date()));
    setError(null);
    if (fileInput.current) fileInput.current.value = "";
  }

  function close() {
    reset();
    onOpenChange(false);
  }

  async function pick(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    setError(null);
    setUploading(true);
    try {
      setJob(await bodyExtractions.create(file));
    } catch (cause) {
      setError(messageFor(cause));
    } finally {
      setUploading(false);
    }
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!job) return;
    if (!measuredAt) {
      setError(t("bodyImport.dateRequired"));
      return;
    }
    const selectedRows = rows.filter((row) => row.metricId && row.value.trim());
    const values = selectedRows.map((row) => ({
        metric_id: Number(row.metricId),
        value: Number(row.value.replace(",", ".")),
      }));
    if (values.length === 0) {
      setError(t("bodyImport.pickAtLeastOne"));
      return;
    }
    if (values.some((item) => !Number.isFinite(item.value))) {
      setError(t("bodyImport.invalidValue"));
      return;
    }
    if (new Set(values.map((item) => item.metric_id)).size !== values.length) {
      setError(t("bodyImport.duplicateSelection"));
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const date = new Date(measuredAt);
      if (Number.isNaN(date.getTime())) {
        setError(t("bodyImport.dateRequired"));
        return;
      }
      await bodyExtractions.confirm(job.id, {
        measured_at: date.toISOString(),
        device: device.trim() || null,
        values,
      });
      notify(t("bodyImport.created"));
      onCreated();
      close();
    } catch (cause) {
      setError(messageFor(cause));
    } finally {
      setBusy(false);
    }
  }

  return (
    <FormSurface
      open={open}
      onOpenChange={(next) => (next ? onOpenChange(true) : close())}
      title={t("bodyImport.title")}
      description={t("bodyImport.description")}
    >
      {job === null ? (
        <div className="flex flex-col gap-4">
          <label className="flex cursor-pointer flex-col items-center gap-3 rounded-[var(--radius-lg)] border border-dashed border-border-strong p-8 text-center hover:bg-band">
            <Upload size={28} className="text-ink-muted" aria-hidden="true" />
            <span className="font-display text-lg text-ink">{t("bodyImport.pickFile")}</span>
            <span className="max-w-prose text-sm text-ink-muted">{t("bodyImport.pickHint")}</span>
            <input
              ref={fileInput}
              type="file"
              accept="image/jpeg,image/png"
              capture="environment"
              className="sr-only"
              onChange={(event) => void pick(event)}
            />
          </label>
          {uploading ? <Skeleton lines={2} label={t("bodyImport.uploading")} /> : null}
          {error ? (
            <p role="alert" className="text-sm text-flag-alert">{error}</p>
          ) : null}
        </div>
      ) : null}

      {waiting ? (
        <div className="flex flex-col gap-3" aria-live="polite">
          <p className="flex items-center gap-2 text-ink">
            <ScanLine size={20} className="text-ink-muted" aria-hidden="true" />
            {job.filename ?? t("bodyImport.title")}
          </p>
          <p className="text-ink-muted">{t("bodyImport.reading")}</p>
          <Skeleton lines={6} label={t("common.loading")} />
        </div>
      ) : null}

      {job?.status === "failed" ? (
        <div className="flex flex-col gap-4">
          <p role="alert" className="text-flag-alert">{t("bodyImport.errors.failed")}</p>
          <div className="flex flex-wrap gap-2">
            <Button onClick={reset}>{t("bodyImport.tryAnother")}</Button>
            <Button variant="ghost" onClick={close}>{t("actions.cancel")}</Button>
          </div>
        </div>
      ) : null}

      {job?.status === "preview" ? (
        <form className="flex flex-col gap-8" onSubmit={submit} noValidate>
          <p className="max-w-prose text-sm text-ink-muted">{t("bodyImport.checkHint")}</p>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Input label={t("body.measuredAt")} type="datetime-local" required value={measuredAt} onChange={(event) => setMeasuredAt(event.target.value)} />
            <Input label={`${t("body.device")} (${t("common.optional")})`} value={device} onChange={(event) => setDevice(event.target.value)} />
          </div>

          <fieldset>
            <legend className="w-full border-b border-border pb-2 font-display font-medium text-ink">{t("body.values")}</legend>
            <div className="mt-4 flex flex-col gap-4">
              {rows.map((row) => {
                const selected = metrics?.find((metric) => String(metric.id) === row.metricId);
                return (
                  <div key={row.key} className="flex flex-col gap-3 rounded-[var(--radius-md)] border border-border p-3">
                    <p className="data text-sm text-ink-muted">{row.sourceName}{row.sourceUnit ? ` · ${row.sourceUnit}` : ""}</p>
                    {row.warnings.length > 0 ? (
                      <ul className="rounded-[var(--radius-md)] bg-band px-3 py-2 text-sm text-flag-warn">
                        {row.warnings.map((warning) => <li key={warning}>{t(`bodyImport.warnings.${warning}`)}</li>)}
                      </ul>
                    ) : null}
                    <Select label={t("bodyImport.metric")} placeholder={t("bodyImport.pickMetric")} options={options} value={row.metricId} onChange={(event) => update(row.key, { metricId: event.target.value, warnings: row.warnings.filter((warning) => warning !== "unmatched") })} />
                    <Input label={t("bodyImport.value")} inputMode="decimal" unit={selected?.unit} value={row.value} onChange={(event) => update(row.key, { value: event.target.value })} />
                    <div>
                      <Button variant="ghost" icon={<Trash2 size={18} aria-hidden="true" />} onClick={() => setRows((current) => current.filter((item) => item.key !== row.key))}>{t("bodyImport.removeValue")}</Button>
                    </div>
                  </div>
                );
              })}
            </div>
          </fieldset>

          {error ? <p role="alert" className="text-sm text-flag-alert">{error}</p> : null}
          <div className="flex flex-wrap gap-2 border-t border-border pt-4">
            <Button type="submit" loading={busy}>{t("bodyImport.confirm")}</Button>
            <Button variant="ghost" onClick={close}>{t("actions.cancel")}</Button>
          </div>
        </form>
      ) : null}
    </FormSurface>
  );
}
