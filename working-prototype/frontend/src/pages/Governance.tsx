import { Lock } from "lucide-react";
import { useState } from "react";
import { useGet, useSend } from "../api/hooks";
import type { Me } from "../auth/useMe";
import { ROLE_LABEL, type Role } from "../auth/useMe";
import { Page } from "../layout/AppShell";
import { Button } from "../ui/Button";
import { Card } from "../ui/Card";
import { Field, Input } from "../ui/Field";
import { Select } from "../ui/Select";
import { useToast } from "../ui/Toast";
import { Loaded, titleCase } from "./common";
import "./pages.css";
import "./governance.css";

type Gov = {
  matrix: Record<string, string[]>;
  threshold: number;
  autonomy: { action: string; label: string; locked: boolean; mode: string }[];
  employment_line: string[];
  weights: { id: number; version: string; status: string; note: string | null; approved_at: string | null }[];
};

const SCOPES: [string, string][] = [
  ["own_profile", "Own profile"], ["own_health", "Own health record"], ["crew_actions", "Crew actions"], ["site_tiers", "Tiers and reasons"],
  ["swap_proposals", "Reassignment proposals"], ["fitness_outcomes", "Fitness outcomes"], ["permit_counts", "Permit counts"],
  ["aggregates", "Site totals"], ["all_records", "Every record"], ["health_detail", "Health detail"],
  ["district_aggregates", "District totals"], ["employer_aggregates", "Employer totals"], ["audit_redacted", "Audit trail (redacted)"], ["admin", "Administration"],
];
const MODES = [
  { value: "tell_me", label: "Tell me" },
  { value: "draft_it", label: "Draft it" },
  { value: "do_and_tell", label: "Do it and tell me" },
];

export function Governance({ me }: { me: Me }) {
  const gov = useGet<Gov>("/api/governance");
  const canEdit = me.role === "hse_head" || me.role === "admin";
  return (
    <Page title="Governance" subtitle="Who sees what, what stays with people, and the line against employment use.">
      <Loaded query={gov}>
        {(g) => (
          <div className="stack">
            <Card title="Who sees what" subtitle="The API enforces this table; the screens only reflect it" flush>
              <div className="dl-table-wrap">
                <table className="dl-table matrix-table">
                  <caption className="visually-hidden">Access by role</caption>
                  <thead>
                    <tr>
                      <th scope="col">Data</th>
                      {Object.keys(g.matrix).map((r) => <th key={r} scope="col">{ROLE_LABEL[r as Role] ?? r}</th>)}
                    </tr>
                  </thead>
                  <tbody>
                    {SCOPES.map(([scope, label]) => (
                      <tr key={scope}>
                        <td className="row-head">{label}</td>
                        {Object.entries(g.matrix).map(([role, scopes]) => (
                          <td key={role} className="matrix-table__cell">{scopes.includes(scope) ? <span className="matrix-table__yes" aria-label="Yes">●</span> : <span className="visually-hidden">No</span>}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
            <div className="grid grid--2">
              <Threshold value={g.threshold} canEdit={canEdit} />
              <Card title="The line against employment use">
                <ul className="list">{g.employment_line.map((l) => <li key={l} className="small">{l}</li>)}</ul>
              </Card>
            </div>
            <Card title="Copilot autonomy" subtitle="Per action. Reassigning a worker, signing a permit and restricting on health grounds are locked to people.">
              <ul className="list">
                {g.autonomy.map((a) => <AutonomyRow key={a.action} item={a} canEdit={canEdit} />)}
              </ul>
            </Card>
            <Card title="Model weights" subtitle="Closed outcomes propose a new version. A person approves it; nothing moves silently.">
              <ul className="list">
                {g.weights.map((w) => <WeightsRow key={w.id} w={w} canEdit={canEdit} />)}
              </ul>
            </Card>
          </div>
        )}
      </Loaded>
    </Page>
  );
}

function Threshold({ value, canEdit }: { value: number; canEdit: boolean }) {
  const [v, setV] = useState(String(value));
  const save = useSend<{ value: number }>("PUT", "/api/governance/threshold");
  const toast = useToast();
  return (
    <Card title="Small groups" subtitle="Any group below this size is hidden in every view, and totals are rounded to the nearest 5.">
      <div className="row" style={{ alignItems: "flex-end", flexWrap: "nowrap" }}>
        <Field label="Hide groups under" hint="Between 5 and 50 people">
          {(p) => <Input {...p} type="number" min={5} max={50} value={v} disabled={!canEdit} onChange={(e) => setV(e.target.value)} style={{ width: 120 }} />}
        </Field>
        {canEdit && <Button variant="primary" busy={save.isPending} onClick={() => save.mutate({ value: Number(v) }, { onSuccess: () => toast({ title: "Threshold saved", body: "It applies everywhere now and is in the audit trail.", tone: "good" }), onError: (e) => toast({ title: "Not saved", body: e.message, tone: "critical" }) })}>Save</Button>}
      </div>
    </Card>
  );
}

function AutonomyRow({ item, canEdit }: { item: Gov["autonomy"][number]; canEdit: boolean }) {
  const save = useSend<{ action: string; mode: string }>("PUT", "/api/governance/autonomy");
  return (
    <li className="row row--between">
      <span className="small row">{item.locked && <Lock size={14} aria-label="Locked to people" />}{item.label}</span>
      <Select
        aria-label={`Autonomy for ${item.label}`}
        value={item.mode}
        disabled={!canEdit}
        onValueChange={(mode) => save.mutate({ action: item.action, mode })}
        options={MODES.map((m) => ({ ...m, disabled: item.locked && m.value === "do_and_tell" }))}
        className="autonomy-select"
      />
    </li>
  );
}

function WeightsRow({ w, canEdit }: { w: Gov["weights"][number]; canEdit: boolean }) {
  const approve = useSend<Record<string, never>>("POST", `/api/governance/weights/${w.id}/approve`);
  return (
    <li className="row row--between">
      <span className="stack stack--tight">
        <span className="small"><strong>{w.version}</strong> · {titleCase(w.status)}</span>
        {w.note && <span className="xsmall muted">{w.note}</span>}
      </span>
      {w.status === "proposed" && canEdit && <Button size="sm" variant="primary" busy={approve.isPending} onClick={() => approve.mutate({})}>Approve</Button>}
    </li>
  );
}
