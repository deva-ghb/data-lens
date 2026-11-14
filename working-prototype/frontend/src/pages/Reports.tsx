import { Camera } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useGet } from "../api/hooks";
import { Page } from "../layout/AppShell";
import { localTime } from "../layout/Meta";
import { Card } from "../ui/Card";
import { Select } from "../ui/Select";
import { Table, type Column } from "../ui/Table";
import { Loaded } from "./common";
import "./pages.css";

type Report = { kind: string; id: number; at: string; zone: string; text: string; status: string; potential: number | null; has_photo: boolean };
const KIND: Record<string, string> = { near_miss: "Near miss", incident: "Incident", hazard: "Hazard report" };

export function Reports() {
  const reports = useGet<Report[]>("/api/incidents");
  const navigate = useNavigate();
  const [kind, setKind] = useState("all");
  const [status, setStatus] = useState("all");
  const columns: Column<Report>[] = [
    { key: "at", header: "Reported", render: (r) => <span className="num">{localTime(r.at)}</span>, width: 140 },
    { key: "kind", header: "Type", render: (r) => <span className={r.kind === "incident" ? "pill pill--rose" : r.kind === "near_miss" ? "pill pill--sand" : "pill"}>{KIND[r.kind]}</span>, width: 130 },
    { key: "zone", header: "Place", render: (r) => r.zone, width: 140 },
    { key: "text", header: "What happened", render: (r) => <span className="row" style={{ flexWrap: "nowrap" }}>{r.has_photo && <Camera size={14} aria-label="Has a photo" />}<span className="small">{r.text}</span></span> },
    { key: "status", header: "Record", render: (r) => <span className={r.status === "closed" ? "pill pill--mint" : "pill pill--periwinkle"}>{r.status === "closed" ? "Confirmed" : "Waiting for review"}</span>, width: 170 },
  ];
  return (
    <Page title="Incidents and hazards" subtitle="Reported from a phone in under a minute. The copilot drafts the record; you confirm it. Every report is also a signal.">
      <Loaded query={reports}>
        {(rows) => {
          const shown = rows.filter((r) => (kind === "all" || r.kind === kind) && (status === "all" || (status === "open" ? r.status !== "closed" : r.status === "closed")));
          return (
            <Card
              flush
              title={`${shown.length} reports`}
              actions={
                <div className="row">
                  <Select aria-label="Type" value={kind} onValueChange={setKind} options={[{ value: "all", label: "All types" }, ...Object.entries(KIND).map(([v, l]) => ({ value: v, label: l }))]} />
                  <Select aria-label="Record status" value={status} onValueChange={setStatus} options={[{ value: "all", label: "Any status" }, { value: "open", label: "Waiting for review" }, { value: "closed", label: "Confirmed" }]} />
                </div>
              }
            >
              <Table caption="Reports" columns={columns} rows={shown} rowKey={(r) => `${r.kind}-${r.id}`} onRowClick={(r) => navigate(`/reports/${r.kind}/${r.id}`)} />
            </Card>
          );
        }}
      </Loaded>
    </Page>
  );
}

