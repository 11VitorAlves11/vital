import * as RadixDialog from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";

import { cn } from "../../lib/cn";

export type SurfaceProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description?: string;
  children: ReactNode;
  footer?: ReactNode;
};

export function Overlay() {
  return (
    <RadixDialog.Overlay className="fixed inset-0 z-40 bg-scrim motion-safe:animate-[fade-in_var(--duration-base)_var(--ease-standard)]" />
  );
}

export function CloseButton() {
  const { t } = useTranslation();
  return (
    <RadixDialog.Close
      aria-label={t("actions.close")}
      className="inline-flex size-[var(--touch-target)] items-center justify-center rounded-[var(--radius-md)] text-ink-muted hover:bg-band"
    >
      <X size={20} aria-hidden="true" />
    </RadixDialog.Close>
  );
}

/** Desktop surface: a centred modal. On mobile, use {@link Sheet} instead. */
export function Dialog({
  open,
  onOpenChange,
  title,
  description,
  children,
  footer,
}: SurfaceProps) {
  return (
    <RadixDialog.Root open={open} onOpenChange={onOpenChange}>
      <RadixDialog.Portal>
        <Overlay />
        <RadixDialog.Content
          className={cn(
            "fixed left-1/2 top-1/2 z-50 flex max-h-[85vh] w-[min(40rem,92vw)] -translate-x-1/2 -translate-y-1/2",
            "flex-col gap-4 overflow-y-auto rounded-[var(--radius-lg)] border border-border",
            "bg-surface-raised p-6 shadow-[var(--shadow-card)]",
          )}
        >
          <div className="flex items-start justify-between gap-4">
            <div>
              <RadixDialog.Title className="font-display text-xl text-ink">
                {title}
              </RadixDialog.Title>
              {description ? (
                <RadixDialog.Description className="mt-1 text-ink-muted">
                  {description}
                </RadixDialog.Description>
              ) : null}
            </div>
            <CloseButton />
          </div>
          {children}
          {footer ? <div className="flex justify-end gap-2">{footer}</div> : null}
        </RadixDialog.Content>
      </RadixDialog.Portal>
    </RadixDialog.Root>
  );
}
