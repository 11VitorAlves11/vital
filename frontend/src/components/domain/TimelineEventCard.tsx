import { ChevronDown } from "lucide-react";
import { useId, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import type { TimelineEvent } from "../../lib/api/types";
import { cn } from "../../lib/cn";
import { formatDate, formatTime } from "../../lib/format";
import { FlagChip } from "../ui/FlagChip";
import { KINDS_WITH_A_MEANINGFUL_HOUR, KIND_STYLES } from "./timelineKinds";

/** The one-line heading of a card: what it is, and when — with the hour only
 *  where an hour changes how it reads. */
function when(event: TimelineEvent, locale: string): string {
  const day = formatDate(event.occurred_on, locale);
  if (!event.occurred_at || !KINDS_WITH_A_MEANINGFUL_HOUR.includes(event.kind)) return day;
  return `${day} · ${formatTime(event.occurred_at, locale)}`;
}

/**
 * One event, compact by default and expandable in place.
 *
 * Expanding never navigates. The point of a timeline is the sequence, and a
 * card that takes the reader off the page to say four more words costs them
 * their position in it.
 */
export function TimelineEventCard({ event }: { event: TimelineEvent }) {
  const { t, i18n } = useTranslation();
  const locale = i18n.resolvedLanguage ?? "pt-PT";
  const [open, setOpen] = useState(false);
  const bodyId = useId();
  const style = KIND_STYLES[event.kind];
  const expandable = event.summary.length > 0 || event.href !== null;

  const title =
    event.title ||
    (event.kind === "progress_photo" && event.pose ? t(`poses.${event.pose}`) : t(`nav.timeline`));

  return (
    <div className="rounded-[var(--radius-md)] border border-border bg-surface-raised">
      <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1 px-3 py-2">
        <div className="flex min-w-0 flex-col">
          <span className="truncate font-medium text-ink">{title}</span>
          <span className="text-sm text-ink-muted">
            {when(event, locale)}
            {event.subtitle ? ` · ${event.subtitle}` : ""}
            {/* An open-ended period says so rather than showing a blank end. */}
            {event.has_duration
              ? ` · ${
                  event.ended_on
                    ? t("timeline.until", { date: formatDate(event.ended_on, locale) })
                    : t("timeline.ongoing")
                }`
              : ""}
          </span>
        </div>
        <span className={cn("text-sm", style.text)}>{t(`timelineKinds.${event.kind}`)}</span>
      </div>

      {expandable ? (
        <>
          <button
            type="button"
            aria-expanded={open}
            aria-controls={bodyId}
            onClick={() => setOpen((current) => !current)}
            className="flex min-h-[var(--touch-target)] w-full items-center gap-1.5 px-3 text-sm text-ink-muted hover:text-ink"
          >
            <ChevronDown
              size={16}
              aria-hidden="true"
              className={cn(
                "transition-transform duration-[var(--duration-fast)]",
                open && "rotate-180",
              )}
            />
            {open ? t("timeline.collapse") : t("timeline.expand")}
          </button>

          {open ? (
            <div id={bodyId} className="flex flex-col gap-2 px-3 pt-1 pb-3">
              {event.summary.length > 0 ? (
                <ul className="flex flex-col gap-1">
                  {event.summary.map((item) => (
                    <li
                      key={item.label}
                      className="flex flex-wrap items-center justify-between gap-2 text-sm"
                    >
                      <span className="text-ink">{item.label}</span>
                      <span className="flex items-center gap-2">
                        <span className="data text-ink">{item.value}</span>
                        {item.flag ? (
                          <FlagChip flag={item.flag} label={t(`flags.${item.flag}`)} />
                        ) : null}
                      </span>
                    </li>
                  ))}
                </ul>
              ) : null}
              {event.href ? (
                <Link
                  to={event.href}
                  className="text-sm text-primary underline-offset-4 hover:underline"
                >
                  {t("timeline.open")}
                </Link>
              ) : null}
            </div>
          ) : null}
        </>
      ) : null}
    </div>
  );
}
