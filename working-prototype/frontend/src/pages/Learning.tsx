import { useGet, useSend } from "../api/hooks";
import { Button } from "../ui/Button";
import { Page } from "../layout/AppShell";
import { Card } from "../ui/Card";
import { EmptyState } from "../ui/EmptyState";
import { Loaded } from "./common";
import "./pages.css";

type Item = { id: number; kind: string; status: string; source_kind: string; source_id: number; content: string; reads: number; reads_by_crew: { crew: string; reads: number | null }[] };
const KIND: Record<string, string> = { card: "One-minute card", toolbox_talk: "Toolbox talk", swp_change: "Proposed practice change" };

export function Learning() {
  const learning = useGet<{ threshold: number; items: Item[] }>("/api/learning");
  return (
    <Page title="Learning" subtitle="Cards, toolbox talks and proposed changes to safe working practice, written only from confirmed sections.">
      <Loaded query={learning}>
        {(data) =>
          data.items.length === 0 ? <Card><EmptyState title="No learning items yet" /></Card> : (
            <div className="grid grid--3">
              {data.items.map((i) => (
                <Card key={i.id} title={KIND[i.kind] ?? i.kind} subtitle={`From warning ${i.source_id} · ${i.status === "draft" ? "not shared yet" : `read ${i.reads} times`}`} actions={i.status === "draft" ? <Share id={i.id} /> : undefined}>
                  <div className="stack">
                    <p className="small prose">{i.content}</p>
                    {i.reads_by_crew.length > 0 && (
                      <div className="stack stack--tight">
                        <span className="section-title">Read by crew</span>
                        <div className="row">
                          {i.reads_by_crew.map((c) => (
                            <span key={c.crew} className="pill">{c.crew}: {c.reads ?? `under ${data.threshold}`}</span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </Card>
              ))}
            </div>
          )
        }
      </Loaded>
    </Page>
  );
}

function Share({ id }: { id: number }) {
  const share = useSend<Record<string, never>>("POST", `/api/learning/${id}/publish`);
  return <Button size="sm" variant="primary" busy={share.isPending} onClick={() => share.mutate({})}>Share with crews</Button>;
}
