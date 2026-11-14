import { CheckCircle2, ThermometerSun } from "lucide-react";
import { useGet, useSend } from "../../api/hooks";
import { localTime } from "../../layout/Meta";
import { Button } from "../../ui/Button";
import { useToast } from "../../ui/Toast";
import { Loaded } from "../common";
import "../pages.css";

type Foreman = { gangs: string[]; shift: { label: string } | null; crew: { name: string; task: string; gang: string }[]; actions: string[]; pending: { id: number; permit: string; text: string; at: string }[] };

export function ForemanHome() {
  const view = useGet<Foreman>("/api/phone/foreman", { refetchInterval: 10_000 });
  return (
    <Loaded query={view}>
      {(v) => (
        <>
          <div className="stack stack--tight">
            <span className="small muted">{v.gangs.join(", ")}</span>
            <h1 className="phone-title">{v.shift?.label ?? "Tonight"}</h1>
          </div>
          {v.pending.map((p) => <Pending key={p.id} item={p} />)}
          {v.actions.length > 0 && (
            <div className="phone-card phone-card--tint">
              <strong>For your crew tonight</strong>
              {v.actions.map((a) => <span key={a} className="small">{a}</span>)}
            </div>
          )}
          <div className="phone-card">
            <strong>Crew ({v.crew.length})</strong>
            <ul className="list">
              {v.crew.map((c) => (
                <li key={c.name} className="row row--between">
                  <span className="small">{c.name}</span>
                  <span className="xsmall muted">{c.task}</span>
                </li>
              ))}
            </ul>
          </div>
        </>
      )}
    </Loaded>
  );
}

function Pending({ item }: { item: Foreman["pending"][number] }) {
  const confirm = useSend<Record<string, never>>("POST", `/api/phone/foreman/confirm/${item.id}`);
  const toast = useToast();
  return (
    <div className="phone-card phone-card--rose">
      <span className="row"><ThermometerSun size={18} aria-hidden="true" /><strong>Deck heat limit crossed</strong></span>
      <span className="small">{item.text}</span>
      <span className="xsmall muted">{item.permit} · {localTime(item.at)}</span>
      <Button variant="primary" block icon={<CheckCircle2 />} busy={confirm.isPending} onClick={() => confirm.mutate({}, { onSuccess: () => toast({ title: "Confirmed. The permit log has it.", tone: "good" }) })} style={{ minHeight: 52 }}>
        Confirm the change
      </Button>
    </div>
  );
}
