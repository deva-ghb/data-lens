import { ArrowRight } from "lucide-react";
import { useState } from "react";
import { useGet, useSend } from "../api/hooks";
import { Page } from "../layout/AppShell";
import { Button } from "../ui/Button";
import { Card } from "../ui/Card";
import { Dialog } from "../ui/Dialog";
import { EmptyState } from "../ui/EmptyState";
import { Field } from "../ui/Field";
import { TextArea } from "../ui/TextArea";
import { useToast } from "../ui/Toast";
import { Loaded } from "./common";
import "./pages.css";
import "./roster.css";

type Swap = { id: number; status: string; worker: string; from: string; to: string; reason: string | null; shift: { label: string }; decided_by: string | null };

export function Swaps() {
  const pending = useGet<Swap[]>("/api/swaps?status=accepted");
  const done = useGet<Swap[]>("/api/swaps");
  return (
    <Page title="Swaps to approve" subtitle="The planner has accepted these reassignments. Each needs your approval before the crew changes.">
      <Loaded query={pending}>
        {(rows) =>
          rows.length === 0 ? (
            <Card>
              <EmptyState title="Nothing to approve" body="Accepted swaps appear here as soon as the planner accepts them." />
            </Card>
          ) : (
            <div className="grid grid--2">
              {rows.map((s) => (
                <SwapCard key={s.id} swap={s} />
              ))}
            </div>
          )
        }
      </Loaded>
      <Card title="Recent decisions">
        <Loaded query={done}>
          {(rows) => (
            <ul className="list">
              {rows
                .filter((s) => ["approved", "rejected", "declined"].includes(s.status))
                .map((s) => (
                  <li key={s.id} className="row row--between">
                    <span className="small">
                      <strong>{s.worker}</strong>: {s.from} <ArrowRight size={12} aria-hidden="true" /> {s.to}
                    </span>
                    <span className={s.status === "approved" ? "pill pill--mint" : "pill pill--sand"}>{s.status}</span>
                  </li>
                ))}
            </ul>
          )}
        </Loaded>
      </Card>
    </Page>
  );
}

function SwapCard({ swap }: { swap: Swap }) {
  const toast = useToast();
  const approve = useSend<{ reason?: string }>("POST", `/api/swaps/${swap.id}/approve`);
  const reject = useSend<{ reason: string }>("POST", `/api/swaps/${swap.id}/reject`);
  const [open, setOpen] = useState(false);
  const [reason, setReason] = useState("");
  return (
    <div className="rec">
      <div className="rec__head">
        <div className="stack stack--tight">
          <span className="rec__name">{swap.worker}</span>
          <span className="small muted">{swap.shift.label}</span>
        </div>
        <span className="pill pill--periwinkle">Accepted by {swap.decided_by ?? "the planner"}</span>
      </div>
      <div className="rec__swap">
        <span className="small">{swap.from}</span>
        <ArrowRight size={16} aria-hidden="true" />
        <strong className="small">{swap.to}</strong>
      </div>
      <p className="small muted">{swap.reason}</p>
      <div className="row" style={{ justifyContent: "flex-end" }}>
        <Button size="sm" variant="ghost" onClick={() => setOpen(true)}>
          Reject
        </Button>
        <Button size="sm" variant="primary" busy={approve.isPending} onClick={() => approve.mutate({}, { onSuccess: () => toast({ title: "Swap approved", body: `${swap.worker} moves to ${swap.to.toLowerCase()} tonight.`, tone: "good" }) })}>
          Approve
        </Button>
      </div>
      <Dialog
        open={open}
        onOpenChange={setOpen}
        title={`Reject the swap for ${swap.worker}?`}
        footer={
          <>
            <Button variant="ghost" onClick={() => setOpen(false)}>Cancel</Button>
            <Button variant="danger" disabled={!reason.trim()} busy={reject.isPending} onClick={() => reject.mutate({ reason: reason.trim() }, { onSuccess: () => setOpen(false) })}>
              Reject swap
            </Button>
          </>
        }
      >
        <Field label="Reason">{(p) => <TextArea {...p} rows={3} value={reason} onChange={(e) => setReason(e.target.value)} />}</Field>
      </Dialog>
    </div>
  );
}
