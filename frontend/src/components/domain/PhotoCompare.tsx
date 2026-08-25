import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import type { Photo } from "../../lib/api/types";
import { formatDate } from "../../lib/format";
import { EmptyState } from "../ui/EmptyState";

/**
 * Two photos of the same pose, side by side, picked with a slider each.
 *
 * A slider rather than two dropdowns because the question is "how far apart",
 * not "which file": dragging along the timeline is the gesture that answers it.
 * Each slider announces the date it has landed on, never the index — "3 of 7"
 * tells a screen-reader user nothing about the comparison they are making.
 */
export function PhotoCompare({ photos }: { photos: Photo[] }) {
  const { t, i18n } = useTranslation();
  const locale = i18n.resolvedLanguage ?? "pt-PT";
  // Oldest first: left to right reads as earlier to later.
  const ordered = [...photos].reverse();
  const [left, setLeft] = useState(0);
  const [right, setRight] = useState(Math.max(ordered.length - 1, 0));

  // The pose filter changes the list under the sliders; an index that no longer
  // exists would blank a panel out.
  useEffect(() => {
    setLeft(0);
    setRight(Math.max(ordered.length - 1, 0));
  }, [ordered.length]);

  if (ordered.length < 2) {
    return (
      <EmptyState
        title={t("photos.compareNeedsTwoTitle")}
        description={t("photos.compareNeedsTwoDescription")}
      />
    );
  }

  const pair = [
    { index: Math.min(left, ordered.length - 1), set: setLeft, label: t("photos.compareFirst") },
    { index: Math.min(right, ordered.length - 1), set: setRight, label: t("photos.compareSecond") },
  ];
  const [first, second] = pair.map((side) => ordered[side.index]);
  const days = Math.round(
    Math.abs(new Date(second.taken_on).getTime() - new Date(first.taken_on).getTime()) / 86_400_000,
  );

  return (
    <div className="flex flex-col gap-4">
      <div className="grid grid-cols-2 gap-3">
        {pair.map((side) => {
          const photo = ordered[side.index];
          return (
            <figure key={side.label} className="flex flex-col gap-2">
              <img
                src={`/api/photos/${photo.id}/file`}
                alt={t("photos.imageAlt", {
                  pose: t(`poses.${photo.pose}`),
                  date: formatDate(photo.taken_on, locale),
                })}
                width={photo.width}
                height={photo.height}
                className="w-full rounded-[var(--radius-md)] border border-border bg-surface-raised object-contain"
              />
              <figcaption className="data text-sm text-ink">
                {formatDate(photo.taken_on, locale)}
              </figcaption>
            </figure>
          );
        })}
      </div>

      <p className="text-ink-muted">{t("photos.apart", { count: days })}</p>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        {pair.map((side) => (
          <label key={side.label} className="flex flex-col gap-1 text-sm font-medium text-ink">
            {side.label}
            <input
              type="range"
              min={0}
              max={ordered.length - 1}
              step={1}
              value={side.index}
              onChange={(event) => side.set(Number(event.target.value))}
              aria-valuetext={formatDate(ordered[side.index].taken_on, locale)}
              className="min-h-[var(--touch-target)] w-full accent-[var(--color-primary)]"
            />
          </label>
        ))}
      </div>
    </div>
  );
}
