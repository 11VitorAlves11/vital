import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";

import { useIsDesktop } from "../../lib/useMediaQuery";
import { BottomNav } from "./BottomNav";
import { Sidebar } from "./Sidebar";

/**
 * Resolves mobile versus desktop navigation in one place: a bottom bar under md,
 * a sidebar from md up. Only one of them is rendered, so the page never carries
 * two navigation landmarks for assistive technology to choose between.
 */
export function AppShell({ children }: { children: ReactNode }) {
  const { t } = useTranslation();
  const isDesktop = useIsDesktop();

  return (
    <div className="flex min-h-dvh">
      {isDesktop ? <Sidebar /> : null}
      <div className="flex min-w-0 flex-1 flex-col">
        {isDesktop ? null : (
          <header className="border-b border-border px-4 py-3">
            <p className="font-display text-xl text-primary">{t("app.name")}</p>
          </header>
        )}
        {/* Bottom padding clears the mobile nav bar. */}
        <main className="mx-auto w-full max-w-[var(--content-max)] flex-1 p-4 pb-24 md:p-8 md:pb-8">
          {children}
        </main>
      </div>
      {isDesktop ? null : <BottomNav />}
    </div>
  );
}
