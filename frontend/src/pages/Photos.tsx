import { Camera, Trash2 } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { PhotoCompare } from "../components/domain/PhotoCompare";
import { SubNav } from "../components/layout/SubNav";
import { Button } from "../components/ui/Button";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorState } from "../components/ui/ErrorState";
import { Select } from "../components/ui/Select";
import { Skeleton } from "../components/ui/Skeleton";
import { Tabs } from "../components/ui/Tabs";
import { useToast } from "../components/ui/Toast";
import { photos as photosApi } from "../lib/api";
import type { Pose } from "../lib/api/types";
import { POSES } from "../lib/api/types";
import { formatDate } from "../lib/format";
import { useAsync } from "../lib/useAsync";
import { PhotoCreate } from "./PhotoCreate";

export function Photos() {
  const { t, i18n } = useTranslation();
  const locale = i18n.resolvedLanguage ?? "pt-PT";
  const notify = useToast();
  const [pose, setPose] = useState<Pose | "">("");
  const [creating, setCreating] = useState(false);
  const { data, loading, error, reload } = useAsync(
    () => photosApi.list({ pose: pose || undefined }),
    [pose],
  );

  async function remove(id: string) {
    await photosApi.remove(id);
    notify(t("photos.deleted"));
    reload();
  }

  const gallery =
    data && data.length > 0 ? (
      <ul className="grid grid-cols-2 gap-4 md:grid-cols-3">
        {data.map((photo) => (
          <li key={photo.id} className="flex flex-col gap-2">
            <img
              src={`/api/photos/${photo.id}/file`}
              alt={t("photos.imageAlt", {
                pose: t(`poses.${photo.pose}`),
                date: formatDate(photo.taken_on, locale),
              })}
              // The stored dimensions come down with the list, so the grid
              // reserves the right box instead of reflowing as images land.
              width={photo.width}
              height={photo.height}
              loading="lazy"
              className="w-full rounded-[var(--radius-md)] border border-border bg-surface-raised object-contain"
            />
            <div className="flex items-baseline justify-between gap-2">
              <span className="data text-sm text-ink">{formatDate(photo.taken_on, locale)}</span>
              <span className="text-sm text-ink-muted">{t(`poses.${photo.pose}`)}</span>
            </div>
            {photo.notes ? <p className="text-sm text-ink-muted">{photo.notes}</p> : null}
            <div>
              <Button
                variant="ghost"
                icon={<Trash2 size={20} aria-hidden="true" />}
                onClick={() => void remove(photo.id)}
              >
                {t("actions.delete")}
              </Button>
            </div>
          </li>
        ))}
      </ul>
    ) : (
      <EmptyState
        title={t("photos.emptyTitle")}
        description={t("photos.emptyDescription")}
        icon={<Camera size={28} className="text-ink-muted" aria-hidden="true" />}
        action={<Button onClick={() => setCreating(true)}>{t("photos.new")}</Button>}
      />
    );

  return (
    <section className="flex flex-col gap-6">
      <SubNav
        label={t("nav.bodySection")}
        items={[
          { to: "/body", label: t("body.title") },
          { to: "/photos", label: t("photos.title") },
        ]}
      />

      <header className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="font-display text-2xl leading-tight font-medium text-ink">
          {t("photos.title")}
        </h1>
        <Button icon={<Camera size={20} aria-hidden="true" />} onClick={() => setCreating(true)}>
          {t("photos.new")}
        </Button>
      </header>

      <p className="max-w-prose text-sm text-ink-muted">{t("photos.privacyNote")}</p>

      <div className="md:max-w-xs">
        <Select
          label={t("photos.pose")}
          value={pose}
          placeholder={t("photos.allPoses")}
          onChange={(event) => setPose(event.target.value as Pose | "")}
          options={POSES.map((value) => ({ value, label: t(`poses.${value}`) }))}
        />
      </div>

      {loading ? <Skeleton lines={6} label={t("common.loading")} /> : null}
      {error ? <ErrorState onRetry={reload} /> : null}

      {data ? (
        <Tabs
          aria-label={t("photos.viewLabel")}
          items={[
            { value: "gallery", label: t("photos.gallery"), content: gallery },
            {
              value: "compare",
              label: t("photos.compare"),
              // Comparing across poses would be comparing two different things,
              // so the filter above is what makes the mode meaningful.
              content: <PhotoCompare photos={data} />,
            },
          ]}
        />
      ) : null}

      <PhotoCreate open={creating} onOpenChange={setCreating} onCreated={reload} />
    </section>
  );
}
