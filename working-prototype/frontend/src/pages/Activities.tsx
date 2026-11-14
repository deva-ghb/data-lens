import { useNavigate } from "react-router-dom";
import { useGet } from "../api/hooks";
import { Page } from "../layout/AppShell";
import { Card } from "../ui/Card";
import { Table, type Column } from "../ui/Table";
import { Loaded } from "./common";
import "./pages.css";

type Activity = { id: number; code: string; name: string; grade: number; exposure_hours_week: number; severity: number; hazards: string[]; swp_items: number; uabc_total_12m: number; control: number };
const HAZARD: Record<string, string> = { FALL_HEIGHT: "Fall from height", STRUCK_PLANT: "Mobile plant", DROPPED_LOAD: "Dropped load", HEAT_ILLNESS: "Heat illness", MANUAL_HANDLING: "Manual handling", HOT_WORK_CONFINED: "Hot work, confined space" };
const GRADE_TINT = ["", "mint", "mint", "sky", "sand", "rose"];

export function Activities() {
  const list = useGet<Activity[]>("/api/activities");
  const navigate = useNavigate();
  const columns: Column<Activity>[] = [
    { key: "name", header: "Activity", render: (a) => <strong>{a.name}</strong> },
    { key: "grade", header: "Grade", render: (a) => <span className={`pill pill--${GRADE_TINT[a.grade]}`}>Grade {a.grade}</span>, width: 110 },
    { key: "hazards", header: "Hazards", render: (a) => <span className="small muted">{a.hazards.map((h) => HAZARD[h] ?? h).join(", ")}</span> },
    { key: "hours", header: "Hours a week", numeric: true, render: (a) => a.exposure_hours_week.toLocaleString(), width: 120 },
    { key: "uabc", header: "Unsafe events, 12 months", numeric: true, render: (a) => a.uabc_total_12m, width: 170 },
    { key: "control", header: "Control layer", numeric: true, render: (a) => <span className={a.control > 1.05 ? "num build__up" : "num"}>× {a.control.toFixed(2)}</span>, width: 130 },
  ];
  return (
    <Page title="Activities" subtitle="The port's activity register: intrinsic risk, safe working practice and how well the controls have held.">
      <Loaded query={list}>
        {(rows) => (
          <Card flush>
            <Table caption="Activities" columns={columns} rows={rows} rowKey={(a) => String(a.id)} onRowClick={(a) => navigate(`/activities/${a.id}`)} />
          </Card>
        )}
      </Loaded>
    </Page>
  );
}
