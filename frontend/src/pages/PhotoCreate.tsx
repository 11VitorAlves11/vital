import { Camera } from "lucide-react";
import { useRef, useState } from "react";
import type { ChangeEvent, FormEvent } from "react";
import { useTranslation } from "react-i18next";

import { Button } from "../components/ui/Button";
import { FormSurface } from "../components/ui/FormSurface";
import { Input } from "../components/ui/Input";
import { Select } from "../components/ui/Select";
import { useToast } from "../components/ui/Toast";
import { photos } from "../lib/api";
import { ApiError } from "../lib/api/client";
import type { Pose } from "../lib/api/types";
import { POSES } from "../lib/api/types";
import { todayInputValue } from "../lib/format";

type PhotoCreateProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCreated: () => void;
};

export function PhotoCreate({ open, onOpenChange, onCreated }: PhotoCreateProps) {
  const { t } = useTranslation();
  const notify = useToast();
  const [file, setFile] = useState<File | null>(null);
  const [takenOn, setTakenOn] = useState(todayInputValue());
  const [pose, setPose] = useState<Pose>("frente");
  const [notes, setNotes] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);

  function pick(event: ChangeEvent<HTMLInputElement>) {
    setFile(event.target.files?.[0] ?? null);
    setError(null);
  }

  function reset() {
    setFile(null);
    setNotes("");
    setError(null);
    if (fileInput.current) fileInput.current.value = "";
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (file === null) {
      setError(t("photos.pickAPhoto"));
      return;
    }
    setError(null);
    setBusy(true);
    try {
      await photos.create({ file, taken_on: takenOn, pose, notes: notes || undefined });
      notify(t("photos.created"));
      reset();
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
      title={t("photos.new")}
      description={t("photos.privacyNote")}
    >
      <form className="flex flex-col gap-6" onSubmit={submit} noValidate>
        <label className="flex cursor-pointer flex-col items-center gap-3 rounded-[var(--radius-lg)] border border-dashed border-border-strong p-6 text-center hover:bg-band">
          <Camera size={28} className="text-ink-muted" aria-hidden="true" />
          <span className="font-display text-lg text-ink">
            {file ? file.name : t("photos.pickFile")}
          </span>
          <input
            ref={fileInput}
            type="file"
            accept="image/*"
            // On a phone this opens the camera directly rather than the gallery,
            // which is where a progress photo is usually taken.
            capture="environment"
            className="sr-only"
            onChange={pick}
          />
        </label>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <Input
            label={t("photos.takenOn")}
            type="date"
            required
            value={takenOn}
            onChange={(event) => setTakenOn(event.target.value)}
          />
          <Select
            label={t("photos.pose")}
            value={pose}
            onChange={(event) => setPose(event.target.value as Pose)}
            options={POSES.map((value) => ({ value, label: t(`poses.${value}`) }))}
          />
        </div>

        <Input
          label={`${t("photos.notes")} (${t("common.optional")})`}
          value={notes}
          onChange={(event) => setNotes(event.target.value)}
        />

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
    </FormSurface>
  );
}
