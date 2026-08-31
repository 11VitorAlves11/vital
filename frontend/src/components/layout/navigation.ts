import { CalendarClock, FlaskConical, House, Scale, User } from "lucide-react";
import type { LucideIcon } from "lucide-react";

export type NavItem = { to: string; labelKey: string; icon: LucideIcon };

/**
 * Five is the ceiling for a bottom bar; anything more would have to fold away.
 *
 * Interventions gave up its slot to the timeline, which is the view everything
 * else appears in, and reaches its own page from there — the two are one
 * subject, things that happened over a period.
 */
export const NAV_ITEMS: NavItem[] = [
  { to: "/", labelKey: "nav.dashboard", icon: House },
  { to: "/timeline", labelKey: "nav.timeline", icon: CalendarClock },
  { to: "/reports", labelKey: "nav.reports", icon: FlaskConical },
  { to: "/body", labelKey: "nav.body", icon: Scale },
  { to: "/profile", labelKey: "nav.profile", icon: User },
];
