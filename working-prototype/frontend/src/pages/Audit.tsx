import { useState } from "react";
import { useGet } from "../api/hooks";
import { Page } from "../layout/AppShell";
import { localTime } from "../layout/Meta";
import { Card } from "../ui/Card";
import { Input } from "../ui/Field";
import { Table, type Column } from "../ui/Table";
import { ROLE_LABEL, type Role } from "../auth/useMe";
import { Loaded, titleCase } from "./common";
import "./pages.css";

type Entry = { id: number; at: string; actor: string | null; actor_role: string; action: string; subject_kind: string; subject_ref: string; model_version: string | null; evidence: unknown };

const ACTION_LABEL: Record<string, string> = {
  ai_draft: "AI draft written",
  warning_opened: "Warning opened",
  warning_step_confirmed: "Warning step confirmed",
  warning_closed: "Warning closed",
  action_created: "Action created",
  action_updated: "Action updated",
  report_confirmed: "Report confirmed",
  learning_shared: "Learning shared",
  score_run: "Roster scored",
  question_asked: "Question asked",
  question_declined: "Question declined",
  checked_in: "Checked in",
  tier_contested: "Tier contested",
  reported_unwell: "Reported unwell",
  outcome_consent_changed: "Sharing choice changed",
  health_record_viewed: "Health record opened",
  person_onboarded: "Person onboarded",
  autonomy_changed: "Autonomy changed",
  weights_approved: "Risk weights approved",
  site_clock_set: "Site clock moved",
};

function who(e: Entry): string {
  if (e.actor) return e.actor;
  if (e.actor_role) return ROLE_LABEL[e.actor_role as Role] ?? titleCase(e.actor_role);
  return "System";
}

function what(e: Entry): string {
  const label = ACTION_LABEL[e.action] ?? titleCase(e.action);
  const ev = e.evidence as { step?: number; outcome?: string; status?: string } | null;
  if (e.action === "warning_step_confirmed" && ev?.step) return `${label}: step ${ev.step}`;
  if (e.action === "warning_closed" && ev?.outcome) return `${label}: ${titleCase(ev.outcome).toLowerCase()}`;
  if (e.action === "action_updated" && ev?.status) return `${label}: ${ev.status}`;
  return label;
}

/** "brief-20260728" reads "Brief for 28 Jul"; tokens stay tokens, so no worker is named. */
function subject(e: Entry): string {
  const kind = e.subject_kind;
  if (kind.startsWith("brief-")) {
    const d = kind.slice(6);
    const day = new Date(`${d.slice(0, 4)}-${d.slice(4, 6)}-${d.slice(6, 8)}T12:00:00Z`);
    return `Brief for ${day.toLocaleDateString("en-GB", { day: "numeric", month: "short", timeZone: "UTC" })}`;
  }
  if (e.subject_ref.startsWith("st-") || e.subject_ref.startsWith("pt-")) return `${titleCase(kind)}, token ${e.subject_ref.slice(0, 9)}`;
  if (e.subject_ref === "-") return titleCase(kind);
  return `${titleCase(kind)} ${e.subject_ref}`;
}

function model(version: string | null): string {
  if (!version) return "";
  const [name = version] = version.split(" prompt ");
  if (name === "authored-seed") return "Authored for the scenario";
  const v = version.split(" v").pop();
  return v ? `${name}, prompt v${v}` : name;
}

export function Audit() {
  const trail = useGet<{ redacted: boolean; entries: Entry[] }>("/api/audit?limit=400");
  const [q, setQ] = useState("");
  const columns: Column<Entry>[] = [
    { key: "at", header: "When", render: (e) => <span className="num small">{localTime(e.at)}</span>, width: 130 },
    { key: "who", header: "Who", render: (e) => <span className="small">{who(e)}</span>, width: 190 },
    { key: "action", header: "What", render: (e) => <span className="small">{what(e)}</span>, width: 240 },
    { key: "subject", header: "On", render: (e) => <span className="small muted">{subject(e)}</span> },
    { key: "model", header: "Drafted by", render: (e) => <span className="xsmall muted">{model(e.model_version)}</span>, width: 210 },
  ];
  return (
    <Page title="Audit trail" subtitle="Every AI draft, human decision, declined question and threshold change. Nobody can edit it.">
      <Loaded query={trail}>
        {(t) => {
          const rows = t.entries.filter((e) => !q.trim() || `${what(e)} ${who(e)} ${subject(e)}`.toLowerCase().includes(q.trim().toLowerCase()));
          return (
            <Card flush title={t.redacted ? "Redacted for the authority: roles, not names" : `${rows.length} entries`} actions={<Input aria-label="Filter" placeholder="Filter by action or person" value={q} onChange={(e) => setQ(e.target.value)} className="filter-input" />}>
              <Table caption="Audit trail" columns={columns} rows={rows} rowKey={(e) => String(e.id)} />
            </Card>
          );
        }}
      </Loaded>
    </Page>
  );
}
