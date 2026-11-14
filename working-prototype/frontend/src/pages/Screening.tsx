import { useNavigate } from "react-router-dom";
import { useGet } from "../api/hooks";
import { Page } from "../layout/AppShell";
import { Card } from "../ui/Card";
import { EmptyState } from "../ui/EmptyState";
import { Table, type Column } from "../ui/Table";
import { Loaded, titleCase } from "./common";
import "./pages.css";

type Item = { person_id: number; worker: string; job: string; why: string; latest_outcome: string | null };

export function Screening() {
  const list = useGet<Item[]>("/api/health/screening");
  const navigate = useNavigate();
  const columns: Column<Item>[] = [
    { key: "worker", header: "Worker", render: (i) => <span className="stack stack--tight"><strong>{i.worker}</strong><span className="xsmall muted">{i.job}</span></span> },
    { key: "why", header: "Why on the list", render: (i) => <span className={i.why.startsWith("Reported") ? "pill pill--rose" : "pill pill--lilac"}>{i.why}</span> },
    { key: "outcome", header: "Latest outcome", render: (i) => (i.latest_outcome ? titleCase(i.latest_outcome) : <span className="muted">None</span>) },
  ];
  return (
    <Page title="Screening" subtitle="Health detail stays with you. The employer sees only the outcome, and only if the worker chooses to share it.">
      <Loaded query={list}>
        {(rows) => rows.length === 0 ? <Card><EmptyState title="Nobody waiting" /></Card> : (
          <Card flush><Table caption="Screening list" columns={columns} rows={rows} rowKey={(i) => String(i.person_id)} onRowClick={(i) => navigate(`/health/${i.person_id}`)} /></Card>
        )}
      </Loaded>
    </Page>
  );
}
