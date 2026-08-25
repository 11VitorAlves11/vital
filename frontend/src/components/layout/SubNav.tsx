import { NavLink } from "react-router-dom";

import { cn } from "../../lib/cn";

export type SubNavItem = { to: string; label: string };

/**
 * The second level of navigation, for sections the bottom bar has no room for.
 *
 * Body composition and progress photos are one subject with two views, and the
 * bar is capped at five destinations — so they share an entry and split here,
 * as real links rather than tabs: each view keeps its own URL.
 */
export function SubNav({ items, label }: { items: SubNavItem[]; label: string }) {
  return (
    <nav aria-label={label} className="border-b border-border">
      <ul className="flex gap-1">
        {items.map((item) => (
          <li key={item.to}>
            <NavLink
              to={item.to}
              end
              className={({ isActive }) =>
                cn(
                  "inline-flex min-h-[var(--touch-target)] items-center whitespace-nowrap px-3",
                  "border-b-2 transition-colors duration-[var(--duration-fast)]",
                  isActive
                    ? "border-primary text-ink"
                    : "border-transparent text-ink-muted hover:text-ink",
                )
              }
            >
              {item.label}
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  );
}
