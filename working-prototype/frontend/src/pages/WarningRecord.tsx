import { ArrowLeft, ClipboardCheck, FilePlus2, PenLine, Plus, Sparkles } from "lucide-react";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { toDraft, useGet, useSend, type ApiDraft } from "../api/hooks";
import type { Me, Role } from "../auth/useMe";
import { Page } from "../layout/AppShell";
import { localTime, useMeta } from "../layout/Meta";
import { AiSection } from "../ui/AiSection";
import { Button } from "../ui/Button";
import { Card } from "../ui/Card";
import { Dialog } from "../ui/Dialog";
import { Field, Input } from "../ui/Field";
import { Select } from "../ui/Select";
import { TextArea } from "../ui/TextArea";
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
              <Card
                title="Actions"
                subtitle="Ranked by the hierarchy of controls"
                actions={me.role === "hse_head" && w.status === "open" ? <AddAction warningId={w.id} /> : undefined}
              >
                {w.actions.length === 0 ? <p className="small muted">No actions yet. Add them once the controls in step 7 are agreed.</p> : (
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
  const draft = useSend<{ refresh: boolean }, { draft: { status: string } | null }>("POST", `/api/warnings/${warningId}/steps/${step.step}/draft`);
  const aiOn = useMeta().data?.ai_available ?? false;
  const confirm = useSend<{ content: string }>("POST", `/api/warnings/${warningId}/steps/${step.step}/confirm`);
  const d = toDraft(step.draft);
  const mine = canConfirm(me.role, step.confirmer_role);
  const [writing, setWriting] = useState(false);
  const [text, setText] = useState("");
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
        {!d && open && step.step < 10 && !writing && (mine || me.role === "hse_head") && (
          <div className="row">
            {me.role === "hse_head" && aiOn && (
              <Button
                size="sm"
                variant="secondary"
                icon={<Sparkles />}
                busy={draft.isPending}
                onClick={() =>
                  draft.mutate(
                    { refresh: false },
                    {
                      onSuccess: (r) => {
                        if (r.draft?.status === "unavailable") {
                          toast({ title: "Draft not available", body: "The copilot could not be reached. Write this section yourself.", tone: "warning" });
                          setWriting(true);
                        }
                      },
                    },
                  )
                }
              >
                Draft this section
              </Button>
            )}
            {mine && (
              <Button size="sm" variant="ghost" icon={<PenLine />} onClick={() => setWriting(true)}>
                Write it yourself
              </Button>
            )}
            <span className="xsmall muted">{aiOn && me.role === "hse_head" ? "The copilot writes from the record so far, or you write it." : "The copilot is not available, so you write this section."} Nothing is saved until you confirm.</span>
          </div>
        )}
        {!d && open && writing && (
          <div className="stack stack--tight">
            <TextArea aria-label={`${step.name}: your text`} rows={4} value={text} onChange={(e) => setText(e.target.value)} />
            <div className="row" style={{ justifyContent: "flex-end" }}>
              <Button size="sm" variant="ghost" onClick={() => setWriting(false)}>Cancel</Button>
              <Button
                size="sm"
                variant="primary"
                disabled={!text.trim()}
                busy={confirm.isPending}
                onClick={() => confirm.mutate({ content: text.trim() }, { onSuccess: () => { setWriting(false); toast({ title: `${step.name} confirmed`, tone: "good" }); }, onError: (e) => toast({ title: "Not confirmed", body: e.message, tone: "critical" }) })}
              >
                Confirm section
              </Button>
            </div>
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

const LEVELS = [
  { value: "eliminate", label: "Eliminate", hint: "Remove the hazard" },
  { value: "substitute", label: "Substitute", hint: "Swap for something less hazardous" },
  { value: "engineer", label: "Engineer", hint: "Change the equipment or the place" },
  { value: "administrative", label: "Administrative", hint: "Change how the work is organised" },
  { value: "ppe", label: "Protective equipment", hint: "The last line of defence" },
];

/** "2026-07-29" plus some days, as a date string. */
function addDays(isoDate: string, days: number): string {
  const d = new Date(`${isoDate}T12:00:00Z`);
  d.setUTCDate(d.getUTCDate() + days);
  return d.toISOString().slice(0, 10);
}

function AddAction({ warningId }: { warningId: number }) {
  const [open, setOpen] = useState(false);
  const meta = useMeta();
  const owners = useGet<{ id: number; name: string; job: string }[]>("/api/action-owners", { enabled: open });
  const today = meta.data?.site_now_local.slice(0, 10) ?? "2026-07-28";
  const [title, setTitle] = useState("");
  const [level, setLevel] = useState<string>();
  const [owner, setOwner] = useState<string>();
  const [due, setDue] = useState(() => addDays(today, 7));
  const [check, setCheck] = useState(() => addDays(today, 21));
  const create = useSend<{ source_kind: string; source_id: number; title: string; control_level: string; owner_id: number; due_on: string; effectiveness_check_on: string }>("POST", "/api/actions");
  const toast = useToast();
  const ready = title.trim() && level && owner && due && check;
  return (
    <>
      <Button size="sm" variant="secondary" icon={<Plus />} onClick={() => setOpen(true)}>Add action</Button>
      <Dialog
        open={open}
        onOpenChange={setOpen}
        title="Add an action"
        description="Each action has an owner, a due date and a date to check that it worked."
        footer={
          <>
            <Button variant="ghost" onClick={() => setOpen(false)}>Cancel</Button>
            <Button
              variant="primary"
              disabled={!ready}
              busy={create.isPending}
              onClick={() =>
                create.mutate(
                  { source_kind: "warning", source_id: warningId, title: title.trim(), control_level: level!, owner_id: Number(owner), due_on: due, effectiveness_check_on: check },
                  { onSuccess: () => { setOpen(false); setTitle(""); toast({ title: "Action added", tone: "good" }); }, onError: (e) => toast({ title: "Not added", body: e.message, tone: "critical" }) },
                )
              }
            >
              Add action
            </Button>
          </>
        }
      >
        <div className="stack">
          <Field label="What will be done">{(p) => <Input {...p} value={title} onChange={(e) => setTitle(e.target.value)} placeholder="For example: repair the cooling units in Camp Block C" />}</Field>
          <Field label="Level">{(p) => <Select {...p} value={level} onValueChange={setLevel} placeholder="Choose a level" options={LEVELS} />}</Field>
          <Field label="Owner">{(p) => <Select {...p} value={owner} onValueChange={setOwner} placeholder="Choose an owner" options={(owners.data ?? []).map((o) => ({ value: String(o.id), label: o.name, hint: o.job }))} />}</Field>
          <div className="grid grid--2">
            <Field label="Due">{(p) => <Input {...p} type="date" value={due} onChange={(e) => setDue(e.target.value)} />}</Field>
            <Field label="Check it worked on">{(p) => <Input {...p} type="date" value={check} onChange={(e) => setCheck(e.target.value)} />}</Field>
          </div>
        </div>
      </Dialog>
    </>
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

