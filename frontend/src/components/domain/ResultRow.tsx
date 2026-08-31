import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";

import type { Result } from "../../lib/api/types";
import { cn } from "../../lib/cn";
import { formatRange, formatValue } from "../../lib/format";
import { FlagChip } from "../ui/FlagChip";
import { Markdown } from "../ui/Markdown";
import { CaveatList } from "./CaveatList";
import { NoteEditor } from "./NoteEditor";

/** One line of a lab report: value in tabular mono, unit, range, flag with label. */
type ResultRowProps = {
  result: Result;
  /** Given only where a note can be written — the report's own page. */
  onAnnotate?: (note: string | null) => Promise<void>;
};

export function ResultRow({ result, onAnnotate }: ResultRowProps) {
  const { t, i18n } = useTranslation();
  const locale = i18n.resolvedLanguage ?? "pt-PT";
  // On a named scale the step is the reference; the two numbers around it read
  // as a pass/fail the marker deliberately is not.
  const range = result.band_label ?? formatRange(result.ref_min, result.ref_max, locale);

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
      <CaveatList caveats={result.caveats} className="mt-1.5" />
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
    </div>
  );
}
