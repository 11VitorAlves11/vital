import { Activity, Camera, FlaskConical, Scale, Scan, Stethoscope } from "lucide-react";
import type { LucideIcon } from "lucide-react";

import type { TimelineKind } from "../../lib/api/types";

/**
 * The icon and colour each kind of event carries, per backlog 2.2.
 *
 * Colour is never the only difference: every event also carries its icon and,
 * in the filter, its name. A rail that could only be read in colour would be
 * unreadable to a good share of the people reading their own blood work.
 */
export const KIND_STYLES: Record<TimelineKind, { icon: LucideIcon; dot: string; text: string }> = {
  lab_report: { icon: FlaskConical, dot: "bg-primary", text: "text-primary" },
  body_composition: { icon: Scale, dot: "bg-flag-normal", text: "text-flag-normal" },
  progress_photo: { icon: Camera, dot: "bg-ink-muted", text: "text-ink-muted" },
  appointment: { icon: Stethoscope, dot: "bg-flag-warn", text: "text-flag-warn" },
  imaging: { icon: Scan, dot: "bg-ink-muted", text: "text-ink-muted" },
  intervention: { icon: Activity, dot: "bg-flag-warn", text: "text-flag-warn" },
};

/** The hour is worth showing on a blood draw and noise on a supplement. */
export const KINDS_WITH_A_MEANINGFUL_HOUR: TimelineKind[] = ["lab_report", "body_composition"];
