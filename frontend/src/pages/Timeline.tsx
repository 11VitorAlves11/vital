import { CalendarClock } from "lucide-react";
import { useCallback, useState } from "react";
import { useTranslation } from "react-i18next";

import { TimelineEventCard } from "../components/domain/TimelineEventCard";
import { KIND_STYLES } from "../components/domain/timelineKinds";
import { SubNav } from "../components/layout/SubNav";
import { Button } from "../components/ui/Button";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorState } from "../components/ui/ErrorState";
import { Skeleton } from "../components/ui/Skeleton";
import { timeline } from "../lib/api";
import type { TimelineEvent, TimelineKind } from "../lib/api/types";
import { cn } from "../lib/cn";
import { useAsync } from "../lib/useAsync";

type Month = { key: string; label: string; events: TimelineEvent[] };
type Year = { year: string; months: Month[] };

/** Group a flat, already-sorted list into the year and month headings the rail
 *  sticks to. Order is preserved throughout — the server sorted it. */
function groupByMonth(events: TimelineEvent[], locale: string): Year[] {
  const years: Year[] = [];
  for (const event of events) {
    const [year, month] = event.occurred_on.split("-");
    const label = new Intl.DateTimeFormat(locale, { month: "long" }).format(
      new Date(Number(year), Number(month) - 1, 1),
    );
    let bucket = years.at(-1);
    if (bucket?.year !== year) {
      bucket = { year, months: [] };
      years.push(bucket);
    }
    const key = `${year}-${month}`;
    let months = bucket.months.at(-1);
    if (months?.key !== key) {
      months = { key, label, events: [] };
      bucket.months.push(months);
    }
    months.events.push(event);
  }
  return years;
}

/**
 * Everything that happened, in one column.
 *
 * Single column on purpose: an alternating left/right timeline throws away half
 * the width and needs a second layout for a phone, and this is the same
 * component on both. The rail carries a node per moment and a bar per period.
 */
export function Timeline() {
  const { t, i18n } = useTranslation();
  const locale = i18n.resolvedLanguage ?? "pt-PT";
  const [kinds, setKinds] = useState<TimelineKind[]>([]);
  const [pages, setPages] = useState<TimelineEvent[][]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const [loadingMore, setLoadingMore] = useState(false);

  // The first page also resets the accumulated ones, so changing the filter
  // starts the list again rather than appending a different query's results.
  const load = useCallback(async () => {
    const page = await timeline.read({ kinds: kinds.length ? kinds : undefined });
    setPages([page.events]);
    setCursor(page.next_before);
    return page;
  }, [kinds]);

  const { data, loading, error, reload } = useAsync(load, [kinds.join(",")]);

  async function loadMore() {
    if (cursor === null) return;
    setLoadingMore(true);
    try {
      const page = await timeline.read({
        kinds: kinds.length ? kinds : undefined,
        before: cursor,
      });
      setPages((current) => [...current, page.events]);
      setCursor(page.next_before);
    } finally {
      setLoadingMore(false);
    }
  }

  function toggle(kind: TimelineKind) {
    setKinds((current) =>
      current.includes(kind) ? current.filter((item) => item !== kind) : [...current, kind],
    );
  }

  const events = pages.flat();
  const years = groupByMonth(events, locale);

  return (
    <section>
      <SubNav
        label={t("nav.timelineSection")}
        items={[
          { to: "/timeline", label: t("timeline.title") },
          { to: "/interventions", label: t("interventions.title") },
        ]}
      />

      <h1 className="mt-6 font-display text-2xl leading-tight font-medium text-ink">
        {t("timeline.title")}
      </h1>

      {/* Offered only for what exists. A filter that can return nothing is a
          control the reader has to learn is useless. */}
      {data && data.available_kinds.length > 1 ? (
        <div className="mt-4 flex flex-wrap gap-2" role="group" aria-label={t("timeline.filter")}>
          {data.available_kinds.map((kind) => {
            const active = kinds.includes(kind);
            const Icon = KIND_STYLES[kind].icon;
            return (
              <button
                key={kind}
                type="button"
                aria-pressed={active}
                onClick={() => toggle(kind)}
                className={cn(
                  "inline-flex min-h-[var(--touch-target)] items-center gap-2 rounded-[var(--radius-md)] border px-3 text-sm",
                  active
                    ? "border-primary bg-band text-ink"
                    : "border-border text-ink-muted hover:text-ink",
                )}
              >
                <Icon size={16} aria-hidden="true" />
                {t(`timelineKinds.${kind}`)}
              </button>
            );
          })}
        </div>
      ) : null}

      <div className="mt-6">
        {loading ? <Skeleton lines={8} label={t("common.loading")} /> : null}
        {error ? <ErrorState onRetry={reload} /> : null}

        {data && events.length === 0 ? (
          <EmptyState
            icon={<CalendarClock size={24} aria-hidden="true" className="text-ink-muted" />}
            title={t("timeline.emptyTitle")}
            description={t("timeline.emptyDescription")}
          />
        ) : null}

        {years.map((year) => (
          <section key={year.year}>
            <h2 className="sticky top-0 z-20 bg-surface py-1 font-display text-lg font-medium text-ink">
              {year.year}
            </h2>
            {year.months.map((month) => (
              <section key={month.key}>
                {/* Below the year, so scrolling through a long year keeps both
                    the year and the month it is in on screen. */}
                <h3 className="sticky top-8 z-10 bg-surface py-1 text-sm text-ink-muted capitalize">
                  {month.label}
                </h3>
                <ol className="flex flex-col">
                  {month.events.map((event) => (
                    <li key={event.id} className="grid grid-cols-[1.25rem_1fr] gap-3">
                      {/* The rail: a continuous line, a node for a moment and a
                          bar for a period. Drawn per row so the line runs
                          unbroken behind the whole month. */}
                      <div className="relative flex justify-center" aria-hidden="true">
                        <span className="absolute inset-y-0 w-px bg-border" />
                        <span
                          className={cn(
                            "relative mt-3 rounded-full",
                            KIND_STYLES[event.kind].dot,
                            event.has_duration ? "h-8 w-1.5" : "size-2.5",
                          )}
                        />
                      </div>
                      <div className="min-w-0 pb-3">
                        <TimelineEventCard event={event} />
                      </div>
                    </li>
                  ))}
                </ol>
              </section>
            ))}
          </section>
        ))}

        {cursor !== null && events.length > 0 ? (
          <div className="mt-4 flex justify-center">
            <Button variant="secondary" loading={loadingMore} onClick={() => void loadMore()}>
              {t("timeline.loadMore")}
            </Button>
          </div>
        ) : null}
      </div>
    </section>
  );
}
