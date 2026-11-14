import { ArrowLeft, Check, Pencil, Plus, X } from "lucide-react";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useGet, useSend } from "../api/hooks";
import type { Me } from "../auth/useMe";
import { Page } from "../layout/AppShell";
import { localTime } from "../layout/Meta";
import { Button } from "../ui/Button";
import { Card } from "../ui/Card";
import { Dialog } from "../ui/Dialog";
import { Field, Input } from "../ui/Field";
import { StatusDot } from "../ui/StatusDot";
import { TextArea } from "../ui/TextArea";
import { TIER_LOOK, type Tier } from "../ui/TierChip";
import { useToast } from "../ui/Toast";
import { Loaded, pct, titleCase } from "./common";
import { CREW } from "./Permits";
import "./pages.css";
import "./permits.css";

type Permit = {
  id: number;
  number: string;
  activity: string;
  grade: number;
  zone: string;
  status: string;
  shift: { label: string };
  issuer: string | null;
  vessel: string | null;
  forecast: { peak_wbgt: number | null; heat_tier: number | null };
  people_factor: { crew_size: number; readiness: Record<Tier, number>; crew_status: "green" | "amber" | "red" | "unscored"; open_reassignments: number; top_drivers: string[]; confidence: number | null; scored: boolean };
  conditions: { id: number; text: string; origin: string; status: string; warning_id: number | null }[];
  events: { id: number; at: string; kind: string; text: string; by: string | null }[];
};

const MOVES: Record<string, { label: string; to: string; variant: "primary" | "secondary" | "danger" }[]> = {
  requested: [{ label: "Assess", to: "assess", variant: "primary" }],
  assessed: [
    { label: "Send back", to: "send-back", variant: "secondary" },
    { label: "Sign and issue", to: "sign", variant: "primary" },
  ],
  issued: [
    { label: "Hold", to: "hold", variant: "secondary" },
    { label: "Start work", to: "start", variant: "primary" },
  ],
  live: [
    { label: "Suspend", to: "suspend", variant: "danger" },
    { label: "Close", to: "close", variant: "secondary" },
  ],
  suspended: [
    { label: "Resume", to: "resume", variant: "primary" },
    { label: "Close", to: "close", variant: "secondary" },
  ],
  closed: [],
};

const TONE: Record<Tier, string> = { fit: "good", fit_with_controls: "warning", reassign: "critical", refer: "lilac", unknown: "neutral" };

export function PermitDetail({ me }: { me: Me }) {
  const { permitId } = useParams();
  const permit = useGet<Permit>(`/api/permits/${permitId}`);
  const canAct = me.role === "permit_issuer" || me.role === "hse_head";
  return (
    <Loaded query={permit}>
      {(p) => (
        <Page
          title={p.number}
          subtitle={`${p.activity} at ${p.zone}, ${p.shift.label}${p.vessel ? `, ${p.vessel} alongside` : ""}`}
          actions={
            <Link to="/permits" className="link row">
              <ArrowLeft size={16} aria-hidden="true" /> All permits
            </Link>
          }
        >
          <div className="row">
            <span className="pill pill--periwinkle">{titleCase(p.status)}</span>
            <StatusDot status={CREW[p.people_factor.crew_status].status} label={CREW[p.people_factor.crew_status].label} />
            {p.issuer && <span className="small muted">Issuer: {p.issuer}</span>}
          </div>
          <div className="grid grid--main-side">
            <div className="stack">
              <Card title="People and conditions" subtitle="The crew as counts. The reassigned worker's record goes to the planner and the worker only.">
                <div className="stack">
                  <div className="readiness">
                    {(Object.keys(TIER_LOOK) as Tier[]).map((t) => (
                      <div key={t} className={`readiness__cell dl-chip--${TONE[t]}`}>
                        <span className="xsmall">{TIER_LOOK[t].label}</span>
                        <span className="readiness__value num">{p.people_factor.readiness[t] ?? 0}</span>
                      </div>
                    ))}
                  </div>
                  <dl className="kv">
                    <dt>Crew</dt>
                    <dd>{p.people_factor.crew_size} people</dd>
                    <dt>Confidence</dt>
                    <dd>{p.people_factor.confidence !== null ? pct(p.people_factor.confidence) : "Not scored yet"}</dd>
                    <dt>Forecast</dt>
                    <dd>{p.forecast.peak_wbgt !== null ? `Peak WBGT ${p.forecast.peak_wbgt.toFixed(1)} °C, heat tier ${p.forecast.heat_tier}` : "No forecast"}</dd>
                    <dt>Top drivers</dt>
                    <dd>{p.people_factor.top_drivers.length ? p.people_factor.top_drivers.join("; ") : "None"}</dd>
                  </dl>
                  {p.people_factor.crew_status === "unscored" && <p className="small" role="status">The planner has not scored this crew yet, so it cannot be signed.</p>}
                  {p.people_factor.crew_status === "red" && (
                    <p className="small" role="status">
                      This permit cannot be signed until the planner settles {p.people_factor.open_reassignments} open reassignment{p.people_factor.open_reassignments === 1 ? "" : "s"}.
                    </p>
                  )}
                </div>
              </Card>
              <Conditions permit={p} canAct={canAct} />
            </div>
            <div className="stack">
              {canAct && <Lifecycle permit={p} />}
              <Card title="Permit log">
                <ol className="timeline">
                  {[...p.events].reverse().map((e) => (
                    <li key={e.id}>
                      <span className="xsmall muted num">{localTime(e.at)}</span>
                      <span className={e.kind === "wbgt_limit" || e.kind === "worker_unwell" ? "timeline__alert" : undefined}>
                        {e.text}
                        {e.by && <span className="xsmall muted"> · {e.by}</span>}
                      </span>
                    </li>
                  ))}
                </ol>
              </Card>
              <a className="link small" href={`/api/permits/${p.id}/people-factor.json`} target="_blank" rel="noreferrer">
                People-factor record (JSON) for the permit system
              </a>
            </div>
          </div>
        </Page>
      )}
    </Loaded>
  );
}

function Lifecycle({ permit }: { permit: Permit }) {
  const toast = useToast();
  const move = useSend<{ move: string; reason?: string }>("POST", (b) => `/api/permits/${permit.id}/${b.move}`);
  const [sendBack, setSendBack] = useState(false);
  const [reason, setReason] = useState("");
  const run = (m: string, extra?: { reason: string }) =>
    move.mutate(
      { move: m, ...extra },
      {
        onSuccess: () => toast({ title: m === "sign" ? "Permit signed and issued" : "Permit updated", tone: "good" }),
        onError: (e) => toast({ title: "Not done", body: e.message, tone: "critical" }),
      },
    );
  const moves = MOVES[permit.status] ?? [];
  return (
    <Card title="Issuer actions">
      <div className="row">
        {moves.length === 0 && <span className="small muted">This permit is closed.</span>}
        {moves.map((m) => (
          <Button key={m.label} variant={m.variant} busy={move.isPending && move.variables?.move === m.to} onClick={() => (m.to === "send-back" ? setSendBack(true) : run(m.to))}>
            {m.label}
          </Button>
        ))}
      </div>
      <Dialog
        open={sendBack}
        onOpenChange={setSendBack}
        title="Send the permit back?"
        footer={
          <>
            <Button variant="ghost" onClick={() => setSendBack(false)}>Cancel</Button>
            <Button variant="primary" disabled={!reason.trim()} onClick={() => { run("send-back", { reason: reason.trim() }); setSendBack(false); }}>Send back</Button>
          </>
        }
      >
        <Field label="What needs to change">{(p) => <TextArea {...p} rows={3} value={reason} onChange={(e) => setReason(e.target.value)} />}</Field>
      </Dialog>
    </Card>
  );
}

function Conditions({ permit, canAct }: { permit: Permit; canAct: boolean }) {
  const [adding, setAdding] = useState(false);
  const [text, setText] = useState("");
  const add = useSend<{ text: string }>("POST", `/api/permits/${permit.id}/conditions`);
  return (
    <Card
      title="Conditions"
      subtitle="Conditions an early warning drafts arrive here for the issuer to accept, edit or reject."
      actions={canAct && permit.status !== "closed" ? <Button size="sm" variant="secondary" icon={<Plus />} onClick={() => setAdding(true)}>Add condition</Button> : undefined}
    >
      <div className="stack stack--tight">
        {permit.conditions.length === 0 && <p className="small muted">No conditions beyond the standard permit.</p>}
        {permit.conditions.map((c) => (
          <ConditionRow key={c.id} permitId={permit.id} condition={c} canAct={canAct} />
        ))}
        {adding && (
          <div className="row" style={{ flexWrap: "nowrap" }}>
            <Input aria-label="New condition" value={text} onChange={(e) => setText(e.target.value)} placeholder="For example: buddy pairs above the second tier" style={{ flex: 1 }} />
            <Button variant="primary" disabled={!text.trim()} busy={add.isPending} onClick={() => add.mutate({ text: text.trim() }, { onSuccess: () => { setText(""); setAdding(false); } })}>
              Add
            </Button>
          </div>
        )}
      </div>
    </Card>
  );
}

function ConditionRow({ permitId, condition, canAct }: { permitId: number; condition: Permit["conditions"][number]; canAct: boolean }) {
  const patch = useSend<{ text?: string; status?: string }>("PATCH", `/api/permits/${permitId}/conditions/${condition.id}`);
  const [editing, setEditing] = useState(false);
  const [text, setText] = useState(condition.text);
  const draft = condition.status === "draft";
  return (
    <div className={draft ? "condition condition--draft" : "condition"}>
      <div className="condition__text stack stack--tight">
        {editing ? (
          <Input aria-label="Condition" value={text} onChange={(e) => setText(e.target.value)} />
        ) : (
          <span className="small">{condition.text}</span>
        )}
        <span className="xsmall muted">
          {condition.origin === "warning" ? `From early warning ${condition.warning_id}` : "Added by the issuer"} · {titleCase(condition.status)}
        </span>
      </div>
      {canAct && condition.status !== "rejected" && (
        <div className="row" style={{ flexWrap: "nowrap" }}>
          {editing ? (
            <Button size="sm" variant="primary" onClick={() => patch.mutate({ text }, { onSuccess: () => setEditing(false) })}>Save</Button>
          ) : (
            <>
              <Button size="sm" variant="ghost" iconOnly aria-label="Edit condition" icon={<Pencil />} onClick={() => setEditing(true)} />
              {draft && (
                <>
                  <Button size="sm" variant="ghost" iconOnly aria-label="Reject condition" icon={<X />} onClick={() => patch.mutate({ status: "rejected" })} />
                  <Button size="sm" variant="secondary" icon={<Check />} onClick={() => patch.mutate({ status: "accepted" })}>Accept</Button>
                </>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}
