import { useGet, useSend } from "../api/hooks";
import type { Me } from "../auth/useMe";
import { Page } from "../layout/AppShell";
import { Button } from "../ui/Button";
import { Card } from "../ui/Card";
import { Table, type Column } from "../ui/Table";
import { useToast } from "../ui/Toast";
import { Loaded, titleCase } from "./common";
import "./pages.css";

type Action = { id: number; title: string; control_level: string; owner: string; owner_id: number; due_on: string; status: string; effectiveness_check_on: string | null; effective: boolean | null; source_kind: string; source_id: number };
const LEVEL_TINT: Record<string, string> = { eliminate: "mint", substitute: "sky", engineer: "periwinkle", administrative: "sand", ppe: "rose" };

export function Actions({ me }: { me: Me }) {
  const actions = useGet<Action[]>("/api/actions");
  const columns: Column<Action>[] = [
    { key: "level", header: "Control", render: (a) => <span className={`pill pill--${LEVEL_TINT[a.control_level]}`}>{a.control_level === "ppe" ? "Protective equipment" : titleCase(a.control_level)}</span>, width: 170 },
    { key: "title", header: "Action", render: (a) => <span className="small">{a.title}</span> },
    { key: "owner", header: "Owner", render: (a) => a.owner, width: 150 },
    { key: "due", header: "Due", render: (a) => <span className="num">{a.due_on}</span>, width: 110 },
    { key: "check", header: "Effectiveness check", render: (a) => (a.effective === null ? <span className="small muted">{a.effectiveness_check_on ?? "Not set"}</span> : <span className={a.effective ? "pill pill--mint" : "pill pill--rose"}>{a.effective ? "Worked" : "Did not work"}</span>), width: 170 },
    { key: "status", header: "Status", render: (a) => <ActionStatus action={a} me={me} />, width: 180 },
  ];
  return (
    <Page title="Actions" subtitle="Corrective and preventive actions across warnings and incidents, ranked by the hierarchy of controls. Each has an owner, a due date and an effectiveness check.">
      <Loaded query={actions}>
        {(rows) => (
          <Card flush>
            <Table caption="Actions" columns={columns} rows={rows} rowKey={(a) => String(a.id)} />
          </Card>
        )}
      </Loaded>
    </Page>
  );
}

function ActionStatus({ action, me }: { action: Action; me: Me }) {
  const patch = useSend<{ status?: string; effective?: boolean }>("PATCH", `/api/actions/${action.id}`);
  const toast = useToast();
  const mine = me.id === action.owner_id || me.role === "hse_head";
  if (!mine || action.effective !== null) return <span className="small">{titleCase(action.status)}</span>;
  if (action.status !== "done")
    return <Button size="sm" variant="secondary" busy={patch.isPending} onClick={() => patch.mutate({ status: "done" })}>Mark done</Button>;
  return (
    <Button size="sm" variant="secondary" busy={patch.isPending} onClick={() => patch.mutate({ effective: true }, { onError: (e) => toast({ title: "Not yet", body: e.message, tone: "neutral" }) })}>
      Record it worked
    </Button>
  );
}
