import { FileText, Trash2, Upload } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import type { ChangeEvent, FormEvent } from "react";
import { useTranslation } from "react-i18next";

import {
  CollectionFields,
  emptyCollection,
  toCollectionContext,
} from "../components/domain/CollectionFields";
import { Button } from "../components/ui/Button";
import { FormSurface } from "../components/ui/FormSurface";
import { Input } from "../components/ui/Input";
import { Select } from "../components/ui/Select";
import { Skeleton } from "../components/ui/Skeleton";
import { useToast } from "../components/ui/Toast";
import { catalogue, extractions } from "../lib/api";
import { ApiError } from "../lib/api/client";
import type { Biomarker, ExtractionJob } from "../lib/api/types";
import { todayInputValue } from "../lib/format";
import { useAsync } from "../lib/useAsync";

const POLL_INTERVAL = 2000;

type Row = {
  key: number;
  biomarkerId: string;
  /** What the document called it, kept beside the match so it can be checked. */
  sourceName: string;
  value: string;
  unit: string;
  refMin: string;
  refMax: string;
  method: string;
  warnings: string[];
};

type ReportImportProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCreated: () => void;
};

function toRows(job: ExtractionJob): Row[] {
  return (job.preview?.results ?? []).map((result, index) => ({
    key: index,
    biomarkerId: result.biomarker_id === null ? "" : String(result.biomarker_id),
    sourceName: result.source_name,
    value: result.value ?? "",
    unit: result.unit ?? "",
    refMin: result.ref_min ?? "",
    refMax: result.ref_max ?? "",
    method: result.method ?? "",
    warnings: result.warnings ?? [],
  }));
}

/**
 * Upload a lab PDF or photograph, watch it being read, then correct what the model got wrong
 * before any of it is stored.
 *
 * The preview is the point of the screen, not a formality: every field is
 * editable, an unmatched line arrives needing a choice rather than quietly
 * missing, and nothing is written until Save.
 */
export function ReportImport({ open, onOpenChange, onCreated }: ReportImportProps) {
  const { t } = useTranslation();
  const notify = useToast();
  const { data: biomarkers } = useAsync(() => catalogue.biomarkers());
  const [customBiomarkers, setCustomBiomarkers] = useState<Biomarker[]>([]);
  const [job, setJob] = useState<ExtractionJob | null>(null);
  const [uploading, setUploading] = useState(false);
  const [duplicateFile, setDuplicateFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [collection, setCollection] = useState(() => emptyCollection(todayInputValue()));
  const [labName, setLabName] = useState("");
  const [rows, setRows] = useState<Row[]>([]);
  const fileInput = useRef<HTMLInputElement>(null);

  const waiting = job !== null && (job.status === "pending" || job.status === "processing");

  // Poll while the model is reading. The interval is cleared on unmount and
  // whenever the status settles, so a closed sheet stops asking.
  useEffect(() => {
    if (!waiting || job === null) return;
    const id = window.setInterval(() => {
      void extractions
        .read(job.id)
        .then(setJob)
        .catch(() => setError(t("errors.generic")));
    }, POLL_INTERVAL);
    return () => window.clearInterval(id);
  }, [waiting, job, t]);

  // The preview lands once; from then on the form belongs to the reader and
  // must not be overwritten by another poll.
  useEffect(() => {
    if (job?.status !== "preview" || job.preview === null) return;
    setRows(toRows(job));
    const preview = job.preview;
    if (preview.lab_name) setLabName(preview.lab_name);
    setCollection({
      collectedOn: preview.collected_on ?? todayInputValue(),
      // The hour only survives if the model read one off the same day it dated.
      collectedTime:
        preview.collected_at && preview.collected_at.startsWith(preview.collected_on ?? "")
          ? preview.collected_at.slice(11, 16)
          : "",
      fastingState: preview.fasting_state,
      fastingHours: "",
    });
  }, [job?.id, job?.status]); // eslint-disable-line react-hooks/exhaustive-deps

  const options = [...(biomarkers ?? []), ...customBiomarkers].map((biomarker: Biomarker) => ({
    value: String(biomarker.id),
    label: `${biomarker.name} (${biomarker.unit_default})`,
  }));

  function reset() {
    setJob(null);
    setRows([]);
    setError(null);
    setDuplicateFile(null);
    setLabName("");
    setCollection(emptyCollection(todayInputValue()));
    if (fileInput.current) fileInput.current.value = "";
  }

  function close() {
    reset();
    onOpenChange(false);
  }

  async function uploadFile(file: File, replace = false) {
    setError(null);
    setUploading(true);
    try {
      setJob(await extractions.create(file, replace));
      setDuplicateFile(null);
    } catch (cause) {
      if (cause instanceof ApiError && cause.status === 409) {
        setDuplicateFile(file);
      } else {
        setError(cause instanceof ApiError ? cause.message : t("errors.generic"));
      }
    } finally {
      setUploading(false);
    }
  }

  async function pick(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (file) await uploadFile(file);
  }

  function update(key: number, patch: Partial<Row>) {
    setRows((current) => current.map((row) => (row.key === key ? { ...row, ...patch } : row)));
  }

  async function createCustom(row: Row) {
    if (!row.unit.trim()) {
      setError(t("extraction.unitNeeded"));
      return;
    }
    setBusy(true);
    try {
      const created = await catalogue.createBiomarker({
        name: row.sourceName,
        unit: row.unit.trim(),
        source_name: row.sourceName,
      });
      setCustomBiomarkers((current) => [...current, created]);
      update(row.key, { biomarkerId: String(created.id), warnings: [] });
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : t("errors.generic"));
    } finally {
      setBusy(false);
    }
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (job === null) return;
    setError(null);
    const filled = rows.filter((row) => row.biomarkerId && row.value.trim() !== "");
    if (filled.length === 0) {
      setError(t("extraction.pickAtLeastOne"));
      return;
    }

    setBusy(true);
    try {
      await extractions.confirm(job.id, {
        ...toCollectionContext(collection),
        lab_name: labName,
        results: filled.map((row) => ({
          biomarker_id: Number(row.biomarkerId),
          source_name: row.sourceName,
          value: Number(row.value.replace(",", ".")),
          unit: row.unit.trim() || null,
          ref_min: row.refMin ? Number(row.refMin.replace(",", ".")) : null,
          ref_max: row.refMax ? Number(row.refMax.replace(",", ".")) : null,
          method: row.method.trim() || null,
        })),
      });
      notify(t("reports.created"));
      onCreated();
      close();
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : t("errors.generic"));
    } finally {
      setBusy(false);
    }
  }

  const unmatched = rows.filter((row) => !row.biomarkerId).length;

  return (
    <FormSurface
      open={open}
      onOpenChange={(next) => (next ? onOpenChange(true) : close())}
      title={t("extraction.title")}
      description={t("extraction.description")}
    >
      {job === null ? (
        <div className="flex flex-col gap-4">
          <label className="flex cursor-pointer flex-col items-center gap-3 rounded-[var(--radius-lg)] border border-dashed border-border-strong p-8 text-center hover:bg-band">
            <Upload size={28} className="text-ink-muted" aria-hidden="true" />
            <span className="font-display text-lg text-ink">{t("extraction.pickFile")}</span>
            <span className="max-w-prose text-sm text-ink-muted">{t("extraction.pickHint")}</span>
            <input
              ref={fileInput}
              type="file"
              accept="application/pdf,image/jpeg,image/png"
              capture="environment"
              className="sr-only"
              onChange={(event) => void pick(event)}
            />
          </label>
          {uploading ? <Skeleton lines={2} label={t("extraction.uploading")} /> : null}
          {duplicateFile ? (
            <div className="flex flex-col gap-3 rounded-[var(--radius-md)] bg-band p-4" role="alert">
              <div className="min-w-0">
                <p className="font-medium text-ink">{t("extraction.duplicateTitle")}</p>
                <p className="mt-1 break-words text-sm text-ink-muted">
                  {t("extraction.duplicateDescription", { filename: duplicateFile.name })}
                </p>
              </div>
              <div className="flex flex-wrap gap-2">
                <Button
                  type="button"
                  loading={uploading}
                  onClick={() => void uploadFile(duplicateFile, true)}
                >
                  {t("extraction.replace")}
                </Button>
                <Button type="button" variant="ghost" onClick={reset}>
                  {t("extraction.chooseAnother")}
                </Button>
              </div>
            </div>
          ) : null}
          {error ? (
            <p role="alert" className="text-sm text-flag-alert">
              {error}
            </p>
          ) : null}
        </div>
      ) : null}

      {waiting ? (
        <div className="flex flex-col gap-3" aria-live="polite">
          <p className="flex items-center gap-2 text-ink">
            <FileText size={20} className="text-ink-muted" aria-hidden="true" />
            {job?.filename ?? t("extraction.title")}
          </p>
          <p className="text-ink-muted">{t("extraction.reading")}</p>
          <Skeleton lines={6} label={t("common.loading")} />
        </div>
      ) : null}

      {job?.status === "failed" ? (
        <div className="flex flex-col gap-4">
          {/* The failure is the job's own message, not a generic one: "the model
              could not be reached" and "this PDF has 40 pages" need different
              things from the reader. */}
          <p role="alert" className="text-flag-alert">
            {job.error ?? t("errors.generic")}
          </p>
          <div className="flex gap-2">
            <Button onClick={reset}>{t("extraction.tryAnotherFile")}</Button>
            <Button variant="ghost" onClick={close}>
              {t("actions.cancel")}
            </Button>
          </div>
        </div>
      ) : null}

      {job?.status === "preview" ? (
        <form className="flex flex-col gap-8" onSubmit={submit} noValidate>
          <p className="max-w-prose text-sm text-ink-muted">{t("extraction.checkHint")}</p>

          <div className="flex flex-col gap-4">
            <Input
              label={t("reports.labName")}
              required
              value={labName}
              onChange={(event) => setLabName(event.target.value)}
            />
            <CollectionFields
              value={collection}
              onChange={(patch) => setCollection((current) => ({ ...current, ...patch }))}
            />
          </div>

          <fieldset>
            <legend className="w-full border-b border-border pb-2 font-display text-base font-medium text-ink">
              {t("reports.results")}
            </legend>
            {unmatched > 0 ? (
              <p className="mt-2 text-sm text-flag-warn">
                {t("extraction.unmatched", { count: unmatched })}
              </p>
            ) : null}

            <div className="mt-4 flex flex-col gap-4">
              {rows.map((row) => (
                <div
                  key={row.key}
                  className="flex flex-col gap-3 rounded-[var(--radius-md)] border border-border p-3"
                >
                  {/* The document's own wording, so a wrong match is visible
                      without opening the PDF beside it. */}
                  <p className="data text-sm text-ink-muted">{row.sourceName}</p>
                  {row.warnings.length > 0 ? <ul className="rounded-[var(--radius-md)] bg-band px-3 py-2 text-sm text-flag-warn">{row.warnings.map((warning) => <li key={warning}>{t(`extraction.warnings.${warning}`)}</li>)}</ul> : null}
                  <Select
                    label={t("reports.biomarker")}
                    placeholder={t("reports.pickBiomarker")}
                    options={options}
                    value={row.biomarkerId}
                    onChange={(event) => update(row.key, { biomarkerId: event.target.value })}
                  />
                  {!row.biomarkerId ? <Button type="button" variant="secondary" loading={busy} onClick={() => void createCustom(row)}>{t("extraction.createCustom")}</Button> : null}
                  <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
                    <Input
                      label={t("reports.unit")}
                      value={row.unit}
                      onChange={(event) => update(row.key, { unit: event.target.value })}
                    />
                    <Input
                      label={t("reports.value")}
                      inputMode="decimal"
                      value={row.value}
                      onChange={(event) => update(row.key, { value: event.target.value })}
                    />
                    <Input
                      label={t("reports.refMin")}
                      inputMode="decimal"
                      value={row.refMin}
                      onChange={(event) => update(row.key, { refMin: event.target.value })}
                    />
                    <Input
                      label={t("reports.refMax")}
                      inputMode="decimal"
                      value={row.refMax}
                      onChange={(event) => update(row.key, { refMax: event.target.value })}
                    />
                  </div>
                  <Input
                    label={`${t("reports.method")} (${t("common.optional")})`}
                    value={row.method}
                    onChange={(event) => update(row.key, { method: event.target.value })}
                  />
                  <div>
                    <Button
                      variant="ghost"
                      icon={<Trash2 size={20} aria-hidden="true" />}
                      onClick={() =>
                        setRows((current) => current.filter((item) => item.key !== row.key))
                      }
                    >
                      {t("actions.removeResult")}
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </fieldset>

          {error ? (
            <p role="alert" className="text-sm text-flag-alert">
              {error}
            </p>
          ) : null}

          <div className="flex gap-2 border-t border-border pt-4">
            <Button type="submit" loading={busy}>
              {t("extraction.confirm")}
            </Button>
            <Button variant="ghost" onClick={close}>
              {t("actions.cancel")}
            </Button>
          </div>
        </form>
      ) : null}
    </FormSurface>
  );
}
