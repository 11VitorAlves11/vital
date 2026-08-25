import { useState } from "react";
import type { FormEvent } from "react";
import { useTranslation } from "react-i18next";

import { body, catalogue } from "../../lib/api";
import { ApiError } from "../../lib/api/client";
import { toLocalInputValue } from "../../lib/format";
import { useAsync } from "../../lib/useAsync";
import { Button } from "../ui/Button";
import { FormSurface } from "../ui/FormSurface";
import { Input } from "../ui/Input";
import { Skeleton } from "../ui/Skeleton";
import { useToast } from "../ui/Toast";

type BodyScanFormProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCreated: () => void;
};

/**
 * Every field the scale reports, on one surface — the whole point is to copy a
 * screen of numbers in one sitting. Blank fields are simply not recorded.
 */
export function BodyScanForm({ open, onOpenChange, onCreated }: BodyScanFormProps) {
  const { t } = useTranslation();
  const notify = useToast();
  const { data: metrics, loading } = useAsync(() => catalogue.bodyMetrics());
  const [measuredAt, setMeasuredAt] = useState(() => toLocalInputValue(new Date()));
  const [device, setDevice] = useState("");
  const [values, setValues] = useState<Record<number, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    const filled = Object.entries(values)
      .filter(([, value]) => value.trim() !== "")
      .map(([metricId, value]) => ({
        metric_id: Number(metricId),
        value: Number(value.replace(",", ".")),
      }));

    if (filled.length === 0) {
      setError(t("body.atLeastOneValue"));
      return;
    }

    setBusy(true);
    try {
      await body.createScan({
        measured_at: new Date(measuredAt).toISOString(),
        device: device || null,
        values: filled,
      });
      notify(t("body.created"));
      setValues({});
      onCreated();
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
      title={t("body.newScan")}
      description={t("body.estimateWarning")}
    >
      {loading ? (
        <Skeleton lines={8} label={t("common.loading")} />
      ) : (
        <form className="flex flex-col gap-4" onSubmit={submit} noValidate>
          <Input
            label={t("body.measuredAt")}
            type="datetime-local"
            required
            value={measuredAt}
            onChange={(event) => setMeasuredAt(event.target.value)}
          />
          <Input
            label={`${t("body.device")} (${t("common.optional")})`}
            value={device}
            onChange={(event) => setDevice(event.target.value)}
          />

          <fieldset className="grid grid-cols-1 gap-3 md:grid-cols-2">
            <legend className="mb-2 font-display text-lg text-ink">{t("body.values")}</legend>
            {metrics?.map((metric) => (
              <Input
                key={metric.id}
                label={metric.name}
                unit={metric.unit}
                inputMode="decimal"
                value={values[metric.id] ?? ""}
                onChange={(event) =>
                  setValues((current) => ({ ...current, [metric.id]: event.target.value }))
                }
              />
            ))}
          </fieldset>

          {error ? (
            <p role="alert" className="text-sm text-flag-alert">
              {error}
            </p>
          ) : null}

          <div className="flex gap-2">
            <Button type="submit" loading={busy}>
              {t("actions.save")}
            </Button>
            <Button variant="ghost" onClick={() => onOpenChange(false)}>
              {t("actions.cancel")}
            </Button>
          </div>
        </form>
      )}
    </FormSurface>
  );
}
