import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { useTranslation } from "react-i18next";

import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { Input } from "../components/ui/Input";
import { Select } from "../components/ui/Select";
import { useToast } from "../components/ui/Toast";
import { auth, body as bodyApi } from "../lib/api";
import { ApiError } from "../lib/api/client";
import type { Sex } from "../lib/api/types";
import { formatDate, formatValue } from "../lib/format";
import { LANGUAGES } from "../lib/i18n";
import { useSession } from "../lib/session";
import { useAsync } from "../lib/useAsync";

/** Whole years at today's date, or null when there is no birth date to count from. */
function ageFrom(birthDate: string): number | null {
  if (!birthDate) return null;
  const born = new Date(birthDate);
  if (Number.isNaN(born.getTime())) return null;
  const today = new Date();
  let years = today.getFullYear() - born.getFullYear();
  const monthDelta = today.getMonth() - born.getMonth();
  // Not yet had this year's birthday, so a year has not completed.
  if (monthDelta < 0 || (monthDelta === 0 && today.getDate() < born.getDate())) years -= 1;
  return years >= 0 && years < 130 ? years : null;
}

export function Profile() {
  const { t, i18n } = useTranslation();
  const locale = i18n.resolvedLanguage ?? "pt-PT";
  const notify = useToast();
  const { user, setUser, signOut } = useSession();
  const [name, setName] = useState(user?.name ?? "");
  const [sex, setSex] = useState<Sex | "">(user?.sex ?? "");
  const [birthDate, setBirthDate] = useState(user?.birth_date ?? "");
  const [heightCm, setHeightCm] = useState(user?.height_cm ?? "");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  // The latest weigh-in, read-only here: weight is a measurement with a history,
  // not a profile field, and having two places to change it would mean two
  // answers to what someone weighs.
  const { data: body } = useAsync(() => bodyApi.summary());
  const weight = (body ?? []).find((item) => item.metric.slug === "weight");
  const age = ageFrom(birthDate);

  // The session can resolve after this page mounts, and the form has to show
  // what is stored rather than an empty field the user might save over.
  useEffect(() => {
    setName(user?.name ?? "");
    setSex(user?.sex ?? "");
    setBirthDate(user?.birth_date ?? "");
    setHeightCm(user?.height_cm ?? "");
  }, [user]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setBusy(true);
    try {
      setUser(
        await auth.updateProfile({
          name: name || null,
          sex: sex || null,
          birth_date: birthDate || null,
          height_cm: heightCm === "" ? null : Number(heightCm),
        }),
      );
      notify(t("profile.saved"));
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : t("errors.generic"));
    } finally {
      setBusy(false);
    }
  }

  return (
    // A narrow column on a wide shell: centred, or it hangs off the left edge
    // of a page whose other views fill the full content width.
    <section className="mx-auto flex w-full max-w-lg flex-col gap-6">
      <h1 className="font-display text-2xl leading-tight font-medium text-ink">
        {t("profile.title")}
      </h1>

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

          <Input
            label={t("profile.birthDate")}
            type="date"
            value={birthDate}
            onChange={(event) => setBirthDate(event.target.value)}
            hint={age === null ? t("profile.birthDateHint") : t("profile.ageIs", { count: age })}
          />

          <Input
            label={t("profile.height")}
            type="number"
            inputMode="decimal"
            min={100}
            max={250}
            step="0.5"
            unit="cm"
            value={heightCm}
            onChange={(event) => setHeightCm(event.target.value)}
            hint={t("profile.heightHint")}
          />

          {/* Shown, not editable: the number belongs to a weigh-in. */}
          <div className="flex flex-col gap-1">
            <span className="text-sm font-medium text-ink">{t("profile.weight")}</span>
            {weight ? (
              <p className="text-ink">
                <span className="data">
                  {formatValue(weight.latest.value, locale)} {weight.metric.unit}
                </span>
                <span className="text-ink-muted">
                  {" · "}
                  {formatDate(weight.measured_at, locale)}
                </span>
              </p>
            ) : (
              <p className="text-sm text-ink-muted">{t("profile.noWeight")}</p>
            )}
            <p className="text-sm text-ink-muted">{t("profile.weightNote")}</p>
          </div>

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
