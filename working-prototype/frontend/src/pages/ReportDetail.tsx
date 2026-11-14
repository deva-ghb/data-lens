import { ArrowLeft } from "lucide-react";
import { Link, useParams } from "react-router-dom";
import { toDraft, useGet, useSend, type ApiDraft } from "../api/hooks";
import { Page } from "../layout/AppShell";
import { localTime } from "../layout/Meta";
import { AiSection } from "../ui/AiSection";
import { Card } from "../ui/Card";
import { useToast } from "../ui/Toast";
import { Loaded, pct, titleCase } from "./common";
import "./pages.css";
import "./report.css";

type Detail = {
  kind: string; id: number; at: string; zone: string; activity: string | null; text: string; status: string; reported_by: string | null;
  photo_url: string | null;
  triage: { type: string | null; type_confidence: number | null } | null;
  photo_checks: Record<string, number | null>;
  risk: { likelihood: number; severity: number; score: number } | null;
  record: ApiDraft;
};

const CHECKS: Record<string, string> = { harness_not_clipped: "Harness not clipped at height", person_under_load: "Person under a suspended load", missing_ppe: "Hard hat or vest missing" };
const KIND: Record<string, string> = { near_miss: "Near miss", incident: "Incident", hazard: "Hazard report" };

function band(score: number): string {
  return score >= 15 ? "red" : score >= 8 ? "amber" : "green";
}

export function ReportDetail() {
  const { kind, reportId } = useParams();
  const report = useGet<Detail>(`/api/incidents/${kind}/${reportId}`);
  const confirm = useSend<{ content: string }>("POST", `/api/incidents/${kind}/${reportId}/confirm`);
  const toast = useToast();
  return (
    <Loaded query={report}>
      {(r) => (
        <Page
          title={`${KIND[r.kind]} at ${r.zone}`}
          subtitle={`Reported ${localTime(r.at)}${r.reported_by ? ` by ${r.reported_by}` : ""}${r.activity ? `, ${r.activity.toLowerCase()}` : ""}`}
          actions={<Link to="/reports" className="link row"><ArrowLeft size={16} aria-hidden="true" /> All reports</Link>}
        >
          <div className="grid grid--main-side">
            <div className="stack">
              <Card title="What the reporter said">
                <p className="prose">{r.text}</p>
                {r.photo_url && <img className="report__photo" src={r.photo_url} alt="Photo taken by the reporter" />}
              </Card>
              {r.status === "closed" ? (
                <Card title="Confirmed record"><p className="prose small">{r.record.content}</p></Card>
              ) : (
                <AiSection
                  draft={toDraft(r.record)!}
                  title="The record, drafted by the copilot"
                  confirmLabel="Confirm the record"
                  busy={confirm.isPending}
                  onEdit={() => undefined}
                  onConfirm={(content) => confirm.mutate({ content }, { onSuccess: () => toast({ title: "Record confirmed", body: "It now counts in the activity's safety history.", tone: "good" }) })}
                />
              )}
            </div>
            <div className="stack">
              <Card title="Triage" subtitle="Typed answers from the Decisions API">
                {r.triage ? (
                  <dl className="kv">
                    <dt>Type</dt>
                    <dd>{titleCase(r.triage.type ?? "unknown")} {r.triage.type_confidence !== null && <span className="muted">({pct(r.triage.type_confidence)} sure)</span>}</dd>
                  </dl>
                ) : <p className="small muted">Triage was not available. A person classifies this report.</p>}
              </Card>
              {r.risk && (
                <Card title="Risk on the site matrix">
                  <div className="matrix" role="img" aria-label={`Likelihood ${r.risk.likelihood}, severity ${r.risk.severity}, score ${r.risk.score}`}>
                    {[5, 4, 3, 2, 1].map((s) =>
                      [1, 2, 3, 4, 5].map((l) => (
                        <span key={`${s}-${l}`} className={`matrix__cell matrix__cell--${band(s * l)}${s === r.risk!.severity && l === r.risk!.likelihood ? " matrix__cell--on" : ""}`}>
                          {s === r.risk!.severity && l === r.risk!.likelihood ? s * l : ""}
                        </span>
                      )),
                    )}
                  </div>
                  <p className="xsmall muted">Severity up, likelihood across. Classified by potential, not outcome.</p>
                </Card>
              )}
              {Object.keys(r.photo_checks).length > 0 && (
                <Card title="Photo checks" subtitle="What the photo shows, checked by the Decisions API">
                  <ul className="list">
                    {Object.entries(r.photo_checks).map(([k, p]) => (
                      <li key={k} className="row row--between">
                        <span className="small">{CHECKS[k] ?? k}</span>
                        <span className={(p ?? 0) >= 0.5 ? "pill pill--rose" : "pill pill--mint"}>{p === null ? "No answer" : (p ?? 0) >= 0.5 ? `Likely (${pct(p)})` : `Unlikely (${pct(p)})`}</span>
                      </li>
                    ))}
                  </ul>
                </Card>
              )}
            </div>
          </div>
        </Page>
      )}
    </Loaded>
  );
}
