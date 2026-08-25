import { NavLink } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { cn } from "../../lib/cn";
import { NAV_ITEMS } from "./navigation";

/** Mobile navigation. Icons always carry their label — never an icon on its own. */
export function BottomNav() {
  const { t } = useTranslation();

  return (
    <nav
      aria-label={t("nav.primary")}
      className="fixed inset-x-0 bottom-0 z-30 border-t border-border bg-surface-raised"
    >
      <ul className="flex">
        {NAV_ITEMS.map(({ to, labelKey, icon: Icon }) => (
          <li key={to} className="flex-1">
            <NavLink
              to={to}
              end={to === "/"}
              className={({ isActive }) =>
                cn(
                  "flex min-h-[var(--touch-target)] flex-col items-center justify-center gap-1 px-1 py-2 text-sm",
                  isActive ? "text-primary" : "text-ink-muted",
                )
              }
            >
              {({ isActive }) => (
                <>
                  <Icon size={24} aria-hidden="true" strokeWidth={isActive ? 2.25 : 1.75} />
                  <span>{t(labelKey)}</span>
                </>
              )}
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  );
}
