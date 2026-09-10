import { Plus, Trash2 } from "lucide-react";
import { useState } from "react";
import type { FormEvent } from "react";
import { useTranslation } from "react-i18next";

import {
  CollectionFields,
  emptyCollection,
  toCollectionContext,
} from "../components/domain/CollectionFields";
import { Button } from "../components/ui/Button";
import { Combobox } from "../components/ui/Combobox";
import { FormSurface } from "../components/ui/FormSurface";
import { Input } from "../components/ui/Input";
import { useToast } from "../components/ui/Toast";
import { catalogue, providers, reports } from "../lib/api";
import { ApiError } from "../lib/api/client";
import { sameName, todayInputValue } from "../lib/format";
import { useAsync } from "../lib/useAsync";

type Row = {
  key: number;
  biomarkerId: string;
  value: string;
  refMin: string;
  refMax: string;
  method: string;
  note: string;
  /** Where the range and unit on this row came from, when they were suggested. */
  from: string | null;
};

function emptyRow(key: number): Row {
  return {
    key,
    biomarkerId: "",
    value: "",
    refMin: "",
    refMax: "",
    method: "",
    note: "",
    from: null,
  };
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
  // Suggestions, not a closed list: a first visit to a new laboratory has to be
  // as easy to record as the tenth to a familiar one.
  const { data: labs } = useAsync(() => providers.labs());
  const { data: doctors } = useAsync(() => providers.doctors());
  const [collection, setCollection] = useState(() => emptyCollection(todayInputValue()));
  const [labName, setLabName] = useState("");
  const [doctorName, setDoctorName] = useState("");
  const [notes, setNotes] = useState("");
  const [rows, setRows] = useState<Row[]>([emptyRow(0)]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  // The laboratory is typed, not picked, so the match back to an entity is the
  // same fold the server applies. No match simply means no suggestions yet.
  const lab = (labs ?? []).find((candidate) => sameName(candidate.name, labName));
  const { data: suggestions } = useAsync(() => reports.prefill(lab?.id), [lab?.id]);

  const options = (biomarkers ?? [])
    .map((biomarker) => ({
      value: String(biomarker.id),
      label: `${biomarker.name} (${biomarker.unit_default})`,
    }))
    .sort((a, b) => a.label.localeCompare(b.label, "pt-PT", { sensitivity: "base" }));

  function update(key: number, patch: Partial<Row>) {
    setRows((current) => current.map((row) => (row.key === key ? { ...row, ...patch } : row)));
  }

  /**
   * Fill a row from the last reading of the marker just chosen.
   *
   * Only into fields still empty: a suggestion may never overwrite something
   * someone typed. The value itself is never suggested — it is the one thing
   * that has to be read off the report.
   */
  function pickBiomarker(key: number, biomarkerId: string) {
    const suggestion = (suggestions ?? []).find(
      (candidate) => String(candidate.biomarker_id) === biomarkerId,
    );
    setRows((current) =>
      current.map((row) => {
        if (row.key !== key) return row;
        if (!suggestion) return { ...row, biomarkerId, from: null };
        // The unit and the assay travel between laboratories; the reference
        // range does not. From another laboratory, the range is left blank
        // rather than carried across as if it applied here.
        const range = suggestion.same_lab
          ? {
              refMin: row.refMin || (suggestion.ref_min ?? ""),
              refMax: row.refMax || (suggestion.ref_max ?? ""),
            }
          : {};
        return {
          ...row,
          biomarkerId,
          ...range,
          method: row.method || (suggestion.method ?? ""),
          from: `${suggestion.lab_name} · ${suggestion.collected_on}`,
        };
      }),
    );
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
        ...toCollectionContext(collection),
        lab_name: labName,
        doctor_name: doctorName || null,
        notes: notes || null,
        results: filled.map((row) => ({
          biomarker_id: Number(row.biomarkerId),
          value: Number(row.value.replace(",", ".")),
          ref_min: row.refMin ? Number(row.refMin.replace(",", ".")) : null,
          ref_max: row.refMax ? Number(row.refMax.replace(",", ".")) : null,
          method: row.method.trim() || null,
          note: row.note.trim() || null,
        })),
      });
      notify(t("reports.created"));
      setRows([emptyRow(0)]);
      setLabName("");
      setDoctorName("");
      setNotes("");
      setCollection(emptyCollection(todayInputValue()));
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
        <div className="flex flex-col gap-4">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Input
              label={t("reports.labName")}
              required
              list="known-labs"
              value={labName}
              onChange={(event) => setLabName(event.target.value)}
            />
            <datalist id="known-labs">
              {(labs ?? []).map((lab) => (
                <option key={lab.id} value={lab.name} />
              ))}
            </datalist>
            <Input
              label={`${t("reports.doctorName")} (${t("common.optional")})`}
              list="known-doctors"
              value={doctorName}
              onChange={(event) => setDoctorName(event.target.value)}
            />
            <datalist id="known-doctors">
              {(doctors ?? []).map((doctor) => (
                <option key={doctor.id} value={doctor.name} />
              ))}
            </datalist>
          </div>
          <CollectionFields
            value={collection}
            onChange={(patch) => setCollection((current) => ({ ...current, ...patch }))}
          />
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
                <Combobox
                  label={t("reports.biomarker")}
                  placeholder={t("reports.pickBiomarker")}
                  noResults={t("reports.noBiomarkerResults")}
                  options={options}
                  value={row.biomarkerId}
                  onValueChange={(value) => pickBiomarker(row.key, value)}
                />
                {row.from ? (
                  <p className="text-sm text-ink-muted">
                    {t("reports.prefilledFrom", { source: row.from })}
                  </p>
                ) : null}
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
                <Input
                  label={`${t("reports.method")} (${t("common.optional")})`}
                  value={row.method}
                  hint={t("reports.methodHint")}
                  onChange={(event) => update(row.key, { method: event.target.value })}
                />
                <Input
                  label={`${t("reports.resultNote")} (${t("common.optional")})`}
                  value={row.note}
                  onChange={(event) => update(row.key, { note: event.target.value })}
                />
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
