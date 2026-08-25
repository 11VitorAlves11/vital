import { Plus, Trash2 } from "lucide-react";
import { useState } from "react";
import type { FormEvent } from "react";
import { useTranslation } from "react-i18next";

import { Button } from "../components/ui/Button";
import { FormSurface } from "../components/ui/FormSurface";
import { Input } from "../components/ui/Input";
import { Select } from "../components/ui/Select";
import { useToast } from "../components/ui/Toast";
import { catalogue, reports } from "../lib/api";
import { ApiError } from "../lib/api/client";
import { todayInputValue } from "../lib/format";
import { useAsync } from "../lib/useAsync";

type Row = { key: number; biomarkerId: string; value: string; refMin: string; refMax: string };

function emptyRow(key: number): Row {
  return { key, biomarkerId: "", value: "", refMin: "", refMax: "" };
}

type ReportCreateProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCreated: () => void;
};

/** Manual entry of a whole collection: the report and every result in one go. */
export function ReportCreate({ open, onOpenChange, onCreated }: ReportCreateProps) {
  const { t } = useTranslation();
  const notify = useToast();
  const { data: biomarkers } = useAsync(() => catalogue.biomarkers());
  const [collectedOn, setCollectedOn] = useState(todayInputValue());
  const [labName, setLabName] = useState("");
  const [fasting, setFasting] = useState(false);
  const [notes, setNotes] = useState("");
  const [rows, setRows] = useState<Row[]>([emptyRow(0)]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const options = (biomarkers ?? []).map((biomarker) => ({
    value: String(biomarker.id),
    label: `${biomarker.name} (${biomarker.unit_default})`,
  }));

  function update(key: number, patch: Partial<Row>) {
    setRows((current) => current.map((row) => (row.key === key ? { ...row, ...patch } : row)));
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    const filled = rows.filter((row) => row.biomarkerId && row.value.trim() !== "");
    if (filled.length === 0) {
      setError(t("errors.required"));
      return;
    }

    setBusy(true);
    try {
      await reports.create({
        collected_on: collectedOn,
        lab_name: labName,
        fasting,
        notes: notes || null,
        results: filled.map((row) => ({
          biomarker_id: Number(row.biomarkerId),
          value: Number(row.value.replace(",", ".")),
          ref_min: row.refMin ? Number(row.refMin.replace(",", ".")) : null,
          ref_max: row.refMax ? Number(row.refMax.replace(",", ".")) : null,
        })),
      });
      notify(t("reports.created"));
      setRows([emptyRow(0)]);
      setLabName("");
      setNotes("");
      onCreated();
      onOpenChange(false);
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : t("errors.generic"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <FormSurface open={open} onOpenChange={onOpenChange} title={t("reports.new")}>
      <form className="flex flex-col gap-8" onSubmit={submit} noValidate>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <Input
            label={t("reports.collectedOn")}
            type="date"
            required
            value={collectedOn}
            onChange={(event) => setCollectedOn(event.target.value)}
          />
          <Input
            label={t("reports.labName")}
            required
            value={labName}
            onChange={(event) => setLabName(event.target.value)}
          />
          <label className="flex min-h-[var(--touch-target)] items-center gap-2 text-ink">
            <input
              type="checkbox"
              checked={fasting}
              onChange={(event) => setFasting(event.target.checked)}
              className="size-5"
            />
            {t("reports.fasting")}
          </label>
        </div>

        <fieldset>
          <legend className="w-full border-b border-border pb-2 font-display text-base font-medium text-ink">
            {t("reports.results")}
          </legend>
          {/* Said once, above the rows, instead of repeated under every one. */}
          <p className="mt-2 text-sm text-ink-muted">{t("reports.refHint")}</p>

          <div className="mt-4 flex flex-col gap-4">
            {rows.map((row) => (
              <div
                key={row.key}
                className="flex flex-col gap-3 rounded-[var(--radius-md)] border border-border p-3"
              >
                <Select
                  label={t("reports.biomarker")}
                  placeholder={t("reports.pickBiomarker")}
                  options={options}
                  value={row.biomarkerId}
                  onChange={(event) => update(row.key, { biomarkerId: event.target.value })}
                />
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
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
                {rows.length > 1 ? (
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
                ) : null}
              </div>
            ))}
          </div>

          <div className="mt-4">
            <Button
              variant="secondary"
              icon={<Plus size={20} aria-hidden="true" />}
              onClick={() => setRows((current) => [...current, emptyRow(Date.now())])}
            >
              {t("actions.addResult")}
            </Button>
          </div>
        </fieldset>

        <Input
          label={`${t("reports.notes")} (${t("common.optional")})`}
          value={notes}
          onChange={(event) => setNotes(event.target.value)}
        />

        {error ? (
          <p role="alert" className="text-sm text-flag-alert">
            {error}
          </p>
        ) : null}

        <div className="flex gap-2 border-t border-border pt-4">
          <Button type="submit" loading={busy}>
            {t("actions.save")}
          </Button>
          <Button variant="ghost" onClick={() => onOpenChange(false)}>
            {t("actions.cancel")}
          </Button>
        </div>
      </form>
    </FormSurface>
  );
}
