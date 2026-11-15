import { ArrowRight, CloudSun, Gauge, RefreshCw, Search, TriangleAlert } from "lucide-react";
import { useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useGet, useSend } from "../api/hooks";
import { useMe } from "../auth/useMe";
import { Page } from "../layout/AppShell";
import { localTime } from "../layout/Meta";
import { Button } from "../ui/Button";
import { Card } from "../ui/Card";
import { Dialog } from "../ui/Dialog";
import { EmptyState } from "../ui/EmptyState";
import { Field, Input } from "../ui/Field";
import { Select } from "../ui/Select";
import { Table, type Column } from "../ui/Table";
import { TextArea } from "../ui/TextArea";
import { TIER_LOOK, TierChip, type Tier } from "../ui/TierChip";
import { useToast } from "../ui/Toast";
import { Loaded, pct, titleCase } from "./common";
import "./pages.css";
import "./roster.css";

export type RosterRow = {
  assignment_id: number;
  worker: string;
  employer: string;
  gang: string | null;
  activity: string;
  grade: number;
  zone: string | null;
  source: string;
  tier: Tier | "not_scored" | null;
  r: number | null;
  reason: string;
  confidence: number | null;
  swap: { id: number; status: string; to: string; reason: string | null } | null;
  contest: { id: number; status: string; text: string } | null;
};

type RosterData = {
  shift: { id: number; label: string };
  run: { id: number; kind: string; ran_at: string; conditions_source: string } | null;
  tier_counts: Record<Tier, number>;
  budget: { limit: number; shown: number; rolled_into_brief: number };
  crew_rule_breaches: { gang: string | null; activity: string | null; rule: string; detail: string }[];
  rows: RosterRow[];
};

type Split = { conditions_share: number; crew_share: number; total_excess: number; p10: number; p90: number; peak_wbgt: number | null; forecast_missing: boolean };

const TIERS: Tier[] = ["fit", "fit_with_controls", "reassign", "refer", "unknown"];
const SWAP_WORDS: Record<string, string> = {
  proposed: "Proposed",
  accepted: "Waiting for the shift manager",
  approved: "Approved",
  declined: "Declined",
  rejected: "Rejected by the shift manager",
};

export function Roster() {
  const roster = useGet<RosterData>("/api/roster");
  const [source, setSource] = useState("scenario");
  const run = useSend<{ kind: string; conditions_source: string; shift_id?: number }>("POST", "/api/runs");
  const toast = useToast();

  const score = (kind: string) =>
    run.mutate(
      // A re-score is of the shift on screen; the evening run picks tomorrow night itself.
      { kind, conditions_source: source, shift_id: kind === "manual" ? roster.data?.shift.id : undefined },
      {
        onSuccess: () => toast({ title: "Roster scored", body: source === "live" ? "Using today's live Abu Dhabi forecast." : "Using the scenario forecast.", tone: "good" }),
        onError: (e) => toast({ title: "Scoring failed", body: e.message, tone: "critical" }),
      },
    );

  return (
    <Page
      title="Assignment risk"
      subtitle="Tomorrow's roster, scored before the shift. Reasons are in work terms; health detail never appears here."
      wide
      actions={
        <>
          <Select
            aria-label="Conditions"
            value={source}
            onValueChange={setSource}
            options={[
              { value: "scenario", label: "Scenario forecast", hint: "The summer story" },
              { value: "live", label: "Live Abu Dhabi forecast", hint: "Pulled hourly from Open-Meteo" },
            ]}
            className="roster__source"
          />
          <Button variant="secondary" icon={<RefreshCw />} busy={run.isPending && run.variables?.kind === "manual"} onClick={() => score("manual")}>
            Re-score now
          </Button>
          <Button variant="primary" icon={<Gauge />} busy={run.isPending && run.variables?.kind === "evening"} onClick={() => score("evening")}>
            Score tomorrow's roster
          </Button>
        </>
      }
    >
      <Loaded query={roster} lines={10}>
        {(data) =>
          data.run === null ? (
            <Card>
              <EmptyState
                title={`${data.shift.label} has not been scored yet`}
                body="The engine reads the roster, check-ins, the forecast, the camp and the safety records, then scores every graded assignment."
                action={<Button variant="primary" icon={<Gauge />} onClick={() => score("evening")} busy={run.isPending}>Score tomorrow's roster</Button>}
              />
            </Card>
          ) : (
            <RosterBody data={data} />
          )
        }
      </Loaded>
    </Page>
  );
}

const PAGE = 25;

type Breach = RosterData["crew_rule_breaches"][number];
type RuleGroup = { rule: string; limit: string; breaches: (Breach & { fact: string })[] };

/** One card per crew rule: the limit once as the subtitle, then one line per crew over it.
 *  The server's detail reads "<fact>; <limit>". */
function groupBreaches(breaches: Breach[]): RuleGroup[] {
  const groups = new Map<string, RuleGroup>();
  for (const b of breaches) {
    const [fact = b.detail, limit = ""] = b.detail.split("; ");
    const group = groups.get(b.rule) ?? { rule: b.rule, limit, breaches: [] };
    group.breaches.push({ ...b, fact });
    groups.set(b.rule, group);
  }
  return [...groups.values()];
}

function RosterBody({ data }: { data: RosterData }) {
  const navigate = useNavigate();
  const [tier, setTier] = useState<string>("all");
  const [query, setQuery] = useState("");
  const split = useGet<Split>(`/api/risk-split?shift_id=${data.shift.id}`);
  const scored = data.rows.filter((r) => r.tier && r.tier !== "not_scored");
  const recommendations = data.rows.filter((r) => r.tier === "reassign");
  const rows = useMemo(
    () =>
      scored.filter(
        (r) =>
          (tier === "all" || r.tier === tier) &&
          (query.trim() === "" || `${r.worker} ${r.gang ?? ""} ${r.activity}`.toLowerCase().includes(query.trim().toLowerCase())),
      ),
    [scored, tier, query],
  );

  const [shown, setShown] = useState(PAGE);
  const visible = rows.slice(0, shown);
  const ruleGroups = useMemo(() => groupBreaches(data.crew_rule_breaches), [data.crew_rule_breaches]);

  const columns: Column<RosterRow>[] = [
    { key: "worker", header: "Worker", render: (r) => <span className="roster__worker">{r.worker}<span className="xsmall muted">{r.employer}</span></span>, width: "22%" },
    { key: "gang", header: "Gang", render: (r) => r.gang ?? "None", width: "12%" },
    { key: "activity", header: "Work", render: (r) => <span>{r.activity}{r.source === "swap" && <span className="pill pill--mint roster__swapped">Swapped</span>}</span>, width: "22%" },
    { key: "tier", header: "Tier", render: (r) => (r.tier && r.tier !== "not_scored" ? <TierChip tier={r.tier} /> : null), width: "16%" },
    { key: "r", header: "Relative risk", numeric: true, render: (r) => (r.r !== null ? r.r.toFixed(2) : ""), width: "10%" },
    { key: "reason", header: "Why", render: (r) => <span className="small muted roster__reason">{r.reason}</span> },
  ];

  return (
    <div className="stack">
      <div className="row row--between">
        <div className="row">
          <span className="pill pill--periwinkle">{data.shift.label}</span>
          <span className="small muted">
            Scored {localTime(data.run!.ran_at)} site time, {data.run!.kind === "evening" ? "evening run" : data.run!.kind === "shift_start" ? "shift-start re-score" : "manual re-score"},{" "}
            {data.run!.conditions_source === "live" ? "live forecast" : "scenario forecast"}
          </span>
        </div>
      </div>
      <div className="tier-tiles">
        {TIERS.map((t) => (
          <button key={t} type="button" className={`tier-tile tier-tile--${t}`} aria-pressed={tier === t} onClick={() => { setTier(tier === t ? "all" : t); setShown(PAGE); }}>
            <span className="tier-tile__label">{TIER_LOOK[t].label}</span>
            <span className="tier-tile__value num">{data.tier_counts[t] ?? 0}</span>
          </button>
        ))}
      </div>
      <div className="grid grid--main-side">
        <Card
          title="Reassign today: recommendations"
          subtitle={`At most ${data.budget.limit} per shift. ${data.budget.rolled_into_brief > 0 ? `${data.budget.rolled_into_brief} more rolled into your brief.` : "Nothing rolled over."}`}
        >
          {recommendations.length === 0 ? (
            <EmptyState title="No reassignments for this shift" body="Every worker on graded work is within the activity's demands, or on extra controls." />
          ) : (
            <div className="stack stack--tight">
              {recommendations.map((r) => (
                <Recommendation key={r.assignment_id} row={r} />
              ))}
            </div>
          )}
        </Card>
        <div className="stack">
          <SplitCard split={split.data} />
          {ruleGroups.map((g) => (
            <Card key={g.rule} title={`Crew rules: ${g.breaches.length} ${g.breaches.length === 1 ? "crew" : "crews"} over`} subtitle={titleCase(g.limit)}>
              <ul className="list">
                {g.breaches.map((b) => (
                  <li key={`${b.gang}-${b.activity}`} className="crew-rule">
                    <TriangleAlert size={16} className="roster__warn" aria-hidden="true" />
                    <span className="crew-rule__text">
                      <span className="crew-rule__gang">
                        {b.gang} <span className="muted">· {b.activity}</span>
                      </span>
                      <span className="small num">{b.fact}</span>
                    </span>
                  </li>
                ))}
              </ul>
            </Card>
          ))}
        </div>
      </div>
      <Card
        title="Everyone on graded work"
        subtitle={`${rows.length === scored.length ? `${scored.length} scored` : `${rows.length} of ${scored.length} match`}. Select a worker to see how the score is built.`}
        actions={
          <div className="row roster__filters">
            <div className="roster__search">
              <Search size={16} aria-hidden="true" />
              <Input aria-label="Search workers" placeholder="Search name, gang or work" value={query} onChange={(e) => { setQuery(e.target.value); setShown(PAGE); }} />
            </div>
            <Select
              aria-label="Filter by tier"
              value={tier}
              onValueChange={(v) => { setTier(v); setShown(PAGE); }}
              options={[{ value: "all", label: "All tiers" }, ...TIERS.map((t) => ({ value: t, label: TIER_LOOK[t].label }))]}
            />
          </div>
        }
        flush
      >
        <Table caption="Scored assignments" columns={columns} rows={visible} rowKey={(r) => String(r.assignment_id)} onRowClick={(r) => navigate(`/roster/${r.assignment_id}`)} emptyText="Nobody matches these filters." />
        {rows.length > shown && (
          <div className="table-more">
            <span className="small muted">
              Showing {visible.length} of {rows.length}
            </span>
            <Button variant="secondary" onClick={() => setShown(shown + PAGE)}>
              Show {Math.min(PAGE, rows.length - shown)} more
            </Button>
          </div>
        )}
      </Card>
    </div>
  );
}

function Recommendation({ row }: { row: RosterRow }) {
  const toast = useToast();
  // Only the planner decides a swap; everyone else who sees the roster reads it.
  const decides = useMe().data?.role === "planner";
  const accept = useSend<{ reason?: string }>("POST", `/api/swaps/${row.swap?.id ?? 0}/accept`);
  const keep = useSend<{ reason: string }>("POST", `/api/assignments/${row.assignment_id}/keep`);
  const resolve = useSend<{ status: string; note: string }>("POST", `/api/contests/${row.contest?.id ?? 0}/resolve`);
  const [open, setOpen] = useState(false);
  const [reason, setReason] = useState("");
  const status = row.swap?.status ?? "none";
  const pending = status === "proposed" || status === "none";
  return (
    <div className="rec">
      <div className="rec__head">
        <div className="stack stack--tight">
          <Link to={`/roster/${row.assignment_id}`} className="rec__name">
            {row.worker}
          </Link>
          <span className="small muted">
            {row.gang} · {row.activity} · relative risk <span className="num">{row.r?.toFixed(2)}</span>
          </span>
        </div>
        <TierChip tier="reassign" />
      </div>
      <p className="small">{row.reason}</p>
      {row.swap && row.swap.to !== row.activity ? (
        <div className="rec__swap">
          <ArrowRight size={16} aria-hidden="true" />
          <span className="small">
            Proposed: <strong>{row.swap.to}</strong> tonight, same crew
          </span>
        </div>
      ) : (
        status === "none" && <p className="small muted">No lower-hazard work fits within the crew rules. Keep with controls, or move by hand.</p>
      )}
      {row.contest && (
        <div className="rec__contest">
          <span className="pill pill--sand">{row.contest.status === "open" ? "Contested by the worker" : `Contest ${row.contest.status}`}</span>
          <p className="xsmall muted">“{row.contest.text}”</p>
          {row.contest.status === "open" && decides && (
            <div className="row">
              <Button size="sm" variant="ghost" busy={resolve.isPending} onClick={() => resolve.mutate({ status: "dismissed", note: "The change stands for tonight." })}>Dismiss</Button>
              <Button size="sm" variant="secondary" busy={resolve.isPending} onClick={() => resolve.mutate({ status: "upheld", note: "Kept on the work with a buddy and extra breaks." })}>Uphold</Button>
            </div>
          )}
        </div>
      )}
      <div className="row row--between">
        <span className="xsmall muted">{status === "none" ? (decides ? "Waiting for you" : "Waiting for the planner") : SWAP_WORDS[status] ?? status}</span>
        {pending && decides && (
          <div className="row">
            <Button size="sm" variant="ghost" onClick={() => setOpen(true)}>
              Keep with controls
            </Button>
            {row.swap && <Button
              size="sm"
              variant="primary"
              busy={accept.isPending}
              onClick={() =>
                accept.mutate({}, { onSuccess: () => toast({ title: "Swap accepted", body: "Sent to the shift manager to approve.", tone: "good" }) })
              }
            >
              Accept swap
            </Button>}
          </div>
        )}
      </div>
      <Dialog
        open={open}
        onOpenChange={setOpen}
        title={`Keep ${row.worker} on ${row.activity.toLowerCase()}?`}
        description="Your reason is logged. The worker stays on tonight's work with the controls in the permit."
        footer={
          <>
            <Button variant="ghost" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="danger"
              disabled={!reason.trim()}
              busy={keep.isPending}
              onClick={() => keep.mutate({ reason: reason.trim() }, { onSuccess: () => { setOpen(false); toast({ title: "Kept with controls", body: "Logged with your reason.", tone: "neutral" }); } })}
            >
              Keep with controls
            </Button>
          </>
        }
      >
        <Field label="Reason">
          {(p) => <TextArea {...p} rows={3} value={reason} onChange={(e) => setReason(e.target.value)} placeholder="For example: he is the only certified lasher left for bay 30." />}
        </Field>
      </Dialog>
    </div>
  );
}

function SplitCard({ split }: { split: Split | undefined }) {
  return (
    <Card title="Tonight's risk: conditions or crew?" subtitle="Where the risk above baseline comes from">
      {!split ? (
        <span className="small muted">Working it out…</span>
      ) : (
        <div className="stack">
          <div className="split" role="img" aria-label={`Conditions ${pct(split.conditions_share)}, crew ${pct(split.crew_share)}`}>
            <span className="split__conditions" style={{ width: pct(split.conditions_share) }}>
              <CloudSun size={14} aria-hidden="true" /> Conditions {pct(split.conditions_share)}
            </span>
            <span className="split__crew" style={{ width: pct(split.crew_share) }}>
              Crew {pct(split.crew_share)}
            </span>
          </div>
          <p className="small muted">
            {split.conditions_share >= 0.5
              ? "Mostly the shift itself: heat, night and the camp. Moving the work window does more than swapping people."
              : "Mostly the crew. Swapping workers does more than moving the window."}
          </p>
          <dl className="kv">
            <dt>Peak forecast WBGT</dt>
            <dd className="num">{split.forecast_missing ? "No forecast" : `${split.peak_wbgt?.toFixed(1)} °C`}</dd>
            <dt>Excess risk, 80% band</dt>
            <dd className="num">
              {split.p10.toFixed(1)} to {split.p90.toFixed(1)}
            </dd>
          </dl>
        </div>
      )}
    </Card>
  );
}
