import { Pencil } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { formatDateTime } from "../../lib/format";
import { Button } from "../ui/Button";
import { Markdown } from "../ui/Markdown";

type NoteEditorProps = {
  note: string | null;
  /** When it was last written — a year-old reading must not read as today's. */
  noteAt: string | null;
  label: string;
  placeholder: string;
  onSave: (note: string | null) => Promise<void>;
};

/**
 * A note someone writes against a report or against one of its values.
 *
 * Read mode by default, because a note is read far more often than it is
 * written, and an always-open textarea makes a page of them look like a form.
 * Line breaks are preserved as typed; nothing else is interpreted.
 */
export function NoteEditor({ note, noteAt, label, placeholder, onSave }: NoteEditorProps) {
  const { t, i18n } = useTranslation();
  const locale = i18n.resolvedLanguage ?? "pt-PT";
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(note ?? "");
  const [busy, setBusy] = useState(false);

  async function save() {
    setBusy(true);
    try {
      await onSave(draft.trim() || null);
      setEditing(false);
    } finally {
      setBusy(false);
    }
  }

  if (!editing) {
    return (
      <div className="flex flex-col items-start gap-1">
        {note ? (
          <>
            <Markdown>{note}</Markdown>
            {noteAt ? (
              <p className="text-sm text-ink-muted">
                {t("notes.writtenAt", { when: formatDateTime(noteAt, locale) })}
              </p>
            ) : null}
          </>
        ) : null}
        <Button
          variant="ghost"
          icon={<Pencil size={16} aria-hidden="true" />}
          onClick={() => {
            setDraft(note ?? "");
            setEditing(true);
          }}
        >
          {note ? t("notes.edit") : t("notes.add")}
        </Button>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-2">
      <label className="flex flex-col gap-1">
        <span className="text-sm font-medium text-ink">{label}</span>
        <span className="text-sm text-ink-muted">{t("notes.markdownHint")}</span>
        <textarea
          rows={4}
          autoFocus
          value={draft}
          placeholder={placeholder}
          onChange={(event) => setDraft(event.target.value)}
          className="w-full rounded-[var(--radius-md)] border border-border-strong bg-surface-raised px-3 py-2 text-ink placeholder:text-ink-muted"
        />
      </label>
      <div className="flex gap-2">
        <Button loading={busy} onClick={() => void save()}>
          {t("actions.save")}
        </Button>
        <Button variant="ghost" onClick={() => setEditing(false)}>
          {t("actions.cancel")}
        </Button>
      </div>
    </div>
  );
}
