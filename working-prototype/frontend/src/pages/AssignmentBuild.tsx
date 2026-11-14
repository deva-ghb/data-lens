import { ArrowLeft, Info } from "lucide-react";
import { Link, useParams } from "react-router-dom";
import { useGet } from "../api/hooks";
import { Page } from "../layout/AppShell";
import { Card } from "../ui/Card";
import { TierChip, type Tier } from "../ui/TierChip";
import { Loaded, pct } from "./common";
import "./pages.css";
import "./build.css";

type Driver = { layer: string; name: string; multiplier: number; contribution: number; source: string; freshness_hours: number | null; reason: string };
type Build = {
  worker: string;
  activity: string;
  grade: number;
  layers: { name: "intrinsic" | "control" | "condition" | "profile"; value: number; drivers: Driver[] }[];
  r: number;
  tier: Tier;
  thresholds: [number, number];
  confidence: number;
  group_step_limited: boolean;
  reason: string;
  late_feeds: string[];
};

const LAYER_TEXT: Record<"intrinsic" | "control" | "condition" | "profile", [string, string]> = {
  intrinsic: ["Intrinsic", "The activity itself: its grade sets the scale and the tier lines."],
  control: ["Control", "How well the controls have held on this work, from 12 months of safety records."],
  condition: ["Condition", "The shift as it will be: heat, night, dust, pace, and the camp the night before."],
  profile: ["Profile", "The person's readiness for this work, in work terms."],
};

const NAMES: Record<string, string> = {
  control_history: "Safety record on this work",
  heat: "Heat",
  night: "Night shift",
  dust: "Dust",
  pace: "Vessel pace",
  camp_recovery: "Camp recovery",
  fatigue: "Fatigue",
  heat_strain: "Heat acclimatisation",
  physical: "Physical restrictions",
  acute: "How they feel today",
  safety_behaviour: "Training path and tenure",
  competency: "Training and competency",
};

function fresh(hours: number | null): string {
  if (hours === null) return "";
  if (hours < 1) return "fresh";
  if (hours < 48) return `${Math.round(hours)} h old`;
  return `${Math.round(hours / 24)} days old`;
}

export function AssignmentBuild() {
  const { assignmentId } = useParams();
  const build = useGet<Build>(`/api/assignments/${assignmentId}/build`);
  return (
    <Loaded query={build}>
      {(b) => {
        let running = 1;
        const max = Math.max(b.r, b.thresholds[1] * 1.1);
        return (
          <Page
            title={b.worker}
            subtitle={`${b.activity}, grade ${b.grade}. How the relative risk is built, layer by layer.`}
            actions={
              <Link to="/roster" className="link row">
                <ArrowLeft size={16} aria-hidden="true" /> Back to the roster
              </Link>
            }
          >
            <div className="grid grid--main-side">
              <Card title="Relative risk" subtitle="Against a crew with no shortfalls on the same work">
                <div className="build">
                  {b.layers.map((layer) => {
                    running *= layer.value;
                    return (
                      <div className="build__row" key={layer.name}>
                        <div className="build__label">
                          <span className="build__name">{LAYER_TEXT[layer.name][0]}</span>
                          <span className="xsmall muted">{LAYER_TEXT[layer.name][1]}</span>
                        </div>
                        <span className="build__times num">× {layer.value.toFixed(2)}</span>
                        <div className="build__track">
                          <span className="build__bar" style={{ width: pct(Math.min(running / max, 1)) }} />
                          <span className="build__line build__line--low" style={{ left: pct(b.thresholds[0] / max) }} />
                          <span className="build__line build__line--high" style={{ left: pct(b.thresholds[1] / max) }} />
                        </div>
                        <span className="build__running num">{running.toFixed(2)}</span>
                      </div>
                    );
                  })}
                  <div className="build__legend xsmall muted">
                    <span><span className="build__key build__key--low" /> Fit with controls from {b.thresholds[0].toFixed(1)}</span>
                    <span><span className="build__key build__key--high" /> Reassign today from {b.thresholds[1].toFixed(1)}</span>
                  </div>
                </div>
              </Card>
              <Card title="Result">
                <div className="stack">
                  <div className="row row--between">
                    <span className="build__r num">R = {b.r.toFixed(2)}</span>
                    <TierChip tier={b.tier} size="lg" />
                  </div>
                  <p className="small">{b.reason}</p>
                  <dl className="kv">
                    <dt>Confidence</dt>
                    <dd>{pct(b.confidence)}</dd>
                    <dt>Group limit</dt>
                    <dd>{b.group_step_limited ? "Applied: the group moved the tier by one step only" : "Not needed"}</dd>
                    <dt>Late feeds</dt>
                    <dd>{b.late_feeds.length ? b.late_feeds.join(", ") : "None"}</dd>
                  </dl>
                  <p className="xsmall muted row">
                    <Info size={14} aria-hidden="true" /> A tier lasts one shift. It is never exported and never used for hiring, pay or discipline.
                  </p>
                </div>
              </Card>
            </div>
            <div className="grid grid--3">
              {b.layers
                .filter((l) => l.drivers.length > 0)
                .map((layer) => (
                  <Card key={layer.name} title={LAYER_TEXT[layer.name][0]} subtitle={`× ${layer.value.toFixed(2)}`}>
                    <ul className="list">
                      {layer.drivers.map((d) => (
                        <li key={d.name} className="stack stack--tight">
                          <div className="row row--between">
                            <span className="small" style={{ fontWeight: 500 }}>{NAMES[d.name] ?? d.name}</span>
                            <span className={d.multiplier > 1.001 ? "num small build__up" : "num small muted"}>× {d.multiplier.toFixed(3)}</span>
                          </div>
                          <span className="small muted">{d.reason}</span>
                          <span className="xsmall muted">
                            {d.source}
                            {fresh(d.freshness_hours) && ` · ${fresh(d.freshness_hours)}`}
                          </span>
                        </li>
                      ))}
                    </ul>
                  </Card>
                ))}
            </div>
          </Page>
        );
      }}
    </Loaded>
  );
}
