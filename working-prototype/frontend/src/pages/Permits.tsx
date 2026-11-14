import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useGet } from "../api/hooks";
import type { Me } from "../auth/useMe";
import { Page } from "../layout/AppShell";
import { Card } from "../ui/Card";
import { EmptyState } from "../ui/EmptyState";
import { StatusDot } from "../ui/StatusDot";
import { TIER_LOOK, type Tier } from "../ui/TierChip";
import { Loaded, titleCase } from "./common";
import "./pages.css";
import "./permits.css";

export type PermitSummary = {
  id: number;
  number: string;
  activity: string;
  grade: number;
  zone: string;
  status: string;
  crew_size: number;
  crew_status: "green" | "amber" | "red" | "unscored";
  readiness: Record<string, number>;
};

const COLUMNS = ["requested", "assessed", "issued", "live", "suspended", "closed"];
export const CREW: Record<"green" | "amber" | "red" | "unscored", { status: "good" | "warning" | "critical" | "neutral"; label: string }> = {
  unscored: { status: "neutral", label: "Crew not scored yet" },
  green: { status: "good", label: "Crew ready" },
  amber: { status: "warning", label: "Crew on controls" },
  red: { status: "critical", label: "Open reassignment" },
};

const BAR: { key: Tier; tone: string }[] = [
  { key: "fit", tone: "good" },
  { key: "fit_with_controls", tone: "warning" },
  { key: "reassign", tone: "critical" },
  { key: "refer", tone: "lilac" },
  { key: "unknown", tone: "neutral" },
];

/** The crew's tiers as one thin bar, with the counts written out beside it. */
function CrewBar({ readiness, size }: { readiness: Record<string, number>; size: number }) {
  const parts = BAR.filter((b) => (readiness[b.key] ?? 0) > 0);
  return (
    <span className="crew-bar">
      <span className="crew-bar__track" aria-hidden="true">
        {parts.map((b) => (
          <span key={b.key} className={`crew-bar__seg crew-bar__seg--${b.tone}`} style={{ flexGrow: readiness[b.key] ?? 0 }} />
        ))}
        {parts.length === 0 && <span className="crew-bar__seg crew-bar__seg--neutral" style={{ flexGrow: Math.max(size, 1) }} />}
      </span>
      <span className="xsmall muted">
        {parts.length === 0 ? "Not scored yet" : parts.map((b) => `${readiness[b.key]} ${TIER_LOOK[b.key].label.toLowerCase()}`).join(" · ")}
      </span>
    </span>
  );
}

export function Permits({ me }: { me: Me }) {
  const board = useGet<{ shift: { label: string }; permits: PermitSummary[] }>("/api/permits");
  const navigate = useNavigate();
  const [stage, setStage] = useState<string>("all");
  return (
    <Page title="Permits to work" subtitle="Each permit carries its crew's readiness as counts. No names appear on a permit.">
      <Loaded query={board}>
        {(data) => {
          const shown = data.permits.filter((p) => stage === "all" || p.status === stage);
          return (
            <div className="stack">
              <div className="row row--between stage-row">
                <span className="pill pill--periwinkle">{data.shift.label}</span>
                <div className="stages" role="group" aria-label="Filter by stage">
                  <button type="button" className="stage" aria-pressed={stage === "all"} onClick={() => setStage("all")}>
                    All <span className="stage__count num">{data.permits.length}</span>
                  </button>
                  {COLUMNS.map((col) => {
                    const n = data.permits.filter((p) => p.status === col).length;
                    return (
                      <button key={col} type="button" className="stage" aria-pressed={stage === col} disabled={n === 0} onClick={() => setStage(stage === col ? "all" : col)}>
                        {titleCase(col)} <span className="stage__count num">{n}</span>
                      </button>
                    );
                  })}
                </div>
              </div>
              {shown.length === 0 ? (
                <Card><EmptyState title="No permits at this stage" body="Pick another stage above." /></Card>
              ) : (
                <div className="permit-grid">
                  {shown.map((p) => (
                    <button key={p.id} type="button" className={`permit-card permit-card--${p.crew_status}`} onClick={() => navigate(`/permits/${p.id}`)}>
                      <span className="permit-card__top">
                        <span className="permit-card__no num">{p.number}</span>
                        <span className="pill">{titleCase(p.status)}</span>
                      </span>
                      <span className="permit-card__work">{p.activity}</span>
                      <span className="xsmall muted">{p.zone} · grade {p.grade} · crew of {p.crew_size}</span>
                      <CrewBar readiness={p.readiness} size={p.crew_size} />
                      <StatusDot status={CREW[p.crew_status].status} label={CREW[p.crew_status].label} />
                    </button>
                  ))}
                </div>
              )}
              {me.role !== "permit_issuer" && <p className="small muted">Only the permit issuer signs, holds or sends back a permit.</p>}
            </div>
          );
        }}
      </Loaded>
    </Page>
  );
}
