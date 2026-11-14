import { useNavigate } from "react-router-dom";
import { useGet } from "../api/hooks";
import type { Me } from "../auth/useMe";
import { Page } from "../layout/AppShell";
import { Card } from "../ui/Card";
import { EmptyState } from "../ui/EmptyState";
import { StatusDot } from "../ui/StatusDot";
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
  crew_status: "green" | "amber" | "red";
  readiness: Record<string, number>;
};

const COLUMNS = ["requested", "assessed", "issued", "live", "suspended", "closed"];
export const CREW: Record<"green" | "amber" | "red", { status: "good" | "warning" | "critical"; label: string }> = {
  green: { status: "good", label: "Crew ready" },
  amber: { status: "warning", label: "Crew on controls" },
  red: { status: "critical", label: "Open reassignment" },
};

export function Permits({ me }: { me: Me }) {
  const board = useGet<{ shift: { label: string }; permits: PermitSummary[] }>("/api/permits");
  const navigate = useNavigate();
  return (
    <Page title="Permits to work" subtitle="Each permit carries its crew's readiness as counts. No names appear on a permit.">
      <Loaded query={board}>
        {(data) => (
          <div className="stack">
            <span className="pill pill--periwinkle" style={{ alignSelf: "flex-start" }}>{data.shift.label}</span>
            {data.permits.length === 0 ? (
              <Card><EmptyState title="No permits for this shift" /></Card>
            ) : (
              <div className="board">
                {COLUMNS.map((col) => {
                  const items = data.permits.filter((p) => p.status === col);
                  return (
                    <section key={col} className="board__col" aria-label={titleCase(col)}>
                      <header className="board__head">
                        <span>{titleCase(col)}</span>
                        <span className="board__count num">{items.length}</span>
                      </header>
                      {items.map((p) => (
                        <button key={p.id} type="button" className={`permit-card permit-card--${p.crew_status}`} onClick={() => navigate(`/permits/${p.id}`)}>
                          <span className="permit-card__no num">{p.number}</span>
                          <span className="permit-card__work">{p.activity}</span>
                          <span className="xsmall muted">{p.zone} · grade {p.grade} · crew of {p.crew_size}</span>
                          <StatusDot status={CREW[p.crew_status].status} label={CREW[p.crew_status].label} />
                        </button>
                      ))}
                    </section>
                  );
                })}
              </div>
            )}
            {me.role !== "permit_issuer" && <p className="small muted">Only the permit issuer signs, holds or sends back a permit.</p>}
          </div>
        )}
      </Loaded>
    </Page>
  );
}
