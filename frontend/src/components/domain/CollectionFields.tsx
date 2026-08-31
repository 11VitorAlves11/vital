import { useTranslation } from "react-i18next";

import type { CollectionContext, FastingState } from "../../lib/api/types";
import { FASTING_STATES } from "../../lib/api/types";
import { Input } from "../ui/Input";
import { Select } from "../ui/Select";

/** What the two report forms actually hold: strings, because that is what an
 *  input gives back, with the hour kept apart from the day it belongs to. */
export type CollectionDraft = {
  collectedOn: string;
  /** `HH:MM`, or empty when nobody recorded the hour. */
  collectedTime: string;
  fastingState: FastingState;
  /** Kept as typed, so a half-entered number does not become a 0. */
  fastingHours: string;
};

export function emptyCollection(collectedOn: string): CollectionDraft {
  return { collectedOn, collectedTime: "", fastingState: "unknown", fastingHours: "" };
}

/** The draft as the API takes it. An hour is sent as a local wall-clock moment
 *  on the collection date; hours of fasting only travel with a declared fast. */
export function toCollectionContext(draft: CollectionDraft): CollectionContext {
  const hours = Number.parseInt(draft.fastingHours, 10);
  return {
    collected_on: draft.collectedOn,
    collected_at: draft.collectedTime ? `${draft.collectedOn}T${draft.collectedTime}:00` : null,
    fasting_state: draft.fastingState,
    fasting_hours:
      draft.fastingState === "fasting" && Number.isFinite(hours) && hours >= 0 ? hours : null,
  };
}

type CollectionFieldsProps = {
  value: CollectionDraft;
  onChange: (patch: Partial<CollectionDraft>) => void;
};

/**
 * The pre-analytical half of a report: when the blood was drawn and in what
 * state. Shared by manual entry and extraction confirmation so the two cannot
 * offer different answers to the same question.
 *
 * Fasting is three options rather than a checkbox. An unticked box says "they
 * had eaten" when it usually means "nobody wrote it down", and only one of those
 * is worth warning about later.
 */
export function CollectionFields({ value, onChange }: CollectionFieldsProps) {
  const { t } = useTranslation();

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
      <Input
        label={t("reports.collectedOn")}
        type="date"
        required
        value={value.collectedOn}
        onChange={(event) => onChange({ collectedOn: event.target.value })}
      />
      <Input
        label={`${t("reports.collectedTime")} (${t("common.optional")})`}
        type="time"
        value={value.collectedTime}
        hint={t("reports.collectedTimeHint")}
        onChange={(event) => onChange({ collectedTime: event.target.value })}
      />
      <Select
        label={t("reports.fastingState")}
        options={FASTING_STATES.map((state) => ({
          value: state,
          label: t(`fastingStates.${state}`),
        }))}
        value={value.fastingState}
        onChange={(event) => onChange({ fastingState: event.target.value as FastingState })}
      />
      {/* Only where it can mean something: hours of a fast nobody claims
          happened describe nothing, and the API refuses them. */}
      {value.fastingState === "fasting" ? (
        <Input
          label={`${t("reports.fastingHours")} (${t("common.optional")})`}
          type="number"
          min={0}
          max={96}
          inputMode="numeric"
          value={value.fastingHours}
          onChange={(event) => onChange({ fastingHours: event.target.value })}
        />
      ) : null}
    </div>
  );
}
