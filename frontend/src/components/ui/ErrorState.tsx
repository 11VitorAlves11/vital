import { useTranslation } from "react-i18next";

import { Button } from "./Button";

type ErrorStateProps = {
  message?: string;
  onRetry?: () => void;
};

/** Sits where the content failed, with a way to try again — never a toast that vanishes. */
export function ErrorState({ message, onRetry }: ErrorStateProps) {
  const { t } = useTranslation();
  return (
    <div
      role="alert"
      className="flex flex-col items-start gap-3 rounded-[var(--radius-lg)] border border-flag-alert p-4"
    >
      <p className="text-ink">{message ?? t("errors.generic")}</p>
      {onRetry ? (
        <Button variant="secondary" onClick={onRetry}>
          {t("actions.retry")}
        </Button>
      ) : null}
    </div>
  );
}
