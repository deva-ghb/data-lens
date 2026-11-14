import { useLayoutEffect, useRef, useState, type ReactNode, type RefObject } from "react";

/** Series colours in their validated, fixed order. Never cycled: callers cap at six. */
export const SERIES_COLORS = [
  "var(--series-1)",
  "var(--series-2)",
  "var(--series-3)",
  "var(--series-4)",
  "var(--series-5)",
  "var(--series-6)",
];

export const SEQUENTIAL = [
  "var(--seq-1)",
  "var(--seq-2)",
  "var(--seq-3)",
  "var(--seq-4)",
  "var(--seq-5)",
  "var(--seq-6)",
];

/** Steps 5 and 6 are dark enough to need white text; lighter steps take near-black. */
export const SEQUENTIAL_INK = [
  "var(--color-text)",
  "var(--color-text)",
  "var(--color-text)",
  "var(--color-text)",
  "#ffffff",
  "#ffffff",
];

export function defaultFormat(value: number): string {
  return value.toLocaleString("en-GB", { maximumFractionDigits: 1 });
}

function niceStep(rough: number): number {
  const power = Math.pow(10, Math.floor(Math.log10(rough)));
  const fraction = rough / power;
  const nice = fraction <= 1 ? 1 : fraction <= 2 ? 2 : fraction <= 2.5 ? 2.5 : fraction <= 5 ? 5 : 10;
  return nice * power;
}

/** Round tick values that cover [min, max]. */
export function niceTicks(min: number, max: number, count = 4): number[] {
  if (max === min) {
    max = min + 1;
  }
  const step = niceStep((max - min) / count);
  const start = Math.floor(min / step) * step;
  const end = Math.ceil(max / step) * step;
  const ticks: number[] = [];
  for (let value = start; value <= end + step / 2; value += step) {
    ticks.push(Number(value.toFixed(10)));
  }
  return ticks;
}

/** Width of an element, kept current as it resizes. */
export function useElementWidth<T extends HTMLElement>(): [RefObject<T>, number] {
  const ref = useRef<T>(null);
  const [width, setWidth] = useState(0);
  useLayoutEffect(() => {
    const element = ref.current;
    if (element === null) return undefined;
    setWidth(element.getBoundingClientRect().width || 600);
    if (typeof ResizeObserver === "undefined") return undefined;
    const observer = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (entry !== undefined) setWidth(entry.contentRect.width);
    });
    observer.observe(element);
    return () => observer.disconnect();
  }, []);
  return [ref, width];
}

export function Legend({ items, shape }: { items: Array<{ label: string; color: string }>; shape: "line" | "rect" }) {
  return (
    <ul className="dl-chart__legend">
      {items.map((item) => (
        <li key={item.label}>
          <span
            className={shape === "line" ? "dl-chart__key-line" : "dl-chart__key-rect"}
            style={{ background: item.color }}
            aria-hidden="true"
          />
          {item.label}
        </li>
      ))}
    </ul>
  );
}

export type TooltipRow = { name: string; value: string; color?: string };

/** Positioned inside the chart box; flips to the left of the anchor near the right edge. */
export function ChartTooltip({
  x,
  y,
  boxWidth,
  title,
  rows,
}: {
  x: number;
  y: number;
  boxWidth: number;
  title: string;
  rows: TooltipRow[];
}) {
  const flip = x > boxWidth - 180;
  const style = flip
    ? { right: Math.max(0, boxWidth - x + 12), top: y }
    : { left: x + 12, top: y };
  return (
    <div className="dl-chart__tooltip" style={style} role="presentation">
      <div className="dl-chart__tooltip-title">{title}</div>
      {rows.map((row) => (
        <div className="dl-chart__tooltip-row" key={row.name}>
          {row.color !== undefined && (
            <span className="dl-chart__key-line" style={{ background: row.color }} aria-hidden="true" />
          )}
          <span className="dl-chart__tooltip-value">{row.value}</span>
          <span className="dl-chart__tooltip-name">{row.name}</span>
        </div>
      ))}
    </div>
  );
}

/** Screen-reader table carrying every value the chart draws. */
export function DataTable({
  caption,
  headers,
  rows,
}: {
  caption: string;
  headers: string[];
  rows: ReactNode[][];
}) {
  return (
    <table className="visually-hidden">
      <caption>{caption}</caption>
      <thead>
        <tr>
          {headers.map((header) => (
            <th key={header} scope="col">
              {header}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((row, rowIndex) => (
          <tr key={rowIndex}>
            {row.map((cell, cellIndex) => (
              <td key={cellIndex}>{cell}</td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}
