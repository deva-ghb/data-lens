import "./ui.css";

export type SkeletonProps = {
  width?: number | string;
  height?: number | string;
  /** Draw several text-height bars, the last one shorter. */
  lines?: number;
};

export function Skeleton({ width = "100%", height = 16, lines }: SkeletonProps) {
  if (lines !== undefined && lines > 1) {
    return (
      <span className="dl-skeleton-stack" aria-hidden="true">
        {Array.from({ length: lines }, (_, index) => (
          <span
            key={index}
            className="dl-skeleton"
            style={{ width: index === lines - 1 ? "60%" : width, height }}
          />
        ))}
      </span>
    );
  }
  return <span className="dl-skeleton" aria-hidden="true" style={{ width, height }} />;
}
