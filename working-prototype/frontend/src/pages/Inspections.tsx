import { Check, X } from "lucide-react";
import { useState } from "react";
import { useGet, useSend } from "../api/hooks";
import { Page } from "../layout/AppShell";
import { localTime } from "../layout/Meta";
import { Button } from "../ui/Button";
import { Card } from "../ui/Card";
import { EmptyState } from "../ui/EmptyState";
import { Input } from "../ui/Field";
import { useToast } from "../ui/Toast";
import { Loaded, pct, titleCase } from "./common";
import "./pages.css";

type Check_ = { id: number; driver: string; question: string; result: string | null; note: string | null };
type Inspection = { id: number; status: string; due_at: string; zone: string; source_kind: string; source_id: number; checks: Check_[] };

export function Inspections() {
  const list = useGet<Inspection[]>("/api/inspections");
  return (
    <Page title="Inspections" subtitle="Built from a warning's drivers: one check per driver, where and when the driver acts. Results raise or lower the warning's confidence.">
      <Loaded query={list}>
        {(rows) =>
          rows.length === 0 ? <Card><EmptyState title="No inspections yet" /></Card> : (
            <div className="stack">
              {rows.map((i) => (
                <Card key={i.id} title={`${i.zone}`} subtitle={`Due ${localTime(i.due_at)} · from ${i.source_kind} ${i.source_id}`} actions={<span className={i.status === "done" ? "pill pill--mint" : "pill pill--periwinkle"}>{titleCase(i.status)}</span>}>
                  <ul className="list">
                    {i.checks.map((c) => <CheckRow key={c.id} inspectionId={i.id} check={c} />)}
                  </ul>
                </Card>
              ))}
            </div>
          )
        }
      </Loaded>
    </Page>
  );
}

function CheckRow({ inspectionId, check }: { inspectionId: number; check: Check_ }) {
  const [note, setNote] = useState("");
  const toast = useToast();
  const save = useSend<{ result: string; note: string }, { note_confirms: number | null }>("POST", `/api/inspections/${inspectionId}/checks/${check.id}`);
  const record = (result: string) =>
    save.mutate({ result, note }, { onSuccess: (r) => toast({ title: "Check recorded", body: r.note_confirms !== null ? `The note reads as ${pct(r.note_confirms)} confirming the driver.` : undefined, tone: "good" }) });
  return (
    <li className="stack stack--tight">
      <span className="small" style={{ fontWeight: 500 }}>{check.question}</span>
      {check.result ? (
        <span className="small muted">{check.result === "confirmed" ? "Confirmed on the ground" : "Not found"}{check.note ? `: ${check.note}` : ""}</span>
      ) : (
        <div className="row" style={{ flexWrap: "nowrap" }}>
          <Input aria-label="What you saw" placeholder="What you saw" value={note} onChange={(e) => setNote(e.target.value)} style={{ flex: 1 }} />
          <Button size="sm" variant="ghost" icon={<X />} onClick={() => record("not_found")}>Not found</Button>
          <Button size="sm" variant="secondary" icon={<Check />} busy={save.isPending} onClick={() => record("confirmed")}>Confirmed</Button>
        </div>
      )}
    </li>
  );
}
