import * as RadixDialog from "@radix-ui/react-dialog";

import { cn } from "../../lib/cn";
import { CloseButton, Overlay, type SurfaceProps } from "./Dialog";

/** Mobile surface: full-screen, sliding up from the bottom. */
export function Sheet({ open, onOpenChange, title, description, children, footer }: SurfaceProps) {
  return (
    <RadixDialog.Root open={open} onOpenChange={onOpenChange}>
      <RadixDialog.Portal>
        <Overlay />
        <RadixDialog.Content
          className={cn(
            "fixed inset-x-0 bottom-0 top-8 z-50 flex flex-col gap-4 overflow-y-auto",
            "rounded-t-[var(--radius-lg)] border-t border-border bg-surface-raised p-4",
            "motion-safe:animate-[slide-up_var(--duration-slow)_var(--ease-standard)]",
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
          {footer ? <div className="flex flex-col gap-2 pb-4">{footer}</div> : null}
        </RadixDialog.Content>
      </RadixDialog.Portal>
    </RadixDialog.Root>
  );
}
