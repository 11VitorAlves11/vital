import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";

import type { Result } from "../../lib/api/types";
import { formatRange, formatValue } from "../../lib/format";
import { FlagChip } from "../ui/FlagChip";

/** One line of a lab report: value in tabular mono, unit, range, flag with label. */
export function ResultRow({ result }: { result: Result }) {
  const { t, i18n } = useTranslation();
  const locale = i18n.resolvedLanguage ?? "pt-PT";
  const range = formatRange(result.ref_min, result.ref_max, locale);

  return (
    <div className="flex flex-wrap items-center justify-between gap-2 border-t border-border py-3">
      <Link to={`/biomarkers/${result.biomarker_id}`} className="text-ink hover:text-primary">
        {result.biomarker_name}
      </Link>
      <div className="flex items-center gap-3">
        <span className="data text-ink">
          {formatValue(result.value, locale)} <span className="text-ink-muted">{result.unit}</span>
        </span>
        <span className="data hidden text-sm text-ink-muted sm:inline">
          {range ?? t("biomarker.noRange")}
        </span>
        <FlagChip
          flag={result.flag}
          label={result.flag ? t(`flags.${result.flag}`) : t("flags.unclassified")}
        />
      </div>
    </div>
  );
}
