import { useState } from "react";
import type { FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Navigate } from "react-router-dom";

import { LogoMark } from "../components/brand/Logo";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { Input } from "../components/ui/Input";
import { Select } from "../components/ui/Select";
import { Skeleton } from "../components/ui/Skeleton";
import { auth } from "../lib/api";
import { ApiError } from "../lib/api/client";
import type { Sex } from "../lib/api/types";
import { useSession } from "../lib/session";

export function Login() {
  const { t } = useTranslation();
  const { user, mode, loading, setUser } = useSession();
  const [registering, setRegistering] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [sex, setSex] = useState<Sex | "">("");
  const [heightCm, setHeightCm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (loading) return <Skeleton className="mx-auto mt-24 max-w-sm" lines={5} />;
  if (user) return <Navigate to="/" replace />;

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const account = registering
        ? await auth.register({
            email,
            password,
            name: name || undefined,
            sex: sex || null,
            height_cm: heightCm === "" ? null : Number(heightCm),
          })
        : await auth.login(email, password);
      setUser(account);
    } catch (cause) {
      if (cause instanceof ApiError && cause.isUnauthorized) setError(t("errors.invalidCredentials"));
      else setError(cause instanceof ApiError ? cause.message : t("errors.generic"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="mx-auto flex min-h-dvh max-w-sm flex-col justify-center gap-6 p-6">
      <div>
        <h1 className="flex items-center gap-3 font-display text-3xl text-primary">
          <LogoMark className="h-11 w-auto shrink-0" />
          {t("app.name")}
        </h1>
        <p className="mt-1 text-ink-muted">{t("auth.loginSubtitle")}</p>
      </div>

      {mode === "oidc" ? (
        <Card>
          <p className="mb-4 text-ink-muted">{t("auth.oidcHint")}</p>
          {/* A full page load, not fetch: the provider answers with a redirect. */}
          <Button className="w-full" onClick={() => window.location.assign("/auth/login")}>
            {t("actions.loginWithProvider")}
          </Button>
        </Card>
      ) : (
        <Card>
          <form className="flex flex-col gap-4" onSubmit={submit} noValidate>
            <h2 className="font-display text-xl text-ink">
              {registering ? t("auth.registerTitle") : t("auth.loginTitle")}
            </h2>
            <Input
              label={t("auth.email")}
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(event) => setEmail(event.target.value)}
            />
            <Input
              label={t("auth.password")}
              type="password"
              autoComplete={registering ? "new-password" : "current-password"}
              required
              minLength={registering ? 10 : undefined}
              hint={registering ? t("auth.passwordHint") : undefined}
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
            {registering ? (
              <>
                <Input
                  label={t("auth.name")}
                  autoComplete="name"
                  value={name}
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
                <p className="text-sm text-ink-muted">{t("sex.why")}</p>
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
              </>
            ) : null}

            {error ? (
              <p role="alert" className="text-sm text-flag-alert">
                {error}
              </p>
            ) : null}

            <Button type="submit" loading={busy}>
              {registering ? t("actions.register") : t("actions.login")}
            </Button>
            <Button variant="ghost" onClick={() => setRegistering((value) => !value)}>
              {registering ? t("auth.haveAccount") : t("auth.noAccount")}
            </Button>
          </form>
        </Card>
      )}
    </main>
  );
}
