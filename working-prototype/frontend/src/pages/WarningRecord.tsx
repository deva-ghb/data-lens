import { ArrowLeft, ClipboardCheck, FilePlus2, Sparkles } from "lucide-react";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { toDraft, useGet, useSend, type ApiDraft } from "../api/hooks";
import type { Me, Role } from "../auth/useMe";
import { Page } from "../layout/AppShell";
import { localTime } from "../layout/Meta";
import { AiSection } from "../ui/AiSection";
import { Button } from "../ui/Button";
import { Card } from "../ui/Card";
import { Dialog } from "../ui/Dialog";
import { Select } from "../ui/Select";
import { useToast } from "../ui/Toast";
import { Loaded, titleCase } from "./common";
import "./pages.css";
import "./warnings.css";

type Step = { step: number; name: string; status: "pending" | "drafted" | "confirmed"; confirmer_role: string; linked_by_ai: boolean; draft: ApiDraft | null; confirmed_by: string | null; confirmed_at: string | null };
type Signal = { feed: string; feed_name: string; class: string; metric: string; zone: string; period_start: string; period_end: string; observed: number; expected: number; ratio: number };
type Record_ = {
  id: number; zone: string; level: string; status: string; outcome: string | null; opened_at: string; closed_at: string | null; classes: string[];
  evidence: { signals: Signal[]; late_feeds: string[]; index: number } | null;
  steps: Step[];
  permits_affected: { id: number; number: string; status: string }[];
  actions: { id: number; title: string; status: string; control_level: string }[];
  inspections: { id: number; status: string; due_at: string }[];
  verification: { confirmed: number; not_found: number; total: number } | null;
};

const CONFIRMER_NAMES: Record<string, string> = { hse_head: "Head of HSE", permit_issuer: "Permit issuer", foreman: "Foreman", system: "Closes automatically" };
const confirmerName = (role: string): string => CONFIRMER_NAMES[role] ?? "the named role";

function canConfirm(role: Role, confirmer: string): boolean {
  if (confirmer === "hse_head") return role === "hse_head";
  if (confirmer === "permit_issuer") return role === "permit_issuer";
  if (confirmer === "foreman") return role === "foreman" || role === "hse_head";
  return false;
}

export function WarningRecord({ me }: { me: Me }) {
  const { warningId } = useParams();
  const record = useGet<Record_>(`/api/warnings/${warningId}`);
  return (
    <Loaded query={record} lines={12}>
      {(w) => (
        <Page
          title={`Early warning: ${w.zone}`}
          subtitle={`Opened ${localTime(w.opened_at)}. The copilot drafts each section; the named role confirms it.`}
          actions={<Link to="/warnings" className="link row"><ArrowLeft size={16} aria-hidden="true" /> All warnings</Link>}
          wide
        >
          <div className="row">
            <span className={w.status === "open" ? "pill pill--rose" : "pill pill--mint"}>{w.status === "open" ? titleCase(w.level) : `Closed: ${titleCase(w.outcome ?? "")}`}</span>
            {w.classes.map((c) => <span key={c} className="pill pill--periwinkle">{titleCase(c)}</span>)}
          </div>
          <div className="grid grid--main-side">
            <Card title="The record" subtitle="Ten steps, from detection to close">
              <ol className="steps">
                {w.steps.map((s) => (
                  <StepView key={s.step} warningId={w.id} step={s} me={me} open={w.status === "open"} />
                ))}
              </ol>
            </Card>
            <div className="stack">
              <SignalsCard w={w} />
              <Card title="Permits affected">
                {w.permits_affected.length === 0 ? <p className="small muted">None on the next shift.</p> : (
                  <ul className="list">
                    {w.permits_affected.map((p) => (
                      <li key={p.id} className="row row--between">
                        <Link className="link num" to={`/permits/${p.id}`}>{p.number}</Link>
                        <span className="pill">{titleCase(p.status)}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </Card>
              <VerifyCard w={w} canAct={me.role === "hse_head" && w.status === "open"} />
              <Card title="Actions" subtitle="Ranked by the hierarchy of controls">
                {w.actions.length === 0 ? <p className="small muted">No actions yet. They are created from step 7.</p> : (
                  <ul className="list">
                    {w.actions.map((a) => (
                      <li key={a.id} className="stack stack--tight">
                        <span className="small">{a.title}</span>
                        <span className="xsmall muted">{titleCase(a.control_level)} · {titleCase(a.status)}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </Card>
              {me.role === "hse_head" && w.status === "open" && <CloseCard id={w.id} />}
            </div>
          </div>
        </Page>
      )}
    </Loaded>
  );
}

function StepView({ warningId, step, me, open }: { warningId: number; step: Step; me: Me; open: boolean }) {
  const toast = useToast();
  const draft = useSend<{ refresh: boolean }>("POST", `/api/warnings/${warningId}/steps/${step.step}/draft`);
  const confirm = useSend<{ content: string }>("POST", `/api/warnings/${warningId}/steps/${step.step}/confirm`);
  const d = toDraft(step.draft);
  const mine = canConfirm(me.role, step.confirmer_role);
  return (
    <li className={`step step--${step.status}`}>
      <span className="step__no num">{step.step}</span>
      <div className="step__body">
        <div className="step__head">
          <span className="step__name">{step.name}</span>
          <span className="xsmall muted">
            {step.status === "confirmed"
              ? step.confirmed_by
                ? `Confirmed by ${step.confirmed_by}`
                : step.linked_by_ai ? "Linked by the copilot" : "Closed"
              : `${step.linked_by_ai ? "Linked by the copilot, checked by" : "Confirmed by"} ${confirmerName(step.confirmer_role)}`}
          </span>
        </div>
        {d && step.status === "confirmed" && <p className="prose small">{d.content}</p>}
        {d && step.status !== "confirmed" && (
          <AiSection
            draft={d}
            title="Copilot draft"
            confirmLabel={mine ? "Confirm section" : `Waiting for the ${confirmerName(step.confirmer_role).toLowerCase()}`}
            busy={confirm.isPending}
            onEdit={() => undefined}
            onConfirm={(content) =>
              mine
                ? confirm.mutate({ content }, { onSuccess: () => toast({ title: `${step.name} confirmed`, tone: "good" }), onError: (e) => toast({ title: "Not confirmed", body: e.message, tone: "critical" }) })
                : toast({ title: `Only the ${confirmerName(step.confirmer_role).toLowerCase()} confirms this section`, tone: "neutral" })
            }
          />
        )}
        {!d && open && step.step < 10 && (me.role === "hse_head" || me.role === "permit_issuer") && (
          <div className="row">
            <Button size="sm" variant="secondary" icon={<Sparkles />} busy={draft.isPending} onClick={() => draft.mutate({ refresh: false }, { onError: (e) => toast({ title: "No draft", body: e.message, tone: "critical" }) })}>
              Draft this section
            </Button>
            <span className="xsmall muted">The copilot writes from the record so far. You edit and confirm.</span>
          </div>
        )}
        {!d && !open && <p className="small muted">Not recorded.</p>}
      </div>
    </li>
  );
}

function SignalsCard({ w }: { w: Record_ }) {
  const signals = w.evidence?.signals ?? [];
  const max = Math.max(2, ...signals.map((s) => s.ratio));
  return (
    <Card title="What moved" subtitle="Against each signal's own baseline">
      <div className="stack">
        {signals.map((s) => (
          <div key={`${s.feed}-${s.metric}`} className="stack stack--tight">
            <span className="small">{s.feed_name}: {s.metric.split("_").join(" ")}</span>
            <div className="signal-row">
              <span className="signal-row__bar"><span className="signal-row__fill" style={{ width: `${Math.min(100, (s.ratio / max) * 100)}%` }} /></span>
              <span className="num small">{s.ratio.toFixed(1)} times</span>
            </div>
            <span className="xsmall muted">{s.zone} · {s.observed} seen against {s.expected} usual · {s.period_start} to {s.period_end}</span>
          </div>
        ))}
        {(w.evidence?.late_feeds ?? []).length > 0 && <p className="xsmall">Late feeds: {w.evidence?.late_feeds.join(", ")}</p>}
      </div>
    </Card>
  );
}

function VerifyCard({ w, canAct }: { w: Record_; canAct: boolean }) {
  const build = useSend<Record<string, never>>("POST", `/api/warnings/${w.id}/inspection`);
  return (
    <Card
      title="Verify on the ground"
      actions={canAct && w.inspections.length === 0 ? <Button size="sm" icon={<ClipboardCheck />} busy={build.isPending} onClick={() => build.mutate({})}>Build inspection</Button> : undefined}
    >
      {w.inspections.length === 0 ? (
        <p className="small muted">One check per driver, in the place and at the time the driver acts.</p>
      ) : (
        <div className="stack stack--tight">
          {w.inspections.map((i) => (
            <Link key={i.id} to="/inspections" className="link small">Inspection due {localTime(i.due_at)} · {titleCase(i.status)}</Link>
          ))}
          {w.verification && <span className="small">{w.verification.confirmed} of {w.verification.total} checks confirmed on the ground</span>}
        </div>
      )}
    </Card>
  );
}

function CloseCard({ id }: { id: number }) {
  const [open, setOpen] = useState(false);
  const [outcome, setOutcome] = useState<string>();
  const close = useSend<{ outcome: string }>("POST", `/api/warnings/${id}/close`);
  const toast = useToast();
  return (
    <Card title="Close the record" subtitle="Recorded either way: this is how lead time and false alarms are measured.">
      <Button icon={<FilePlus2 />} onClick={() => setOpen(true)}>Record the outcome</Button>
      <Dialog
        open={open}
        onOpenChange={setOpen}
        title="How did this warning turn out?"
        footer={
          <>
            <Button variant="ghost" onClick={() => setOpen(false)}>Cancel</Button>
            <Button variant="primary" disabled={!outcome} busy={close.isPending} onClick={() => close.mutate({ outcome: outcome! }, { onSuccess: () => { setOpen(false); toast({ title: "Record closed", tone: "good" }); } })}>Close record</Button>
          </>
        }
      >
        <Select
          aria-label="Outcome"
          value={outcome}
          onValueChange={setOutcome}
          placeholder="Choose the outcome"
          options={[
            { value: "right", label: "Right", hint: "It was real and the warning came in time" },
            { value: "early", label: "Early", hint: "Real, but earlier than it needed to be" },
            { value: "false_alarm", label: "False alarm", hint: "Nothing was building" },
            { value: "missed", label: "Missed", hint: "Something happened that this did not stop" },
          ]}
        />
      </Dialog>
    </Card>
  );
}

