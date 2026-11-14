import { Upload } from "lucide-react";
import { useState } from "react";
import { useGet, useSend } from "../api/hooks";
import { Page } from "../layout/AppShell";
import { localTime } from "../layout/Meta";
import { Button } from "../ui/Button";
import { Card } from "../ui/Card";
import { Dialog } from "../ui/Dialog";
import { Field, Input } from "../ui/Field";
import { Select } from "../ui/Select";
import { StatusDot } from "../ui/StatusDot";
import { Table, type Column } from "../ui/Table";
import { useToast } from "../ui/Toast";
import { Loaded, pct, titleCase } from "./common";
import "./pages.css";

type Feed = { code: string; name: string; signal_class: string; cadence_minutes: number; allowed_delay_minutes: number; location_level: string; source: string; readings: number; latest: string | null; age_hours: number | null; late: boolean; live_latest: string | null; live_age_hours: number | null };
type Proposal = { id: string; name: string; ai_available: boolean; columns: { column: string; field: string; free_text: boolean; confidence: number | null }[]; preview: Record<string, string | null>[]; rows: number };

function cadence(min: number): string {
  return min >= 1440 ? "Daily" : min >= 720 ? "Each shift" : min >= 60 ? "Hourly" : `${min} min`;
}

export function Signals() {
  const signals = useGet<{ feeds: Feed[]; live_weather: { ok: boolean; last_success?: string; error?: string } | null }>("/api/signals");
  const [open, setOpen] = useState(false);
  const columns: Column<Feed>[] = [
    { key: "name", header: "Feed", render: (f) => <span className="stack stack--tight"><strong className="small">{f.name}</strong><span className="xsmall muted">{f.source === "uploaded" ? "Connected from a file" : "Located to " + f.location_level}</span></span> },
    { key: "class", header: "Signal class", render: (f) => <span className="pill pill--periwinkle">{titleCase(f.signal_class)}</span>, width: 160 },
    { key: "cadence", header: "Cadence", render: (f) => cadence(f.cadence_minutes), width: 110 },
    { key: "delay", header: "Allowed delay", render: (f) => `${Math.round(f.allowed_delay_minutes / 60)} h`, width: 120 },
    { key: "fresh", header: "Freshness", render: (f) => <StatusDot status={f.late ? "critical" : "good"} label={f.late ? "Late" : f.age_hours !== null ? `${f.age_hours} h old` : "Fresh"} />, width: 140 },
    { key: "live", header: "Live", render: (f) => (f.live_latest ? <span className="small">Live to {localTime(f.live_latest)}</span> : <span className="small muted">Scenario only</span>), width: 170 },
  ];
  return (
    <Page title="Signals" subtitle="Every feed, its class, cadence and freshness. A late feed is named wherever it is used and never filled in silently." actions={<Button variant="primary" icon={<Upload />} onClick={() => setOpen(true)}>Connect a feed</Button>}>
      <Loaded query={signals}>
        {(s) => (
          <div className="stack">
            {s.live_weather && (
              <p className="small">
                Live Abu Dhabi weather: {s.live_weather.ok ? `pulled ${s.live_weather.last_success?.replace("T", " ").slice(0, 16)} UTC` : `last pull failed (${s.live_weather.error})`}
              </p>
            )}
            <Card flush><Table caption="Feeds" columns={columns} rows={s.feeds} rowKey={(f) => f.code} /></Card>
          </div>
        )}
      </Loaded>
      <ConnectDialog open={open} onOpenChange={setOpen} />
    </Page>
  );
}

function ConnectDialog({ open, onOpenChange }: { open: boolean; onOpenChange: (o: boolean) => void }) {
  const [name, setName] = useState("");
  const [csv, setCsv] = useState("");
  const [klass, setKlass] = useState("clinical");
  const [metric, setMetric] = useState("count");
  const propose = useSend<{ name: string; csv: string }, Proposal>("POST", "/api/signals/connect");
  const confirm = useSend<{ id: string; signal_class: string; metric: string }>("POST", (b) => `/api/signals/connect/${b.id}/confirm`);
  const toast = useToast();
  const p = propose.data;
  return (
    <Dialog
      open={open}
      onOpenChange={onOpenChange}
      size="lg"
      title="Connect a new feed"
      description="Upload a CSV. The copilot maps the columns; free-text columns are never loaded."
      footer={
        p ? (
          <Button variant="primary" busy={confirm.isPending} onClick={() => confirm.mutate({ id: p.id, signal_class: klass, metric }, { onSuccess: () => { onOpenChange(false); toast({ title: "Feed connected", tone: "good" }); }, onError: (e) => toast({ title: "Not connected", body: e.message, tone: "critical" }) })}>
            Confirm and load {p.rows} rows
          </Button>
        ) : (
          <Button variant="primary" disabled={!name.trim() || !csv} busy={propose.isPending} onClick={() => propose.mutate({ name, csv })}>Map the columns</Button>
        )
      }
    >
      <div className="stack">
        <Field label="Feed name">{(f) => <Input {...f} value={name} onChange={(e) => setName(e.target.value)} placeholder="For example: Pharmacy sales by camp block" />}</Field>
        <Field label="CSV file">
          {(f) => <input {...{ id: f.id }} type="file" accept=".csv,text/csv" onChange={async (e) => setCsv((await e.target.files?.[0]?.text()) ?? "")} />}
        </Field>
        {p && (
          <div className="stack stack--tight">
            <span className="section-title">Proposed mapping</span>
            <ul className="list">
              {p.columns.map((c) => (
                <li key={c.column} className="row row--between">
                  <span className="small"><strong>{c.column}</strong></span>
                  {c.free_text ? <span className="pill pill--sand">Free text: excluded</span> : <span className="pill pill--mint">{titleCase(c.field)}{c.confidence !== null ? ` (${pct(c.confidence)})` : ""}</span>}
                </li>
              ))}
            </ul>
            <div className="grid grid--2">
              <Field label="Signal class">{(f) => <Select {...f} value={klass} onValueChange={setKlass} options={["clinical", "workplace", "environmental", "community", "worker_reported"].map((v) => ({ value: v, label: titleCase(v) }))} />}</Field>
              <Field label="Measure name">{(f) => <Input {...f} value={metric} onChange={(e) => setMetric(e.target.value)} />}</Field>
            </div>
          </div>
        )}
      </div>
    </Dialog>
  );
}
