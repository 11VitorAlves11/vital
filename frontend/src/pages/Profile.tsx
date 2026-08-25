import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { useTranslation } from "react-i18next";

import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { Input } from "../components/ui/Input";
import { Select } from "../components/ui/Select";
import { useToast } from "../components/ui/Toast";
import { auth } from "../lib/api";
import { ApiError } from "../lib/api/client";
import type { Sex } from "../lib/api/types";
import { LANGUAGES } from "../lib/i18n";
import { useSession } from "../lib/session";

export function Profile() {
  const { t, i18n } = useTranslation();
  const notify = useToast();
  const { user, setUser, signOut } = useSession();
  const [name, setName] = useState(user?.name ?? "");
  const [sex, setSex] = useState<Sex | "">(user?.sex ?? "");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  // The session can resolve after this page mounts, and the form has to show
  // what is stored rather than an empty field the user might save over.
  useEffect(() => {
    setName(user?.name ?? "");
    setSex(user?.sex ?? "");
  }, [user]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setBusy(true);
    try {
      setUser(await auth.updateProfile({ name: name || null, sex: sex || null }));
      notify(t("profile.saved"));
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : t("errors.generic"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="flex max-w-lg flex-col gap-6">
      <h1 className="font-display text-2xl text-ink">{t("profile.title")}</h1>

      <Card>
        <form className="flex flex-col gap-4" onSubmit={submit} noValidate>
          {user?.email ? (
            <p className="text-ink-muted">
              {t("profile.email")}: <span className="data text-ink">{user.email}</span>
            </p>
          ) : null}

          <Input
            label={t("profile.name")}
            value={name}
            autoComplete="name"
            onChange={(event) => setName(event.target.value)}
          />

          <Select
            label={t("sex.label")}
            placeholder={t("sex.unset")}
            value={sex}
            onChange={(event) => setSex(event.target.value as Sex | "")}
            options={[
              { value: "M", label: t("sex.M") },
              { value: "F", label: t("sex.F") },
            ]}
          />
          <p className="text-sm text-ink-muted">
            {t("sex.why")} {t("profile.sexNote")}
          </p>

          {error ? (
            <p role="alert" className="text-sm text-flag-alert">
              {error}
            </p>
          ) : null}

          <Button type="submit" loading={busy}>
            {t("actions.save")}
          </Button>
        </form>
      </Card>

      <Card>
        <Select
          label={t("profile.language")}
          value={i18n.resolvedLanguage ?? "pt-PT"}
          onChange={(event) => void i18n.changeLanguage(event.target.value)}
          options={LANGUAGES.map((language) => ({
            value: language.code,
            label: language.label,
          }))}
        />
      </Card>

      <Button variant="secondary" onClick={() => void signOut()}>
        {t("actions.logout")}
      </Button>
    </section>
  );
}
