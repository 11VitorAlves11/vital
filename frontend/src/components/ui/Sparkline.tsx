import { cn } from "../../lib/cn";

type SparklineProps = {
  values: number[];
  /** Read out instead of the drawing — the shape alone is not accessible. */
  summary: string;
  className?: string;
  width?: number;
  height?: number;
};

/**
 * Hand-drawn SVG rather than a chart library: at this size a Recharts instance
 * per dashboard card costs far more than the polyline it would render.
 */
export function Sparkline({
  values,
  summary,
  className,
  width = 120,
  height = 32,
}: SparklineProps) {
  // A single reading is not a trend, and an empty band where a line should be
  // reads as something that failed to load.
  if (values.length < 2) return null;

  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  const step = values.length > 1 ? width / (values.length - 1) : 0;
  const points = values
    .map((value, index) => {
      const x = values.length > 1 ? index * step : width / 2;
      // A flat series sits in the middle instead of collapsing onto the floor.
      const y = height - ((value - min) / span) * (height - 4) - 2;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");

  return (
    <svg
      role="img"
      aria-label={summary}
      viewBox={`0 0 ${width} ${height}`}
      className={cn("h-8 w-full text-primary", className)}
      preserveAspectRatio="none"
    >
      <polyline
        points={points}
        fill="none"
        stroke="currentColor"
        strokeWidth={1.5}
        strokeLinecap="round"
        strokeLinejoin="round"
        vectorEffect="non-scaling-stroke"
      />
    </svg>
  );
}
