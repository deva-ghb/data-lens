import { ArrowRight, MessageCircleQuestion, Sparkles } from "lucide-react";
import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { toDraft, useGet, useSend, type ApiDraft } from "../api/hooks";
import type { Me } from "../auth/useMe";
import { Page } from "../layout/AppShell";
import { Button } from "../ui/Button";
import { Card } from "../ui/Card";
import { EmptyState } from "../ui/EmptyState";
import { ErrorState } from "../ui/ErrorState";
import { Input } from "../ui/Field";
import { BulletList } from "../ui/ReasoningPanel";
import { Skeleton } from "../ui/Skeleton";
import "./pages.css";

type Decision = { title: string; detail: string | null; link: string; tone: "critical" | "warning" | "neutral" };
type HomeData = { role: string; name: string; brief: ApiDraft; decisions: Decision[] };
type Answer = { text: string; declined: boolean; note: string };

function greeting(): string {
  const h = new Date().getHours();
  return h < 12 ? "Good morning" : h < 18 ? "Good afternoon" : "Good evening";
}

export function Home({ me }: { me: Me }) {
  const home = useGet<HomeData>("/api/home", { staleTime: 120_000 });
  const ask = useSend<{ text: string }, Answer>("POST", "/api/home/question");
  const [question, setQuestion] = useState("");
  const brief = toDraft(home.data?.brief);

  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (question.trim()) ask.mutate({ text: question.trim() });
  };

  return (
    <Page title={`${greeting()}, ${me.name.split(" ")[0]}`} subtitle="Your brief for today, and the decisions waiting for you.">
      <div className="grid grid--main-side">
        <div className="stack">
          <Card
            title="Today's brief"
            subtitle="Written by the copilot from what your role can see"
            actions={brief && brief.status !== "unavailable" ? <span className="pill pill--periwinkle"><Sparkles size={14} aria-hidden="true" /> Draft for you</span> : undefined}
          >
            {home.isPending && <Skeleton lines={8} />}
            {home.isError && <ErrorState title="The brief could not be loaded" message={home.error.message} onRetry={() => home.refetch()} />}
            {brief && brief.status === "unavailable" && (
              <EmptyState title="The copilot is not available right now" body="Nothing has been filled in for you. The decisions on the right come straight from the records." />
            )}
            {brief && brief.status !== "unavailable" && (
              <div className="stack">
                <p className="prose">{brief.content}</p>
                <div className="grid grid--2">
                  <div className="stack stack--tight">
                    <span className="section-title">Unsure about</span>
                    <BulletList items={brief.unsure} none="Nothing flagged" />
                  </div>
                  <div className="stack stack--tight">
                    <span className="section-title">Would change this view</span>
                    <BulletList items={brief.would_change} none="Nothing flagged" />
                  </div>
                </div>
              </div>
            )}
          </Card>
          <Card title="Ask the copilot" subtitle="Answers use only the data your role can see. It says so when a question goes beyond that.">
            <form className="question" onSubmit={submit}>
              <Input aria-label="Your question" value={question} onChange={(e) => setQuestion(e.target.value)} placeholder="For example: how many people are in Reassign today tonight?" />
              <Button type="submit" variant="primary" icon={<MessageCircleQuestion />} busy={ask.isPending} disabled={!question.trim()}>
                Ask
              </Button>
            </form>
            {ask.data && (
              <div className={ask.data.declined ? "answer answer--declined" : "answer"} role="status">
                <p className="prose">{ask.data.text}</p>
                {ask.data.note && <p className="small muted">{ask.data.note}</p>}
              </div>
            )}
            {ask.isError && <p className="small" role="alert">{ask.error.message}</p>}
          </Card>
        </div>
        <Card title="Waiting for you" subtitle="At most three, so nothing cries wolf">
          {home.isPending && <Skeleton lines={4} />}
          {home.data && home.data.decisions.length === 0 && <EmptyState title="Nothing waiting" body="When a decision needs you, it appears here." />}
          <div className="stack stack--tight">
            {home.data?.decisions.map((d) => (
              <Link key={d.title} to={d.link} className={`decision decision--${d.tone}`}>
                <span className="decision__mark" aria-hidden="true" />
                <span className="stack stack--tight" style={{ flex: 1 }}>
                  <span className="decision__title">{d.title}</span>
                  {d.detail && <span className="small muted">{d.detail}</span>}
                </span>
                <ArrowRight size={16} aria-hidden="true" className="muted" />
              </Link>
            ))}
          </div>
        </Card>
      </div>
    </Page>
  );
}
