import { ArrowLeft } from "lucide-react";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useGet, useSend } from "../api/hooks";
import { Page } from "../layout/AppShell";
import { localTime } from "../layout/Meta";
import { Button } from "../ui/Button";
import { Card } from "../ui/Card";
import { Field } from "../ui/Field";
import { Select } from "../ui/Select";
import { TextArea } from "../ui/TextArea";
import { useToast } from "../ui/Toast";
import { Loaded, titleCase } from "./common";
import "./pages.css";

type Record_ = {
  person_id: number; worker: string; job: string; site_arrival_date: string;
  lab_trends: { panel: string; points: { at: string; value: number; flag: string | null }[] }[];
  checkins: { at: string; sleep: string; feeling: string; hydration_ok: boolean }[];
  outcomes: { at: string; outcome: string; restriction: string | null; shared: boolean; by: string | null }[];
};

const SLEEP: Record<string, string> = { under_5: "Under 5 h", "5_to_6": "5 to 6 h", "6_to_7": "6 to 7 h", "7_plus": "7 h or more" };

export function WorkerHealth() {
  const { personId } = useParams();
  const record = useGet<Record_>(`/api/health/workers/${personId}`);
  return (
    <Loaded query={record}>
      {(r) => (
        <Page title={r.worker} subtitle={`${r.job} · on site since ${r.site_arrival_date}`} actions={<Link to="/health" className="link row"><ArrowLeft size={16} aria-hidden="true" /> Screening list</Link>}>
          <div className="grid grid--main-side">
            <div className="stack">
              <Card title="Lab trends" subtitle="Clinician reviewed. Never shown outside the clinic.">
                {r.lab_trends.length === 0 ? <p className="small muted">No lab panels on record.</p> : (
                  <ul className="list">
                    {r.lab_trends.map((t) => (
                      <li key={t.panel} className="row row--between">
                        <span className="small" style={{ fontWeight: 500 }}>{titleCase(t.panel)}</span>
                        <span className="row">
                          {t.points.map((p) => <span key={p.at} className={p.flag ? "pill pill--rose num" : "pill num"}>{p.value}</span>)}
                        </span>
                      </li>
                    ))}
                  </ul>
                )}
              </Card>
              <Card title="Recent check-ins">
                <ul className="list">
                  {r.checkins.map((c) => (
                    <li key={c.at} className="row row--between">
                      <span className="small num">{localTime(c.at)}</span>
                      <span className="row">
                        <span className="pill">{SLEEP[c.sleep] ?? c.sleep}</span>
                        <span className={c.feeling === "good" ? "pill pill--mint" : "pill pill--sand"}>{titleCase(c.feeling)}</span>
                        {!c.hydration_ok && <span className="pill pill--sand">Low water</span>}
                      </span>
                    </li>
                  ))}
                </ul>
              </Card>
            </div>
            <div className="stack">
              <OutcomeForm personId={r.person_id} />
              <Card title="Outcome history">
                <ul className="list">
                  {r.outcomes.map((o) => (
                    <li key={o.at} className="stack stack--tight">
                      <span className="row row--between"><strong className="small">{titleCase(o.outcome)}</strong><span className="xsmall muted num">{localTime(o.at)}</span></span>
                      {o.restriction && <span className="small muted">{o.restriction}</span>}
                      <span className="xsmall muted">{o.shared ? "Shared with the employer" : "Not shared with the employer"}{o.by ? ` · ${o.by}` : ""}</span>
                    </li>
                  ))}
                </ul>
              </Card>
            </div>
          </div>
        </Page>
      )}
    </Loaded>
  );
}

function OutcomeForm({ personId }: { personId: number }) {
  const [outcome, setOutcome] = useState<string>();
  const [restriction, setRestriction] = useState("");
  const [share, setShare] = useState("yes");
  const save = useSend<{ outcome: string; restriction_text: string; share_with_employer: boolean }>("POST", `/api/health/workers/${personId}/outcome`);
  const toast = useToast();
  return (
    <Card title="Fitness outcome" subtitle="You have the final word on health. The planner sees only the outcome.">
      <div className="stack">
        <Field label="Outcome">
          {(p) => (
            <Select {...p} value={outcome} onValueChange={setOutcome} placeholder="Choose" options={[
              { value: "fit", label: "Fit" },
              { value: "fit_with_restrictions", label: "Fit with restrictions" },
              { value: "not_today", label: "Not today" },
            ]} />
          )}
        </Field>
        {outcome === "fit_with_restrictions" && (
          <Field label="Restriction">{(p) => <TextArea {...p} rows={2} value={restriction} onChange={(e) => setRestriction(e.target.value)} />}</Field>
        )}
        <Field label="The worker's choice" hint="The worker decides whether the employer sees this outcome.">
          {(p) => <Select {...p} value={share} onValueChange={setShare} options={[{ value: "yes", label: "Share the outcome with the employer" }, { value: "no", label: "Do not share" }]} />}
        </Field>
        <Button variant="primary" disabled={!outcome} busy={save.isPending} onClick={() => save.mutate({ outcome: outcome!, restriction_text: restriction, share_with_employer: share === "yes" }, { onSuccess: () => toast({ title: "Outcome recorded", tone: "good" }), onError: (e) => toast({ title: "Not saved", body: e.message, tone: "critical" }) })}>
          Record outcome
        </Button>
      </div>
    </Card>
  );
}
