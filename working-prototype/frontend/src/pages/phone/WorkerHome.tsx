import { BookOpen, HeartPulse, Languages, MessageSquareWarning } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";
import { useGet, useSend } from "../../api/hooks";
import type { Me } from "../../auth/useMe";
import { Button } from "../../ui/Button";
import { Dialog } from "../../ui/Dialog";
import { Field } from "../../ui/Field";
import { TextArea } from "../../ui/TextArea";
import { TierChip, type Tier } from "../../ui/TierChip";
import { useToast } from "../../ui/Toast";
import { Loaded } from "../common";
import "../pages.css";

type MeData = {
  name: string; language: string;
  assignment: { id: number; shift: { label: string }; activity: string; zone: string | null } | null;
  checked_in: boolean; tier: Tier | null; reason_en: string | null; reason_local: string | null;
  swap_to: string | null; contest: { status: string; text: string } | null; cards_unread: number;
};

const SLEEP: [string, string][] = [["under_5", "Under 5 hours"], ["5_to_6", "5 to 6 hours"], ["6_to_7", "6 to 7 hours"], ["7_plus", "7 hours or more"]];
const FEEL: [string, string][] = [["good", "Good"], ["tired", "Tired"], ["unwell", "Not well"]];

export function WorkerHome({ me }: { me: Me }) {
  const data = useGet<MeData>("/api/phone/me");
  return (
    <Loaded query={data}>
      {(d) => (
        <>
          <div className="stack stack--tight">
            <span className="small muted">Hello</span>
            <h1 className="phone-title">{d.name}</h1>
          </div>
          {d.assignment ? (
            <div className="phone-card">
              <span className="small muted">{d.assignment.shift.label}</span>
              <strong>{d.assignment.activity}</strong>
              {d.assignment.zone && <span className="small muted">{d.assignment.zone}</span>}
            </div>
          ) : (
            <div className="phone-card"><span className="small">No shift on the roster for you.</span></div>
          )}
          {d.assignment && !d.checked_in && <CheckIn />}
          {d.checked_in && <div className="phone-card phone-card--mint small">Checked in. Thank you.</div>}
          {d.tier && d.tier !== "fit" && <Reason d={d} />}
          {d.tier === "fit" && <div className="phone-card phone-card--mint"><TierChip tier="fit" size="lg" /><span className="small">You are good for tonight's work. Stay hydrated.</span></div>}
          <Unwell disabled={!d.assignment} />
          <Link to="/m/cards" className="phone-card row row--between" style={{ textDecoration: "none", color: "inherit" }}>
            <span className="row"><BookOpen size={18} aria-hidden="true" /> Safety cards</span>
            {d.cards_unread > 0 && <span className="pill pill--periwinkle">{d.cards_unread} new</span>}
          </Link>
          <p className="xsmall muted">{me.employer}</p>
        </>
      )}
    </Loaded>
  );
}

function CheckIn() {
  const [sleep, setSleep] = useState<string>();
  const [feel, setFeel] = useState<string>();
  const [water, setWater] = useState<boolean>();
  const send = useSend<{ sleep_band: string; feeling: string; hydration_ok: boolean }>("POST", "/api/phone/checkin");
  const toast = useToast();
  return (
    <div className="phone-card phone-card--tint">
      <strong>Check in for tonight</strong>
      <span className="small">How long did you sleep?</span>
      <div className="tap-grid">
        {SLEEP.map(([v, l]) => <button key={v} type="button" className="tap" aria-pressed={sleep === v} onClick={() => setSleep(v)}>{l}</button>)}
      </div>
      <span className="small">How do you feel?</span>
      <div className="tap-grid" style={{ gridTemplateColumns: "repeat(3, 1fr)" }}>
        {FEEL.map(([v, l]) => <button key={v} type="button" className="tap" aria-pressed={feel === v} onClick={() => setFeel(v)}>{l}</button>)}
      </div>
      <span className="small">Have you had enough water?</span>
      <div className="tap-grid">
        <button type="button" className="tap" aria-pressed={water === true} onClick={() => setWater(true)}>Yes</button>
        <button type="button" className="tap" aria-pressed={water === false} onClick={() => setWater(false)}>Not yet</button>
      </div>
      <Button variant="primary" block disabled={!sleep || !feel || water === undefined} busy={send.isPending} onClick={() => send.mutate({ sleep_band: sleep!, feeling: feel!, hydration_ok: water! }, { onSuccess: () => toast({ title: "Checked in", tone: "good" }) })}>
        Send check-in
      </Button>
    </div>
  );
}

function Reason({ d }: { d: MeData }) {
  const [english, setEnglish] = useState(d.reason_local === null);
  const [open, setOpen] = useState(false);
  const [text, setText] = useState("");
  const contest = useSend<{ text: string }>("POST", "/api/phone/contest");
  const toast = useToast();
  return (
    <div className="phone-card phone-card--rose">
      <TierChip tier={d.tier!} size="lg" />
      {d.swap_to && <strong>Tonight: {d.swap_to}</strong>}
      <p className={english ? "small" : "phone-local"} lang={english ? "en" : d.language}>{english ? d.reason_en : d.reason_local}</p>
      {d.reason_local && (
        <button type="button" className="tap" style={{ minHeight: 44 }} onClick={() => setEnglish(!english)}>
          <Languages size={16} aria-hidden="true" style={{ marginRight: 8 }} /> {english ? "Show in my language" : "Show in English"}
        </button>
      )}
      {d.contest ? (
        <span className="pill pill--sand">You contested this. The planner will reply.</span>
      ) : (
        <Button variant="secondary" block icon={<MessageSquareWarning />} onClick={() => setOpen(true)}>Contest this change</Button>
      )}
      <Dialog
        open={open}
        onOpenChange={setOpen}
        title="Why do you disagree?"
        description="The planner sees your words. This is never held against you."
        footer={<Button variant="primary" block disabled={!text.trim()} busy={contest.isPending} onClick={() => contest.mutate({ text }, { onSuccess: () => { setOpen(false); toast({ title: "Sent to the planner", tone: "good" }); } })}>Send</Button>}
      >
        <Field label="Your reason">{(p) => <TextArea {...p} rows={4} value={text} onChange={(e) => setText(e.target.value)} />}</Field>
      </Dialog>
    </div>
  );
}

function Unwell({ disabled }: { disabled: boolean }) {
  const [open, setOpen] = useState(false);
  const send = useSend<Record<string, never>, { next: string }>("POST", "/api/phone/unwell");
  const toast = useToast();
  return (
    <>
      <Button variant="danger" block icon={<HeartPulse />} disabled={disabled} onClick={() => setOpen(true)} style={{ minHeight: 56 }}>
        I feel unwell
      </Button>
      <Dialog
        open={open}
        onOpenChange={setOpen}
        title="Tell the clinic you feel unwell?"
        description="The clinician is told straight away. Your crew's permit shows only that a crew member went to the cool room, not your name."
        footer={<Button variant="danger" block busy={send.isPending} onClick={() => send.mutate({}, { onSuccess: (r) => { setOpen(false); toast({ title: "The clinic has been told", body: r.next, tone: "warning" }); } })}>Yes, tell the clinic</Button>}
      />
    </>
  );
}
