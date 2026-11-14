import { useState } from "react";
import { useGet } from "../api/hooks";
import { Page } from "../layout/AppShell";
import { localTime } from "../layout/Meta";
import { Card } from "../ui/Card";
import { Input } from "../ui/Field";
import { Table, type Column } from "../ui/Table";
import { Loaded, titleCase } from "./common";
import "./pages.css";

type Entry = { id: number; at: string; actor: string | null; actor_role: string; action: string; subject_kind: string; subject_ref: string; model_version: string | null; evidence: unknown };

export function Audit() {
  const trail = useGet<{ redacted: boolean; entries: Entry[] }>("/api/audit?limit=400");
  const [q, setQ] = useState("");
  const columns: Column<Entry>[] = [
    { key: "at", header: "When", render: (e) => <span className="num small">{localTime(e.at)}</span>, width: 130 },
    { key: "who", header: "Who", render: (e) => <span className="small">{e.actor ?? titleCase(e.actor_role)}</span>, width: 190 },
    { key: "action", header: "What", render: (e) => <span className="small">{titleCase(e.action)}</span>, width: 220 },
    { key: "subject", header: "On", render: (e) => <span className="small muted">{titleCase(e.subject_kind)} {e.subject_ref}</span> },
    { key: "model", header: "Model", render: (e) => <span className="xsmall muted">{e.model_version ?? ""}</span>, width: 200 },
  ];
  return (
    <Page title="Audit trail" subtitle="Every AI draft, human decision, declined question and threshold change. Nobody can edit it.">
      <Loaded query={trail}>
        {(t) => {
          const rows = t.entries.filter((e) => !q.trim() || `${e.action} ${e.actor ?? ""} ${e.subject_kind}`.toLowerCase().includes(q.trim().toLowerCase()));
          return (
            <Card flush title={t.redacted ? "Redacted for the authority: roles, not names" : `${rows.length} entries`} actions={<Input aria-label="Filter" placeholder="Filter by action or person" value={q} onChange={(e) => setQ(e.target.value)} style={{ width: 260 }} />}>
              <Table caption="Audit trail" columns={columns} rows={rows} rowKey={(e) => String(e.id)} />
            </Card>
          );
        }}
      </Loaded>
    </Page>
  );
}
