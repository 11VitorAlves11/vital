import { CalendarClock, Sigma } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";

import type { Result } from "../../lib/api/types";
import { cn } from "../../lib/cn";
import { formatList, formatRange, formatValue } from "../../lib/format";
import { Button } from "../ui/Button";
import { FlagChip } from "../ui/FlagChip";
import { Markdown } from "../ui/Markdown";
import { CaveatList } from "./CaveatList";
import { NoteEditor } from "./NoteEditor";
import { ScheduleRepeatForm } from "./ScheduleRepeatForm";

/** One line of a lab report: value in tabular mono, unit, range, flag with label. */
type ResultRowProps = {
  result: Result;
  /** Given only where a note can be written — the report's own page. */
  onAnnotate?: (note: string | null) => Promise<void>;
};

export function ResultRow({ result, onAnnotate }: ResultRowProps) {
  const { t, i18n } = useTranslation();
  const locale = i18n.resolvedLanguage ?? "pt-PT";
  const [scheduling, setScheduling] = useState(false);
  // On a named scale the step is the reference; the two numbers around it read
  // as a pass/fail the marker deliberately is not.
  const range = result.band_label ?? formatRange(result.ref_min, result.ref_max, locale);
  const position = result.range_position === null ? null : Number(result.range_position);
  const quartile =
    position === null || Number.isNaN(position) ? null : Math.min(4, Math.floor(position / 25) + 1);

  return (
    <div className="border-t border-border py-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <Link to={`/biomarkers/${result.biomarker_id}`} className="text-ink hover:text-primary">
          {result.biomarker_name}
        </Link>
        <div className="flex items-center gap-3">
          <span className="data text-ink">
            {formatValue(result.value, locale)}{" "}
            <span className="text-ink-muted">{result.unit}</span>
          </span>
          <span
            className={cn(
              "hidden text-sm text-ink-muted sm:inline",
              // Tabular figures are for numbers; a band name is prose.
              range && !result.band_label && "data",
            )}
          >
            {range ?? t("biomarker.noRange")}
          </span>
          <FlagChip
            flag={result.flag}
            label={result.flag ? t(`flags.${result.flag}`) : t("flags.unclassified")}
          />
        </div>
      </div>
      {quartile ? (
        <p className="mt-1 text-sm text-ink-muted">
          {t("biomarker.rangePosition", {
            position: new Intl.NumberFormat(locale, { maximumFractionDigits: 1 }).format(position!),
            quartile,
          })}
        </p>
      ) : null}
      <CaveatList caveats={result.caveats} className="mt-1.5" />
      {/* A computed value has nothing to annotate or repeat: there is no row
          behind it to attach a note to, or to schedule a fresh reading from. */}
      {result.derived_from ? (
        <p className="mt-1.5 flex items-center gap-1.5 text-sm text-ink-muted">
          <Sigma size={14} aria-hidden="true" className="shrink-0" />
          {t("reports.derivedFrom", { sources: formatList(result.derived_from, locale) })}
        </p>
      ) : (
        <>
          {onAnnotate ? (
            <NoteEditor
              note={result.note}
              noteAt={result.note_at}
              label={t("reports.resultNote")}
              placeholder={t("notes.resultPlaceholder")}
              onSave={onAnnotate}
            />
          ) : result.note ? (
            <Markdown className="mt-1.5 text-sm">{result.note}</Markdown>
          ) : null}
          {result.id ? (
            <>
              <Button
                variant="ghost"
                className="mt-1.5"
                icon={<CalendarClock size={16} aria-hidden="true" />}
                onClick={() => setScheduling(true)}
              >
                {t("repeats.schedule")}
              </Button>
              <ScheduleRepeatForm
                open={scheduling}
                onOpenChange={setScheduling}
                resultId={result.id}
                biomarkerName={result.biomarker_name}
              />
            </>
          ) : null}
        </>
      )}
    </div>
  );
}
