import { useState } from "react";
import "../ui.css";
import { ChartTooltip, DataTable, defaultFormat, niceTicks, useElementWidth } from "./chartKit";

export type BarDatum = {
  label: string;
  /** null means the value is hidden, for example a group too small to show. */
  value: number | null;
};

export type BarChartProps = {
  label: string;
  data: BarDatum[];
  formatValue?: (value: number) => string;
  /**
   * Columns read left to right; bars read top to bottom and suit long labels or narrow screens.
   * "columns" falls back to bars when the column labels would collide.
   */
  orientation?: "auto" | "columns" | "bars";
  height?: number;
  color?: string;
  hiddenText?: string;
};

const BAR_MAX = 24;
const RADIUS = 4;

/** A rectangle with a 4 px rounded data end and a square base. */
function columnPath(x: number, y: number, w: number, h: number): string {
  const r = Math.min(RADIUS, w / 2, h);
  return `M${x} ${y + h} V${y + r} Q${x} ${y} ${x + r} ${y} H${x + w - r} Q${x + w} ${y} ${x + w} ${y + r} V${y + h} Z`;
}

function barPath(x: number, y: number, w: number, h: number): string {
  const r = Math.min(RADIUS, h / 2, w);
  return `M${x} ${y} H${x + w - r} Q${x + w} ${y} ${x + w} ${y + r} V${y + h - r} Q${x + w} ${y + h} ${x + w - r} ${y + h} H${x} Z`;
}

export function BarChart({
  label,
  data,
  formatValue = defaultFormat,
  orientation = "auto",
  height = 240,
  color = "var(--series-1)",
  hiddenText = "Hidden",
}: BarChartProps) {
  const [boxRef, width] = useElementWidth<HTMLDivElement>();
  const [active, setActive] = useState<number | null>(null);

  const values = data.map((d) => d.value).filter((v): v is number => v !== null);
  const ticks = niceTicks(0, values.length > 0 ? Math.max(...values) : 1, 4);
  const max = ticks[ticks.length - 1] ?? 1;

  const longest = data.reduce((m, d) => Math.max(m, d.label.length), 0);
  const columnBand = width > 0 ? (width - 44) / Math.max(1, data.length) : 0;
  // Column labels must never touch, so even a requested column chart turns into bars when they would.
  const columnsFit = columnBand >= Math.max(56, longest * 7 + 12);
  const useBars = orientation === "bars" || !columnsFit;

  const table = (
    <DataTable
      caption={label}
      headers={["", "Value"]}
      rows={data.map((d) => [d.label, d.value === null ? hiddenText : formatValue(d.value)])}
    />
  );

  if (useBars) {
    const labelW = Math.min(160, Math.max(64, longest * 7 + 8));
    const valueW = 56;
    const rowH = 36;
    const thickness = 16;
    const innerW = Math.max(0, width - labelW - valueW);
    const svgH = data.length * rowH;
    return (
      <div className="dl-chart" ref={boxRef}>
        {width > 0 && (
          <svg width={width} height={svgH} role="img" aria-label={label}>
            {data.map((d, i) => {
              const y = i * rowH;
              const w = d.value === null ? 0 : (d.value / max) * innerW;
              return (
                <g
                  key={d.label}
                  onPointerEnter={() => setActive(i)}
                  onPointerLeave={() => setActive(null)}
                >
                  <rect x={0} y={y} width={width} height={rowH} fill="transparent" />
                  <text x={0} y={y + rowH / 2} dy="0.32em" className="dl-chart__label-text">
                    <title>{d.label}</title>
                    {d.label.length * 7 > labelW - 8
                      ? `${d.label.slice(0, Math.floor((labelW - 16) / 7))}...`
                      : d.label}
                  </text>
                  <line
                    x1={labelW}
                    x2={labelW}
                    y1={y + 6}
                    y2={y + rowH - 6}
                    stroke="var(--chart-axis)"
                    shapeRendering="crispEdges"
                  />
                  {d.value !== null && w > 0 && (
                    <path
                      d={barPath(labelW, y + (rowH - thickness) / 2, w, thickness)}
                      fill={color}
                      opacity={active === null || active === i ? 1 : 0.55}
                    />
                  )}
                  <text
                    x={labelW + w + 8}
                    y={y + rowH / 2}
                    dy="0.32em"
                    className={d.value === null ? undefined : "dl-chart__value"}
                  >
                    {d.value === null ? hiddenText : formatValue(d.value)}
                  </text>
                </g>
              );
            })}
          </svg>
        )}
        {table}
      </div>
    );
  }

  const margin = { top: 20, right: 8, bottom: 28, left: 44 };
  const innerW = Math.max(0, width - margin.left - margin.right);
  const innerH = height - margin.top - margin.bottom;
  const band = innerW / Math.max(1, data.length);
  const thickness = Math.min(BAR_MAX, band * 0.6);
  const yAt = (value: number) => margin.top + (1 - value / max) * innerH;

  return (
    <div className="dl-chart" ref={boxRef}>
      {width > 0 && (
        <svg width={width} height={height} role="img" aria-label={label}>
          {ticks.map((tick) => (
            <g key={tick}>
              <line
                x1={margin.left}
                x2={margin.left + innerW}
                y1={yAt(tick)}
                y2={yAt(tick)}
                stroke={tick === 0 ? "var(--chart-axis)" : "var(--chart-grid)"}
                shapeRendering="crispEdges"
              />
              <text x={margin.left - 8} y={yAt(tick)} dy="0.32em" textAnchor="end">
                {formatValue(tick)}
              </text>
            </g>
          ))}
          {data.map((d, i) => {
            const cx = margin.left + band * i + band / 2;
            const h = d.value === null ? 0 : (d.value / max) * innerH;
            const top = margin.top + innerH - h;
            return (
              <g
                key={d.label}
                onPointerEnter={() => setActive(i)}
                onPointerLeave={() => setActive(null)}
              >
                <rect
                  x={margin.left + band * i}
                  y={margin.top}
                  width={band}
                  height={innerH}
                  fill="transparent"
                />
                {d.value !== null && h > 0 && (
                  <path
                    d={columnPath(cx - thickness / 2, top, thickness, h)}
                    fill={color}
                    opacity={active === null || active === i ? 1 : 0.55}
                  />
                )}
                <text
                  x={cx}
                  y={d.value === null ? margin.top + innerH - 8 : top - 6}
                  textAnchor="middle"
                  className={d.value === null ? undefined : "dl-chart__value"}
                >
                  {d.value === null ? hiddenText : formatValue(d.value)}
                </text>
                <text x={cx} y={height - 8} textAnchor="middle">
                  {d.label}
                </text>
              </g>
            );
          })}
        </svg>
      )}
      {active !== null && width > 0 && data[active] !== undefined && !useBars && (
        <ChartTooltip
          x={margin.left + band * active + band / 2 + thickness / 2}
          y={margin.top}
          boxWidth={width}
          title={data[active]?.label ?? ""}
          rows={[
            {
              name: label,
              value:
                data[active]?.value === null || data[active]?.value === undefined
                  ? hiddenText
                  : formatValue(data[active]?.value ?? 0),
            },
          ]}
        />
      )}
      {table}
    </div>
  );
}
