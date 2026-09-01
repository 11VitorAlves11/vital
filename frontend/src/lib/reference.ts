import type { BodyMetric } from "./api/types";

/** Whether this metric's bands produce a verdict, or only put a name to a value.
 *
 * A band set with no flags is a real scale that declines to judge — the ACE
 * body-fat categories are fitness classes, and a bioimpedance estimate read
 * against them is context, not a finding. */
export function classifies(metric: BodyMetric): boolean {
  return metric.bands?.some((band) => band.flag !== null) ?? false;
}

/** What the reader is told about the reference: the standard when one judges,
 *  and otherwise the reason none does — which differs for every metric and is
 *  the more useful of the two sentences. Null when the catalogue says neither. */
export function referenceLabel(metric: BodyMetric): string | null {
  return classifies(metric) ? metric.source : metric.trend_reason;
}
