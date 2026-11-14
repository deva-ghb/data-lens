import { ArrowRight, CloudSun, Gauge, RefreshCw, Search, TriangleAlert } from "lucide-react";
import { useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useGet, useSend } from "../api/hooks";
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
import { Loaded, pct } from "./common";
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
  contest: { status: string; text: string } | null;
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
  const run = useSend<{ kind: string; conditions_source: string }>("POST", "/api/runs");
  const toast = useToast();

  const score = (kind: string) =>
    run.mutate(
      { kind, conditions_source: source },
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

function RosterBody({ data }: { data: RosterData }) {
  const navigate = useNavigate();
  const [tier, setTier] = useState<string>("all");
  const [query, setQuery] = useState("");
  const split = useGet<Split>(`/api/risk-split?shift_id=${data.shift.id}`);
  const scored = data.rows.filter((r) => r.tier && r.tier !== "not_scored");
  const recommendations = data.rows.filter((r) => r.swap && r.tier === "reassign");
  const rows = useMemo(
    () =>
      scored.filter(
        (r) =>
          (tier === "all" || r.tier === tier) &&
          (query.trim() === "" || `${r.worker} ${r.gang ?? ""} ${r.activity}`.toLowerCase().includes(query.trim().toLowerCase())),
      ),
    [scored, tier, query],
  );

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
          <button key={t} type="button" className={`tier-tile tier-tile--${t}`} aria-pressed={tier === t} onClick={() => setTier(tier === t ? "all" : t)}>
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
          {data.crew_rule_breaches.length > 0 && (
            <Card title="Crew rules">
              <ul className="list">
                {data.crew_rule_breaches.map((b) => (
                  <li key={`${b.gang}-${b.activity}-${b.rule}`} className="row">
                    <TriangleAlert size={16} className="roster__warn" aria-hidden="true" />
                    <span className="small">
                      <strong>{b.gang}</strong>, {b.activity?.toLowerCase()}: {b.detail}
                    </span>
                  </li>
                ))}
              </ul>
            </Card>
          )}
        </div>
      </div>
      <Card
        title="Everyone on graded work"
        subtitle={`${rows.length} of ${scored.length} shown. Select a worker to see how the score is built.`}
        actions={
          <div className="row roster__filters">
            <div className="roster__search">
              <Search size={16} aria-hidden="true" />
              <Input aria-label="Search workers" placeholder="Search name, gang or work" value={query} onChange={(e) => setQuery(e.target.value)} />
            </div>
            <Select
              aria-label="Filter by tier"
              value={tier}
              onValueChange={setTier}
              options={[{ value: "all", label: "All tiers" }, ...TIERS.map((t) => ({ value: t, label: TIER_LOOK[t].label }))]}
            />
          </div>
        }
        flush
      >
        <Table caption="Scored assignments" columns={columns} rows={rows} rowKey={(r) => String(r.assignment_id)} onRowClick={(r) => navigate(`/roster/${r.assignment_id}`)} emptyText="Nobody matches these filters." />
      </Card>
    </div>
  );
}

function Recommendation({ row }: { row: RosterRow }) {
  const toast = useToast();
  const accept = useSend<{ reason?: string }>("POST", `/api/swaps/${row.swap!.id}/accept`);
  const decline = useSend<{ reason: string }>("POST", `/api/swaps/${row.swap!.id}/decline`);
  const [open, setOpen] = useState(false);
  const [reason, setReason] = useState("");
  const pending = row.swap!.status === "proposed";
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
      <div className="rec__swap">
        <ArrowRight size={16} aria-hidden="true" />
        <span className="small">
          Proposed: <strong>{row.swap!.to}</strong> tonight, same crew
        </span>
        {row.contest && <span className="pill pill--sand">Contested by the worker</span>}
      </div>
      {row.contest && <p className="xsmall muted">“{row.contest.text}”</p>}
      <div className="row row--between">
        <span className="xsmall muted">{SWAP_WORDS[row.swap!.status] ?? row.swap!.status}</span>
        {pending && (
          <div className="row">
            <Button size="sm" variant="ghost" onClick={() => setOpen(true)}>
              Decline
            </Button>
            <Button
              size="sm"
              variant="primary"
              busy={accept.isPending}
              onClick={() =>
                accept.mutate({}, { onSuccess: () => toast({ title: "Swap accepted", body: "Sent to the shift manager to approve.", tone: "good" }) })
              }
            >
              Accept swap
            </Button>
          </div>
        )}
      </div>
      <Dialog
        open={open}
        onOpenChange={setOpen}
        title={`Decline the swap for ${row.worker}?`}
        description="Your reason is logged. The worker keeps tonight's work with the controls in the permit."
        footer={
          <>
            <Button variant="ghost" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="danger"
              disabled={!reason.trim()}
              busy={decline.isPending}
              onClick={() => decline.mutate({ reason: reason.trim() }, { onSuccess: () => { setOpen(false); toast({ title: "Swap declined", tone: "neutral" }); } })}
            >
              Decline swap
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
