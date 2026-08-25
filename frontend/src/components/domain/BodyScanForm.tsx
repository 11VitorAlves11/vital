import { useState } from "react";
import type { FormEvent } from "react";
import { useTranslation } from "react-i18next";

import { body, catalogue } from "../../lib/api";
import { ApiError } from "../../lib/api/client";
import type { BodyMetric } from "../../lib/api/types";
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
 * Eighteen figures copied off a scale app in one sitting. Ungrouped, that is a
 * wall; grouped the way the scale reports them, it is five short lists.
 */
const GROUPS: { key: string; slugs: string[] }[] = [
  { key: "weight", slugs: ["weight", "bmi"] },
  {
    key: "fat",
    slugs: [
      "body-fat-pct",
      "fat-mass",
      "subcutaneous-fat-pct",
      "visceral-fat-index",
      "waist-circumference",
    ],
  },
  {
    key: "lean",
    slugs: [
      "fat-free-mass",
      "muscle-mass",
      "muscle-rate",
      "skeletal-muscle-mass",
      "bone-mass",
      "protein-mass",
      "protein-pct",
    ],
  },
  { key: "water", slugs: ["water-mass", "water-pct"] },
  { key: "metabolism", slugs: ["bmr", "metabolic-age"] },
];

/** Groups in catalogue order, with anything the catalogue grows later at the end. */
function groupMetrics(metrics: BodyMetric[]): { key: string; metrics: BodyMetric[] }[] {
  const remaining = new Map(metrics.map((metric) => [metric.slug, metric]));
  const grouped = GROUPS.map(({ key, slugs }) => {
    const members: BodyMetric[] = [];
    for (const slug of slugs) {
      const metric = remaining.get(slug);
      if (metric) {
        members.push(metric);
        remaining.delete(slug);
      }
    }
    return { key, metrics: members };
  }).filter((group) => group.metrics.length > 0);

  if (remaining.size > 0) {
    grouped.push({ key: "other", metrics: [...remaining.values()] });
  }
  return grouped;
}

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
        <form className="flex flex-col gap-8" onSubmit={submit} noValidate>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
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
          </div>

          {metrics
            ? groupMetrics(metrics).map((group) => (
                <fieldset key={group.key}>
                  <legend className="mb-3 w-full border-b border-border pb-2 font-display text-base font-medium text-ink">
                    {t(`body.groups.${group.key}`)}
                  </legend>
                  <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                    {group.metrics.map((metric) => (
                      <Input
                        key={metric.id}
                        label={metric.name}
                        unit={metric.unit}
                        inputMode="decimal"
                        value={values[metric.id] ?? ""}
                        onChange={(event) =>
                          setValues((current) => ({
                            ...current,
                            [metric.id]: event.target.value,
                          }))
                        }
                      />
                    ))}
                  </div>
                </fieldset>
              ))
            : null}

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
      )}
    </FormSurface>
  );
}
