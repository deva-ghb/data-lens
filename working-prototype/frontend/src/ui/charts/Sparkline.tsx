import { useId } from "react";

export type SparklineProps = {
  values: number[];
  label: string;
  width?: number;
  height?: number;
};

/** A small trend line in a quiet grey with the latest point in the accent. */
export function Sparkline({ values, label, width = 96, height = 32 }: SparklineProps) {
  const gradientId = useId();
  if (values.length < 2) return null;
  const pad = 6;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  const step = (width - pad * 2) / (values.length - 1);
  const points = values.map((value, index) => ({
    x: pad + index * step,
    y: pad + (1 - (value - min) / span) * (height - pad * 2),
  }));
  const line = points.map((p, i) => `${i === 0 ? "M" : "L"}${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(" ");
  const first = points[0];
  const last = points[points.length - 1];
  if (first === undefined || last === undefined) return null;
  const area = `${line} L${last.x.toFixed(1)} ${height} L${first.x.toFixed(1)} ${height} Z`;
  return (
    <svg
      className="dl-sparkline"
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      role="img"
      aria-label={`${label}: from ${values[0]} to ${values[values.length - 1]}`}
    >
      <defs>
        <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="var(--series-1)" stopOpacity="0.14" />
          <stop offset="100%" stopColor="var(--series-1)" stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={area} fill={`url(#${gradientId})`} />
      <path
        d={line}
        fill="none"
        stroke="var(--seq-3)"
        strokeWidth={1.5}
        strokeLinejoin="round"
        strokeLinecap="round"
      />
      <circle cx={last.x} cy={last.y} r={4} fill="var(--color-page)" />
      <circle cx={last.x} cy={last.y} r={2.75} fill="var(--color-accent)" />
    </svg>
  );
}
