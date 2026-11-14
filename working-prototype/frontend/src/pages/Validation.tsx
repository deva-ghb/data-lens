import { useState } from "react";
import { useGet, useSend } from "../api/hooks";
import { Page } from "../layout/AppShell";
import { Button } from "../ui/Button";
import { Card } from "../ui/Card";
import { Stat } from "../ui/Stat";
import { BarChart } from "../ui/charts/BarChart";
import { Loaded, pct } from "./common";
import "./pages.css";

type Result = {
  action_line: number; feeds_off: string[]; days: number; lead_time_hours: Record<string, number | null>; sensitivity: [number, number];
  ppv: number; false_alarms: number; false_alarms_per_30d: number; latency_by_feed: Record<string, number>; budget_breaches: number;
  episodes: { district: string; zones: string[]; first_day: string; event: string | null }[];
  chosen_action_line?: number; sweep?: { action_line: number; sensitivity: [number, number]; ppv: number; false_alarms_per_30d: number; budget_breaches: number }[];
  feed_names?: Record<string, string>;
};

const EVENT: Record<string, string> = {
  E1_DUST_RESP: "Dust and breathing, Yard Block 4 (May)",
  E2_NIGHT_FATIGUE: "Night lashing fatigue, Berth 3 (June)",
  E3_PLANT_STRUCK: "Plant and people, Yard Block 2 (July)",
  E4_CAMP_C_COOLING: "Camp Block C cooling (July)",
};
const SWITCHABLE = ["CLINIC_VISITS", "CAMP_TICKETS", "CHECKINS", "SAFETY_REPORTS", "AIR_QUALITY", "SICKNESS_ABSENCE"];

export function Validation() {
  const stored = useGet<Result>("/api/analytics/validation", { staleTime: Infinity });
  const run = useSend<{ action_line: number; feeds_off: string[] }, Result>("POST", "/api/analytics/backtest");
  const [off, setOff] = useState<string[]>([]);
  const shown = run.data ?? stored.data;
  return (
    <Page title="Validation" subtitle="A back-test on 90 synthetic days with four injected events. The detector sees each day once. This shows the method runs end to end, not a real site's hit rate.">
      <Loaded query={stored}>
        {(base) => {
          const r = shown ?? base;
          const names = base.feed_names ?? {};
          return (
            <div className="stack">
              <div className="grid grid--4">
                <Stat label="Events found" value={`${r.sensitivity[0]} of ${r.sensitivity[1]}`} />
                <Stat label="Shortest lead time" value={`${Math.min(...Object.values(r.lead_time_hours).map((v) => v ?? 0))}`} unit="hours" />
                <Stat label="Warnings that were right" value={pct(r.ppv)} />
                <Stat label="False alarms a month" value={r.false_alarms_per_30d.toFixed(1)} />
              </div>
              <div className="grid grid--2">
                <Card title="Lead time by event" subtitle="Hours from the first warning to the harm it would have led to">
                  <BarChart label="Lead time by event" orientation="bars" data={Object.entries(r.lead_time_hours).map(([k, v]) => ({ label: EVENT[k] ?? k, value: v }))} formatValue={(v) => `${v} h`} hiddenText="Missed" />
                </Card>
                <Card title="Switch feeds off" subtitle="See the warning degrade, and the missing feed named">
                  <div className="stack">
                    <div className="row">
                      {SWITCHABLE.map((code) => (
                        <button key={code} type="button" className="tap" aria-pressed={off.includes(code)} style={{ minHeight: 40 }} onClick={() => setOff(off.includes(code) ? off.filter((c) => c !== code) : [...off, code])}>
                          {off.includes(code) ? "Off: " : ""}{names[code] ?? code}
                        </button>
                      ))}
                    </div>
                    <Button variant="primary" busy={run.isPending} onClick={() => run.mutate({ action_line: r.action_line, feeds_off: off })}>Run the back-test again</Button>
                    {run.data && <p className="small">With {off.length ? off.map((c) => names[c] ?? c).join(", ") : "every feed"} {off.length ? "off" : "on"}: {run.data.sensitivity[0]} of {run.data.sensitivity[1]} events found.</p>}
                  </div>
                </Card>
              </div>
              {base.sweep && (
                <Card title="Action line sweep" subtitle={`The most sensitive line that keeps every day inside the alert budget: ${base.chosen_action_line}`}>
                  <BarChart label="Warnings that were right, by action line" orientation="columns" data={base.sweep.map((s) => ({ label: s.action_line.toFixed(1), value: Math.round(s.ppv * 100) }))} formatValue={(v) => `${v}%`} height={200} />
                </Card>
              )}
              <Card title="Data latency by feed" subtitle="The slowest feed sets the real delay">
                <div className="row">
                  {Object.entries(r.latency_by_feed).map(([code, h]) => <span key={code} className="pill">{names[code] ?? code}: {h} h</span>)}
                </div>
              </Card>
            </div>
          );
        }}
      </Loaded>
    </Page>
  );
}
