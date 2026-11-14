import { ArrowDownRight, ArrowRight, ArrowUpRight } from "lucide-react";
import { cx } from "./cx";
import { Sparkline } from "./charts/Sparkline";
import "./ui.css";

export type StatDelta = {
  /** Already formatted, signed, for example "+3" or "-1.2". */
  text: string;
  direction: "up" | "down" | "flat";
  /** Whether this direction is good news for this figure. */
  good: boolean;
  /** The period compared against, for example "vs last week". */
  period: string;
};

export type StatProps = {
  label: string;
  value: string;
  unit?: string;
  delta?: StatDelta;
  trend?: number[];
};

const DELTA_ICON = { up: ArrowUpRight, down: ArrowDownRight, flat: ArrowRight };

export function Stat({ label, value, unit, delta, trend }: StatProps) {
  const DeltaIcon = delta === undefined ? null : DELTA_ICON[delta.direction];
  return (
    <div className="dl-stat">
      <span className="dl-stat__label">{label}</span>
      <div className="dl-stat__row">
        <span className="dl-stat__value">
          {value}
          {unit !== undefined && <span className="dl-stat__unit">{unit}</span>}
        </span>
        {trend !== undefined && trend.length > 1 && (
          <Sparkline values={trend} label={`${label} trend`} />
        )}
      </div>
      {delta !== undefined && DeltaIcon !== null && (
        <span
          className={cx(
            "dl-stat__delta",
            delta.direction !== "flat" && (delta.good ? "dl-stat__delta--good" : "dl-stat__delta--bad"),
          )}
        >
          <DeltaIcon aria-hidden="true" />
          <span className="num">{delta.text}</span>
          <span className="dl-stat__delta-period">{delta.period}</span>
        </span>
      )}
    </div>
  );
}
