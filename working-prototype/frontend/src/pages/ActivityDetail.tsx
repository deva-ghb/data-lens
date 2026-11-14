import { ArrowLeft } from "lucide-react";
import { Link, useParams } from "react-router-dom";
import { useGet } from "../api/hooks";
import { Page } from "../layout/AppShell";
import { Card } from "../ui/Card";
import { Stat } from "../ui/Stat";
import { BarChart } from "../ui/charts/BarChart";
import { Loaded } from "./common";
import "./pages.css";
import "./build.css";

type Detail = {
  id: number; code: string; name: string; grade: number; severity: number; exposure_hours_week: number; thresholds: [number, number] | null;
  hazards: { code: string; name: string }[]; swp: { seq: number; text: string }[];
  uabc_12m: Record<string, number>; uabc_by_month: { month: string; day: number; night: number }[];
  control: number; control_reason: string; sensitivity: Record<string, "H" | "M" | "L">; lower_hazard_alternative: string | null;
};

const DIM: Record<string, string> = { fatigue: "Fatigue", heat_strain: "Heat", physical: "Physical", acute: "How they feel", safety_behaviour: "Safety behaviour", competency: "Competency" };
const LEVEL: Record<string, [string, string]> = { H: ["High", "rose"], M: ["Medium", "sand"], L: ["Low", "mint"] };

export function ActivityDetail() {
  const { activityId } = useParams();
  const detail = useGet<Detail>(`/api/activities/${activityId}`);
  return (
    <Loaded query={detail}>
      {(a) => (
        <Page
          title={a.name}
          subtitle={`Grade ${a.grade} · ${a.exposure_hours_week.toLocaleString()} worker-hours a week · ${a.hazards.map((h) => h.name.toLowerCase()).join(", ")}`}
          actions={<Link to="/activities" className="link row"><ArrowLeft size={16} aria-hidden="true" /> All activities</Link>}
        >
          <div className="grid grid--4">
            <Stat label="Unsafe acts" value={String(a.uabc_12m.unsafe_act)} />
            <Stat label="Unsafe behaviours" value={String(a.uabc_12m.unsafe_behaviour)} />
            <Stat label="Unsafe conditions" value={String(a.uabc_12m.unsafe_condition)} />
            <Stat label="Near misses" value={String(a.uabc_12m.near_miss)} />
          </div>
          <div className="grid grid--main-side">
            <Card title="Unsafe events by month" subtitle="Last 12 months, night shifts">
              <BarChart label="Unsafe events on night shifts by month" data={a.uabc_by_month.map((m) => ({ label: m.month.slice(5), value: m.night }))} orientation="columns" height={200} />
            </Card>
            <Card title="Control layer">
              <div className="stack">
                <span className="build__r num">× {a.control.toFixed(2)}</span>
                <p className="small muted">{a.control_reason}</p>
                {a.thresholds && <p className="small">Fit with controls from {a.thresholds[0]}, reassign today from {a.thresholds[1]}.</p>}
                {a.lower_hazard_alternative && <p className="small">Lower-hazard work in the same competency: <strong>{a.lower_hazard_alternative}</strong></p>}
              </div>
            </Card>
          </div>
          <div className="grid grid--2">
            <Card title="Sensitivity" subtitle="How much a shortfall in each area raises this work's hazards">
              <ul className="list">
                {Object.entries(a.sensitivity).map(([d, l]) => (
                  <li key={d} className="row row--between">
                    <span className="small">{DIM[d] ?? d}</span>
                    <span className={`pill pill--${(LEVEL[l] ?? ["", ""])[1]}`}>{(LEVEL[l] ?? ["", ""])[0]}</span>
                  </li>
                ))}
              </ul>
            </Card>
            <Card title="Safe working practice" subtitle={`${a.swp.length} items`}>
              <ol className="list">
                {a.swp.map((s) => (
                  <li key={s.seq} className="small row" style={{ flexWrap: "nowrap", alignItems: "flex-start" }}>
                    <span className="num muted" style={{ width: 24, flex: "none" }}>{s.seq}.</span>
                    <span>{s.text}</span>
                  </li>
                ))}
              </ol>
            </Card>
          </div>
        </Page>
      )}
    </Loaded>
  );
}
