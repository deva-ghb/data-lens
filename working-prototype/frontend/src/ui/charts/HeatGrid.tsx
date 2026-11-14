import { EyeOff } from "lucide-react";
import "../ui.css";
import { SEQUENTIAL, SEQUENTIAL_INK, defaultFormat } from "./chartKit";

export type HeatGridProps = {
  label: string;
  rows: string[];
  columns: string[];
  /** values[row][column]; null means hidden (too few people to show). */
  values: Array<Array<number | null>>;
  formatValue?: (value: number) => string;
  /** Fix the colour scale, for example [0, 1] for rates. Defaults to the data range. */
  domain?: [number, number];
  hiddenText?: string;
  /** Short note under the scale, for example what a hidden cell means. */
  note?: string;
};

function stepFor(value: number, min: number, max: number): number {
  if (max <= min) return 0;
  const t = (value - min) / (max - min);
  return Math.min(SEQUENTIAL.length - 1, Math.max(0, Math.floor(t * SEQUENTIAL.length)));
}

/** A grid of soft blocks, one per row and column, shaded light to dark by value. */
export function HeatGrid({
  label,
  rows,
  columns,
  values,
  formatValue = defaultFormat,
  domain,
  hiddenText = "Hidden",
  note,
}: HeatGridProps) {
  const flat = values.flat().filter((v): v is number => v !== null);
  const min = domain?.[0] ?? (flat.length > 0 ? Math.min(...flat) : 0);
  const max = domain?.[1] ?? (flat.length > 0 ? Math.max(...flat) : 1);

  return (
    <div className="dl-chart dl-heat">
      <div
        className="dl-heat__grid"
        role="table"
        aria-label={label}
        style={{ gridTemplateColumns: `auto repeat(${columns.length}, minmax(var(--heat-cell-min, 64px), 1fr))` }}
      >
        <div role="row" style={{ display: "contents" }}>
          <span role="columnheader" />
          {columns.map((column) => (
            <span key={column} role="columnheader" className="dl-heat__colhead">
              {column}
            </span>
          ))}
        </div>
        {rows.map((row, r) => (
          <div key={row} role="row" style={{ display: "contents" }}>
            <span role="rowheader" className="dl-heat__rowhead">
              {row}
            </span>
            {columns.map((column, c) => {
              const value = values[r]?.[c] ?? null;
              const key = `${r}-${c}`;
              const text = value === null ? hiddenText : formatValue(value);
              if (value === null) {
                return (
                  <span
                    key={key}
                    role="cell"
                    tabIndex={0}
                    className="dl-heat__cell dl-heat__cell--hidden"
                    title={`${row}, ${column}: hidden`}
                  >
                    <EyeOff className="dl-heat__hidden-icon" aria-hidden="true" />
                    <span className="dl-heat__hidden-word">{hiddenText}</span>
                  </span>
                );
              }
              const step = stepFor(value, min, max);
              return (
                <span
                  key={key}
                  role="cell"
                  tabIndex={0}
                  className="dl-heat__cell"
                  title={`${row}, ${column}: ${text}`}
                  style={{
                    background: SEQUENTIAL[step],
                    color: SEQUENTIAL_INK[step],
                    borderColor: step === 0 ? "var(--tint-periwinkle-border)" : "transparent",
                  }}
                >
                  {text}
                </span>
              );
            })}
          </div>
        ))}
      </div>
      <div className="dl-heat__scale" aria-hidden="true">
        <span>{formatValue(min)}</span>
        <span className="dl-heat__ramp">
          {SEQUENTIAL.map((color) => (
            <span key={color} style={{ background: color }} />
          ))}
        </span>
        <span>{formatValue(max)}</span>
        {note !== undefined && <span className="dl-heat__note">{note}</span>}
      </div>
    </div>
  );
}
