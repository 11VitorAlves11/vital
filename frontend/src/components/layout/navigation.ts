import { Activity, House, Scale, User, FlaskConical } from "lucide-react";
import type { LucideIcon } from "lucide-react";

export type NavItem = { to: string; labelKey: string; icon: LucideIcon };

/** Five is the ceiling for a bottom bar; anything more would have to fold away. */
export const NAV_ITEMS: NavItem[] = [
  { to: "/", labelKey: "nav.dashboard", icon: House },
  { to: "/reports", labelKey: "nav.reports", icon: FlaskConical },
  { to: "/body", labelKey: "nav.body", icon: Scale },
  { to: "/interventions", labelKey: "nav.interventions", icon: Activity },
  { to: "/profile", labelKey: "nav.profile", icon: User },
];
