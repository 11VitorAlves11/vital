import type { FormEvent } from "react";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { repeats } from "../../lib/api";
import { ApiError } from "../../lib/api/client";
import { Button } from "../ui/Button";
import { FormSurface } from "../ui/FormSurface";
import { Input } from "../ui/Input";
import { useToast } from "../ui/Toast";

/** "YYYY-MM", what `<input type="month">` speaks, `monthsAhead` from today. */
function monthValue(monthsAhead: number): string {
  const date = new Date();
  date.setDate(1);
  date.setMonth(date.getMonth() + monthsAhead);
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}`;
}

type ScheduleRepeatFormProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  resultId: string;
  biomarkerName: string;
};

/**
 * Turns one result into a reminder: repeat this marker around a month still to
 * come. The month is all the backend asks for — a day would claim a precision
 * nobody has when setting a reminder months out.
 */
export function ScheduleRepeatForm({
  open,
  onOpenChange,
  resultId,
  biomarkerName,
}: ScheduleRepeatFormProps) {
  const { t } = useTranslation();
  const notify = useToast();
  const [month, setMonth] = useState(() => monthValue(3));
  const [note, setNote] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    const [year, targetMonth] = month.split("-").map(Number);
    if (!year || !targetMonth) {
      setError(t("errors.required"));
      return;
    }

    setBusy(true);
    try {
      await repeats.create({
        result_id: resultId,
        target_year: year,
        target_month: targetMonth,
        note: note.trim() || null,
      });
      notify(t("repeats.created"));
      setNote("");
      onOpenChange(false);
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : t("errors.generic"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <FormSurface
      open={open}
      onOpenChange={onOpenChange}
      title={t("repeats.scheduleTitle", { biomarker: biomarkerName })}
    >
      <form className="flex flex-col gap-4" onSubmit={submit} noValidate>
        <Input
          label={t("repeats.targetMonth")}
          type="month"
          required
          min={monthValue(0)}
          value={month}
          onChange={(event) => setMonth(event.target.value)}
        />
        <label className="flex flex-col gap-1">
          <span className="text-sm font-medium text-ink">
            {`${t("repeats.note")} (${t("common.optional")})`}
          </span>
          <textarea
            rows={3}
            value={note}
            placeholder={t("repeats.notePlaceholder")}
            onChange={(event) => setNote(event.target.value)}
            className="w-full rounded-[var(--radius-md)] border border-border-strong bg-surface-raised px-3 py-2 text-ink placeholder:text-ink-muted"
          />
        </label>

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
