import { NavLink } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { cn } from "../../lib/cn";
import { NAV_ITEMS } from "./navigation";

/** Desktop navigation. */
export function Sidebar() {
  const { t } = useTranslation();

  return (
    <nav
      aria-label={t("nav.primary")}
      className="w-56 shrink-0 border-r border-border bg-surface-raised p-4"
    >
      <p className="mb-6 px-2 font-display text-xl text-primary">{t("app.name")}</p>
      <ul className="flex flex-col gap-1">
        {NAV_ITEMS.map(({ to, labelKey, icon: Icon }) => (
          <li key={to}>
            <NavLink
              to={to}
              end={to === "/"}
              className={({ isActive }) =>
                cn(
                  "flex min-h-[var(--touch-target)] items-center gap-3 rounded-[var(--radius-md)] px-3",
                  isActive ? "bg-band text-primary" : "text-ink-muted hover:text-ink",
                )
              }
            >
              <Icon size={20} aria-hidden="true" />
              <span>{t(labelKey)}</span>
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  );
}
