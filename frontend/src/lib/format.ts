/** Values arrive as decimal strings so nothing is lost in transit; they are only
 * turned into numbers for display and for plotting. */

export function toNumber(value: string | number | null | undefined): number {
  if (value === null || value === undefined) return Number.NaN;
  return typeof value === "number" ? value : Number.parseFloat(value);
}

export function formatValue(value: string | number | null | undefined, locale: string): string {
  const parsed = toNumber(value);
  if (Number.isNaN(parsed)) return "—";
  return new Intl.NumberFormat(locale, { maximumFractionDigits: 4 }).format(parsed);
}

export function formatDate(iso: string, locale: string): string {
  return new Intl.DateTimeFormat(locale, { dateStyle: "medium" }).format(new Date(iso));
}

export function formatDateTime(iso: string, locale: string): string {
  return new Intl.DateTimeFormat(locale, { dateStyle: "medium", timeStyle: "short" }).format(
    new Date(iso),
  );
}

/** Range as it reads on a lab report: "13–17", "≥ 13", "≤ 17". */
export function formatRange(
  min: string | number | null,
  max: string | number | null,
  locale: string,
): string | null {
  const low = min === null ? null : formatValue(min, locale);
  const high = max === null ? null : formatValue(max, locale);
  if (low && high) return `${low}–${high}`;
  if (low) return `≥ ${low}`;
  if (high) return `≤ ${high}`;
  return null;
}

/** Datetime-local inputs want "YYYY-MM-DDTHH:mm" in local time. */
export function toLocalInputValue(date: Date): string {
  const offset = date.getTimezoneOffset() * 60_000;
  return new Date(date.getTime() - offset).toISOString().slice(0, 16);
}

export function todayInputValue(): string {
  return toLocalInputValue(new Date()).slice(0, 10);
}
