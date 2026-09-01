import { ArrowDown, ArrowRight, ArrowUp, Minus } from "lucide-react";
import { Fragment } from "react";
import { useTranslation } from "react-i18next";
import { Link, useSearchParams } from "react-router-dom";

import { CaveatList } from "../components/domain/CaveatList";
import { Card } from "../components/ui/Card";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorState } from "../components/ui/ErrorState";
import { FlagChip } from "../components/ui/FlagChip";
import { LinkButton } from "../components/ui/LinkButton";
import { Select } from "../components/ui/Select";
import { Skeleton } from "../components/ui/Skeleton";
import { reports } from "../lib/api";
import type {
  BiomarkerCategory,
  ComparisonRow,
  ReportComparison,
  ReportSummary,
  Result,
} from "../lib/api/types";
import { formatDate, formatRange, formatSigned, formatValue, toNumber } from "../lib/format";
import { useAsync } from "../lib/useAsync";
import { useIsDesktop } from "../lib/useMediaQuery";

/** Which two collections to compare, from the URL and what exists.
 *
 * One id on its own comes from a report's own page ("compare this one"), and the
 * other side is the draw next to it in time — the comparison somebody landing
 * there means, without asking them to pick it. */
function chosenPair(list: ReportSummary[], a: string | null, b: string | null): [string, string] {
  if (a && b) return [a, b];
  const single = a ?? b;
  if (single) {
    const index = list.findIndex((report) => report.id === single);
    // The list is newest-first, so the next index is the draw before this one,
    // and the previous index is the one after it for the oldest report.
    const neighbour = list[index + 1] ?? list[index - 1];
    return [single, neighbour?.id ?? ""];
  }
  return [list[1]?.id ?? "", list[0]?.id ?? ""];
}

/** The rows as panels, in the order the server sorted them. Both layouts group
 *  the same way the dashboard does: the panel reads before any single row. */
function byPanel(rows: ComparisonRow[]): { category: BiomarkerCategory; rows: ComparisonRow[] }[] {
  const panels: { category: BiomarkerCategory; rows: ComparisonRow[] }[] = [];
  for (const row of rows) {
    const last = panels.at(-1);
    if (last && last.category === row.category) last.rows.push(row);
    else panels.push({ category: row.category, rows: [row] });
  }
  return panels;
}

/** Rows whose flag crossed the interval, in either direction. Derived here
 *  rather than fetched: the rule is the flags, which are already on the page. */
function crossings(rows: ComparisonRow[]) {
  const outside = (result: Result | null) => result?.flag === "low" || result?.flag === "high";
  const pairs = rows.filter((row) => row.previous && row.current);
  return {
    entered: pairs.filter((row) => outside(row.previous) && row.current?.flag === "normal").length,
    left: pairs.filter((row) => row.previous?.flag === "normal" && outside(row.current)).length,
  };
}

/** One side of the diff: the value as the laboratory printed it.
 *
 * A normal value wears no chip — the same silence a lab report keeps — and the
 * range appears only where it moved between the two draws, which is where
 * knowing it changes how the value reads. */
function Reading({
  result,
  unit,
  showRange,
  locale,
}: {
  result: Result | null;
  /** The scale the difference is on, when it is not this result's own unit. */
  unit: string | null;
  showRange: boolean;
  locale: string;
}) {
  const { t } = useTranslation();
  if (!result) return <span className="text-ink-muted">—</span>;

  const range = result.band_label ?? formatRange(result.ref_min, result.ref_max, locale);
  const flagged = result.flag === "low" || result.flag === "high";
  // A draw reported in g/L next to one in g/dL is not the fall the two numbers
  // look like. The converted value is what the difference was actually taken on.
  const converted =
    unit && result.canonical_value !== null && result.unit !== unit
      ? `= ${formatValue(result.canonical_value, locale)} ${unit}`
      : null;

  return (
    <div className="flex flex-col items-end gap-1">
      <span className="data text-ink">
        {formatValue(result.value, locale)} <span className="text-ink-muted">{result.unit}</span>
      </span>
      {converted ? <span className="data text-xs text-ink-muted">{converted}</span> : null}
      {flagged ? (
        <FlagChip
          flag={result.flag}
          label={result.band_label ?? t(`flags.${result.flag}`)}
          className="text-xs"
        />
      ) : null}
      {showRange && range ? <span className="text-xs text-ink-muted">{range}</span> : null}
    </div>
  );
}

/** What moved: an arrow, the signed difference, and the unit it is in. */
function Delta({ row, locale }: { row: ComparisonRow; locale: string }) {
  const { t } = useTranslation();
  if (!row.previous) return <span className="text-sm text-ink-muted">{t("compare.added")}</span>;
  if (!row.current) return <span className="text-sm text-ink-muted">{t("compare.dropped")}</span>;
  if (row.delta === null) return <span className="text-ink-muted">—</span>;

  const value = toNumber(row.delta);
  const Arrow = value > 0 ? ArrowUp : value < 0 ? ArrowDown : Minus;
  return (
    <span className="data inline-flex items-center justify-end gap-1 text-ink">
      {/* Direction only. Whether a rise is good news is the flag's business, and
          a coloured arrow would answer that wrongly for half the markers. */}
      <Arrow size={16} aria-hidden="true" className="shrink-0 text-ink-muted" />
      {formatSigned(row.delta, locale)}
      <span className="text-ink-muted">{row.unit}</span>
    </span>
  );
}

function movedReference(row: ComparisonRow): boolean {
  return row.caveats.some((caveat) => caveat.code === "reference_changed");
}

function MarkerName({ row }: { row: ComparisonRow }) {
  return (
    <Link to={`/biomarkers/${row.biomarker_id}`} className="text-ink hover:text-primary">
      {row.biomarker_name}
    </Link>
  );
}

/** Desktop: one dense table, values aligned in columns the way a report prints them. */
function ComparisonTable({ data, locale }: { data: ReportComparison; locale: string }) {
  const { t } = useTranslation();

  return (
    <Card className="overflow-x-auto p-0">
      <table className="w-full">
        <caption className="sr-only">
          {t("compare.caption", {
            previous: formatDate(data.previous.collected_on, locale),
            current: formatDate(data.current.collected_on, locale),
          })}
        </caption>
        <thead>
          <tr className="text-sm text-ink-muted">
            <th scope="col" className="px-4 py-2 text-left font-medium">
              {t("reports.biomarker")}
            </th>
            <th scope="col" className="data px-4 py-2 text-right font-medium">
              {formatDate(data.previous.collected_on, locale)}
            </th>
            <th scope="col" className="data px-4 py-2 text-right font-medium">
              {formatDate(data.current.collected_on, locale)}
            </th>
            <th scope="col" className="px-4 py-2 text-right font-medium">
              {t("compare.delta")}
            </th>
            <th scope="col" className="px-4 py-2 text-right font-medium">
              {t("compare.percent")}
            </th>
          </tr>
        </thead>
        {byPanel(data.rows).map((panel) => (
          <tbody key={panel.category} className="border-t border-border">
            <tr>
              <th
                scope="colgroup"
                colSpan={5}
                className="bg-band px-4 py-2 text-left font-display text-sm font-medium text-ink"
              >
                {t(`categories.${panel.category}`)}
              </th>
            </tr>
            {panel.rows.map((row) => (
              <Fragment key={row.biomarker_id}>
                <tr className="border-t border-border">
                  <th scope="row" className="px-4 py-3 text-left align-top font-normal">
                    <MarkerName row={row} />
                  </th>
                  <td className="px-4 py-3 text-right align-top">
                    <Reading
                      result={row.previous}
                      unit={row.unit}
                      showRange={movedReference(row)}
                      locale={locale}
                    />
                  </td>
                  <td className="px-4 py-3 text-right align-top">
                    <Reading
                      result={row.current}
                      unit={row.unit}
                      showRange={movedReference(row)}
                      locale={locale}
                    />
                  </td>
                  <td className="px-4 py-3 text-right align-top">
                    <Delta row={row} locale={locale} />
                  </td>
                  <td className="px-4 py-3 text-right align-top">
                    {row.percent_change === null ? (
                      <span className="text-ink-muted">—</span>
                    ) : (
                      <span className="data text-ink">
                        {formatSigned(row.percent_change, locale)}%
                      </span>
                    )}
                  </td>
                </tr>
                {row.caveats.length > 0 ? (
                  <tr>
                    <td colSpan={5} className="px-4 pb-3">
                      <CaveatList caveats={row.caveats} />
                    </td>
                  </tr>
                ) : null}
              </Fragment>
            ))}
          </tbody>
        ))}
      </table>
    </Card>
  );
}

/** Mobile: the same rows stacked, because five columns on a phone put the
 *  difference — the one thing the page is for — off the right edge. */
function ComparisonList({ data, locale }: { data: ReportComparison; locale: string }) {
  const { t } = useTranslation();

  return (
    <div className="flex flex-col gap-6">
      {byPanel(data.rows).map((panel) => (
        <section key={panel.category}>
          <h2 className="mb-2 border-b border-border pb-1 font-display text-sm font-medium text-ink">
            {t(`categories.${panel.category}`)}
          </h2>
          <Card className="p-0">
            <ul>
              {panel.rows.map((row) => (
                <li key={row.biomarker_id} className="border-t border-border p-4 first:border-t-0">
                  <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
                    <MarkerName row={row} />
                    <span className="flex items-baseline gap-2">
                      <Delta row={row} locale={locale} />
                      {row.percent_change === null ? null : (
                        <span className="data text-sm text-ink-muted">
                          {formatSigned(row.percent_change, locale)}%
                        </span>
                      )}
                    </span>
                  </div>
                  <dl className="mt-2 flex flex-col gap-2">
                    {(
                      [
                        [data.previous.collected_on, row.previous],
                        [data.current.collected_on, row.current],
                      ] as const
                    ).map(([date, result]) => (
                      <div key={date} className="flex items-baseline justify-between gap-3">
                        <dt className="data text-sm text-ink-muted">{formatDate(date, locale)}</dt>
                        <dd>
                          <Reading
                            result={result}
                            unit={row.unit}
                            showRange={movedReference(row)}
                            locale={locale}
                          />
                        </dd>
                      </div>
                    ))}
                  </dl>
                  <CaveatList caveats={row.caveats} className="mt-2" />
                </li>
              ))}
            </ul>
          </Card>
        </section>
      ))}
    </div>
  );
}

export function ReportCompare() {
  const { t, i18n } = useTranslation();
  const locale = i18n.resolvedLanguage ?? "pt-PT";
  const isDesktop = useIsDesktop();
  const [params, setParams] = useSearchParams();
  const { data: list, loading: listing, error: listError, reload } = useAsync(() => reports.list());
  const [a, b] = chosenPair(list ?? [], params.get("a"), params.get("b"));
  const comparable = Boolean(a && b) && a !== b;

  const {
    data,
    loading,
    error,
    reload: reloadComparison,
  } = useAsync(
    () => (comparable ? reports.compare(a, b) : Promise.resolve(null)),
    [a, b, comparable],
  );

  const options = (list ?? []).map((report) => ({
    value: report.id,
    label: `${formatDate(report.collected_on, locale)} · ${report.lab_name}`,
  }));
  const moved = data ? crossings(data.rows) : { entered: 0, left: 0 };

  if (listing) return <Skeleton lines={6} label={t("common.loading")} />;
  if (listError || !list) return <ErrorState onRetry={reload} />;

  if (list.length < 2) {
    return (
      <EmptyState
        title={t("compare.needTwoTitle")}
        description={t("compare.needTwoDescription")}
        action={<LinkButton to="/reports">{t("reports.new")}</LinkButton>}
      />
    );
  }

  return (
    <section className="flex flex-col gap-6">
      <header>
        <h1 className="font-display text-2xl leading-tight font-medium text-ink">
          {t("compare.title")}
        </h1>
      </header>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 md:max-w-3xl">
        <Select
          label={t("compare.first")}
          options={options}
          value={a}
          onChange={(event) => setParams({ a: event.target.value, b })}
        />
        <Select
          label={t("compare.second")}
          options={options}
          value={b}
          onChange={(event) => setParams({ a, b: event.target.value })}
        />
      </div>

      {!comparable ? <p className="text-ink-muted">{t("compare.samePick")}</p> : null}
      {comparable && loading ? <Skeleton lines={6} label={t("common.loading")} /> : null}
      {error ? <ErrorState onRetry={reloadComparison} /> : null}

      {data ? (
        <>
          {/* Which way round the two are read, said once, so no column header
              has to carry it — and so the arrow between them is the sentence. */}
          <p className="flex flex-wrap items-center gap-x-2 gap-y-1 text-ink">
            <Link to={`/reports/${data.previous.id}`} className="hover:text-primary">
              <span className="data">{formatDate(data.previous.collected_on, locale)}</span>
              <span className="text-ink-muted"> · {data.previous.lab_name}</span>
            </Link>
            <ArrowRight size={16} aria-hidden="true" className="text-ink-muted" />
            <Link to={`/reports/${data.current.id}`} className="hover:text-primary">
              <span className="data">{formatDate(data.current.collected_on, locale)}</span>
              <span className="text-ink-muted"> · {data.current.lab_name}</span>
            </Link>
            {moved.entered > 0 || moved.left > 0 ? (
              <span className="text-sm text-ink-muted">
                {[
                  moved.left > 0 ? t("compare.left", { count: moved.left }) : null,
                  moved.entered > 0 ? t("compare.entered", { count: moved.entered }) : null,
                ]
                  .filter(Boolean)
                  .join(" · ")}
              </span>
            ) : null}
          </p>

          {isDesktop ? (
            <ComparisonTable data={data} locale={locale} />
          ) : (
            <ComparisonList data={data} locale={locale} />
          )}
        </>
      ) : null}
    </section>
  );
}
