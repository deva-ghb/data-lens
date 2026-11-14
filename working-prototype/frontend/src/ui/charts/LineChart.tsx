import { useId, useState, type KeyboardEvent, type PointerEvent } from "react";
import "../ui.css";
import {
  ChartTooltip,
  DataTable,
  Legend,
  SERIES_COLORS,
  defaultFormat,
  niceTicks,
  useElementWidth,
} from "./chartKit";

export type LineSeries = { id: string; label: string; values: Array<number | null> };

export type LineChartProps = {
  /** Text alternative naming what is plotted. */
  label: string;
  /** X positions in order, for example dates or shift names. */
  categories: string[];
  series: LineSeries[];
  height?: number;
  formatValue?: (value: number) => string;
  /** Start the value axis at zero (default) or fit it to the data. */
  zeroBased?: boolean;
  /** A horizontal reference, for example a threshold. */
  reference?: { value: number; label: string };
};

const MARGIN = { top: 12, right: 24, bottom: 28, left: 44 };

/** Every nth x label at a steady rhythm, so the gaps between labels stay even. */
function labelIndices(count: number, every: number): number[] {
  const picked: number[] = [];
  for (let index = 0; index < count; index += every) picked.push(index);
  return picked;
}

export function LineChart({
  label,
  categories,
  series,
  height = 240,
  formatValue = defaultFormat,
  zeroBased = true,
  reference,
}: LineChartProps) {
  const [boxRef, width] = useElementWidth<HTMLDivElement>();
  const [active, setActive] = useState<number | null>(null);
  const areaId = useId();
  const shown = series.slice(0, SERIES_COLORS.length);

  const all = shown.flatMap((s) => s.values.filter((v): v is number => v !== null));
  if (reference !== undefined) all.push(reference.value);
  const dataMin = all.length > 0 ? Math.min(...all) : 0;
  const dataMax = all.length > 0 ? Math.max(...all) : 1;
  const ticks = niceTicks(zeroBased ? Math.min(0, dataMin) : dataMin, dataMax, 4);
  const yMin = ticks[0] ?? 0;
  const yMax = ticks[ticks.length - 1] ?? 1;

  const innerW = Math.max(0, width - MARGIN.left - MARGIN.right);
  const innerH = height - MARGIN.top - MARGIN.bottom;
  const count = categories.length;
  const xAt = (index: number) =>
    MARGIN.left + (count <= 1 ? innerW / 2 : (index / (count - 1)) * innerW);
  const yAt = (value: number) => MARGIN.top + (1 - (value - yMin) / (yMax - yMin)) * innerH;

  const maxLabels = Math.max(2, Math.floor(innerW / 64));
  const labelEvery = Math.max(1, Math.ceil(count / maxLabels));

  const pathFor = (values: Array<number | null>) => {
    let d = "";
    let pen = false;
    values.forEach((value, index) => {
      if (value === null) {
        pen = false;
        return;
      }
      d += `${pen ? "L" : "M"}${xAt(index).toFixed(1)} ${yAt(value).toFixed(1)} `;
      pen = true;
    });
    return d.trim();
  };

  const nearest = (clientX: number, rect: DOMRect) => {
    const x = clientX - rect.left - MARGIN.left;
    if (count <= 1) return 0;
    return Math.min(count - 1, Math.max(0, Math.round((x / innerW) * (count - 1))));
  };

  const onMove = (event: PointerEvent<SVGRectElement>) => {
    const svg = event.currentTarget.ownerSVGElement;
    if (svg === null) return;
    setActive(nearest(event.clientX, svg.getBoundingClientRect()));
  };

  const onKey = (event: KeyboardEvent<SVGSVGElement>) => {
    if (event.key === "ArrowRight" || event.key === "ArrowLeft") {
      event.preventDefault();
      const delta = event.key === "ArrowRight" ? 1 : -1;
      setActive((current) => Math.min(count - 1, Math.max(0, (current ?? (delta > 0 ? -1 : count)) + delta)));
    }
    if (event.key === "Escape") setActive(null);
  };

  const single = shown.length === 1;
  const lastIndex = (values: Array<number | null>) => {
    for (let i = values.length - 1; i >= 0; i -= 1) if (values[i] !== null) return i;
    return -1;
  };

  return (
    <div className="dl-chart" ref={boxRef}>
      {!single && (
        <Legend
          shape="line"
          items={shown.map((s, i) => ({ label: s.label, color: SERIES_COLORS[i] ?? "" }))}
        />
      )}
      {width > 0 && (
        <svg
          width={width}
          height={height}
          role="img"
          aria-label={label}
          tabIndex={0}
          onKeyDown={onKey}
          onBlur={() => setActive(null)}
        >
          {ticks.map((tick) => (
            <g key={tick}>
              <line
                x1={MARGIN.left}
                x2={MARGIN.left + innerW}
                y1={yAt(tick)}
                y2={yAt(tick)}
                stroke={tick === yMin ? "var(--chart-axis)" : "var(--chart-grid)"}
                strokeWidth={1}
                shapeRendering="crispEdges"
              />
              <text x={MARGIN.left - 8} y={yAt(tick)} dy="0.32em" textAnchor="end">
                {formatValue(tick)}
              </text>
            </g>
          ))}
          {labelIndices(count, labelEvery).map((index) => (
            <text
              key={index}
              x={xAt(index)}
              y={height - 8}
              textAnchor="middle"
            >
              {categories[index]}
            </text>
          ))}
          {reference !== undefined && (
            <g>
              <line
                x1={MARGIN.left}
                x2={MARGIN.left + innerW}
                y1={yAt(reference.value)}
                y2={yAt(reference.value)}
                stroke="var(--status-warning-dot)"
                strokeWidth={1}
                strokeDasharray="4 4"
                shapeRendering="crispEdges"
              />
              <text
                x={MARGIN.left + 4}
                y={yAt(reference.value) - 6}
                textAnchor="start"
                className="dl-chart__value"
              >
                {reference.label}
              </text>
            </g>
          )}
          {single && shown[0] !== undefined && (
            <>
              <defs>
                <linearGradient id={areaId} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="var(--series-1)" stopOpacity="0.12" />
                  <stop offset="100%" stopColor="var(--series-1)" stopOpacity="0.02" />
                </linearGradient>
              </defs>
              {(() => {
                const values = shown[0].values;
                const first = values.findIndex((v) => v !== null);
                const last = lastIndex(values);
                if (first < 0 || values.slice(first, last + 1).some((v) => v === null)) return null;
                const d = `${pathFor(values)} L${xAt(last).toFixed(1)} ${yAt(yMin).toFixed(1)} L${xAt(first).toFixed(1)} ${yAt(yMin).toFixed(1)} Z`;
                return <path d={d} fill={`url(#${areaId})`} />;
              })()}
            </>
          )}
          {shown.map((s, i) => (
            <path
              key={s.id}
              d={pathFor(s.values)}
              fill="none"
              stroke={SERIES_COLORS[i]}
              strokeWidth={2}
              strokeLinejoin="round"
              strokeLinecap="round"
            />
          ))}
          {active === null &&
            shown.map((s, i) => {
              const last = lastIndex(s.values);
              const value = s.values[last];
              if (last < 0 || value === null || value === undefined) return null;
              return (
                <g key={`end-${s.id}`}>
                  <circle cx={xAt(last)} cy={yAt(value)} r={6} fill="var(--color-page)" />
                  <circle cx={xAt(last)} cy={yAt(value)} r={4} fill={SERIES_COLORS[i]} />
                </g>
              );
            })}
          {active !== null && (
            <g>
              <line
                x1={xAt(active)}
                x2={xAt(active)}
                y1={MARGIN.top}
                y2={MARGIN.top + innerH}
                stroke="var(--color-border-strong)"
                strokeWidth={1}
                shapeRendering="crispEdges"
              />
              {shown.map((s, i) => {
                const value = s.values[active];
                if (value === null || value === undefined) return null;
                return (
                  <g key={`dot-${s.id}`}>
                    <circle cx={xAt(active)} cy={yAt(value)} r={6} fill="var(--color-page)" />
                    <circle cx={xAt(active)} cy={yAt(value)} r={4} fill={SERIES_COLORS[i]} />
                  </g>
                );
              })}
            </g>
          )}
          <rect
            x={MARGIN.left - 8}
            y={MARGIN.top}
            width={innerW + 16}
            height={innerH}
            fill="transparent"
            onPointerMove={onMove}
            onPointerLeave={() => setActive(null)}
          />
        </svg>
      )}
      {active !== null && width > 0 && (
        <ChartTooltip
          x={xAt(active)}
          y={MARGIN.top + (single ? 0 : 32)}
          boxWidth={width}
          title={categories[active] ?? ""}
          rows={shown.map((s, i) => {
            const value = s.values[active];
            return {
              name: s.label,
              value: value === null || value === undefined ? "No data" : formatValue(value),
              color: SERIES_COLORS[i],
            };
          })}
        />
      )}
      <DataTable
        caption={label}
        headers={["", ...shown.map((s) => s.label)]}
        rows={categories.map((category, index) => [
          category,
          ...shown.map((s) => {
            const value = s.values[index];
            return value === null || value === undefined ? "No data" : formatValue(value);
          }),
        ])}
      />
    </div>
  );
}
