import { Radar } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useGet, useSend } from "../api/hooks";
import { Page } from "../layout/AppShell";
import { localTime } from "../layout/Meta";
import { Button } from "../ui/Button";
import { Card } from "../ui/Card";
import { EmptyState } from "../ui/EmptyState";
import { Table, type Column } from "../ui/Table";
import { useToast } from "../ui/Toast";
import { Loaded, titleCase } from "./common";
import "./pages.css";
import "./warnings.css";

type Zone = { zone: string; kind: string; level: string; index: number; classes: string[]; late_feeds: string[] };
type Summary = { id: number; zone: string; level: string; status: string; outcome: string | null; opened_at: string; closed_at: string | null; classes: string[]; steps_drafted: number; steps_confirmed: number };
type Listing = { day: string; zones: Zone[]; open: Summary[]; closed: Summary[] };

const KIND_ORDER = ["camp_block", "berth", "yard_block", "district"];
const KIND_LABEL: Record<string, string> = { camp_block: "Workers' village", berth: "Berths", yard_block: "Yard and workshop", district: "Districts" };
const OUTCOME: Record<string, string> = { right: "Right", early: "Early", false_alarm: "False alarm", missed: "Missed" };

export function Warnings() {
  const listing = useGet<Listing>("/api/warnings");
  const scan = useSend<Record<string, never>, { opened: number[] }>("POST", "/api/warnings/scan");
  const toast = useToast();
  const navigate = useNavigate();
  const columns: Column<Summary>[] = [
    { key: "zone", header: "Place", render: (w) => <strong>{w.zone}</strong> },
    { key: "opened", header: "Opened", render: (w) => localTime(w.opened_at) },
    { key: "classes", header: "Signal classes", render: (w) => w.classes.map(titleCase).join(" and ") },
    { key: "outcome", header: "Outcome", render: (w) => <span className={w.outcome === "false_alarm" ? "pill pill--sand" : "pill pill--mint"}>{OUTCOME[w.outcome ?? ""] ?? ""}</span> },
  ];
  return (
    <Page
      title="Early warnings"
      subtitle="Each place against its own baseline. Nothing goes above Watch unless two different kinds of signal agree."
      actions={
        <Button icon={<Radar />} busy={scan.isPending} onClick={() => scan.mutate({}, { onSuccess: (r) => toast({ title: r.opened.length ? `${r.opened.length} new warning record(s)` : "No new warnings", tone: r.opened.length ? "warning" : "good" }) })}>
          Run the detector now
        </Button>
      }
    >
      <Loaded query={listing}>
        {(data) => {
          const late = [...new Set(data.zones.flatMap((z) => z.late_feeds))];
          return (
          <div className="stack">
            <Card title="Site map" subtitle={`Deviation from each place's own baseline, day ending ${data.day}`}>
              <div className="stack">
                {late.length > 0 && (
                  <p className="late-banner small" role="status">
                    Late: {late.join(", ")}. Places that rely on {late.length === 1 ? "this feed" : "these feeds"} are shown one level lower until it catches up.
                  </p>
                )}
                {KIND_ORDER.map((kind) => (
                  <div key={kind} className="stack stack--tight">
                    <span className="section-title">{KIND_LABEL[kind]}</span>
                    <div className="zones">
                      {data.zones
                        .filter((z) => z.kind === kind)
                        .map((z) => (
                          <div key={z.zone} className={`zone zone--${z.level}`} title={z.classes.length ? `Signals up: ${z.classes.join(", ")}` : "Within baseline"}>
                            <span className="zone__name">{z.zone}</span>
                            <span className="zone__level">{titleCase(z.level)}</span>
                            {z.late_feeds.length > 0 && <span className="zone__late">Late: {z.late_feeds.join(", ")}</span>}
                          </div>
                        ))}
                    </div>
                  </div>
                ))}
              </div>
            </Card>
            <Card title="Open warning records">
              {data.open.length === 0 ? (
                <EmptyState title="No open warnings" />
              ) : (
                <div className="stack stack--tight">
                  {data.open.map((w) => (
                    <button key={w.id} type="button" className="warning-open" onClick={() => navigate(`/warnings/${w.id}`)}>
                      <span className="warning-open__mark" aria-hidden="true" />
                      <span className="stack stack--tight" style={{ flex: 1 }}>
                        <span className="warning-open__title">{w.zone}</span>
                        <span className="small muted">
                          Opened {localTime(w.opened_at)} · {w.classes.map(titleCase).join(" and ")} signals agree · {w.steps_confirmed} of 10 sections confirmed, {w.steps_drafted} drafted
                        </span>
                      </span>
                      <span className="pill pill--rose">{titleCase(w.level)}</span>
                    </button>
                  ))}
                </div>
              )}
            </Card>
            <Card title="Closed records" subtitle="Every record closes with an outcome. That is how lead time and false alarms are measured." flush>
              <Table caption="Closed warnings" columns={columns} rows={data.closed} rowKey={(w) => String(w.id)} onRowClick={(w) => navigate(`/warnings/${w.id}`)} />
            </Card>
          </div>
          );
        }}
      </Loaded>
    </Page>
  );
}
