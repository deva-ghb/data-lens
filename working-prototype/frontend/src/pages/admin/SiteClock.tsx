import { CalendarClock } from "lucide-react";
import { useState } from "react";
import { useSend } from "../../api/hooks";
import { Page } from "../../layout/AppShell";
import { siteTime, useMeta } from "../../layout/Meta";
import { Button } from "../../ui/Button";
import { Card } from "../../ui/Card";
import { Field, Input } from "../../ui/Field";
import { useToast } from "../../ui/Toast";
import "../pages.css";

const PRESETS: [string, string][] = [
  ["Evening before the story night", "2026-07-28T14:00"],
  ["Shift start, 29 July night", "2026-07-29T15:00"],
  ["Mid-shift, 29 July night", "2026-07-29T17:30"],
  ["Morning after", "2026-07-30T04:00"],
];

export function SiteClock() {
  const meta = useMeta();
  const [value, setValue] = useState("2026-07-29T15:00");
  const save = useSend<{ now: string }>("PUT", "/api/admin/clock");
  const toast = useToast();
  const set = (utc: string) => save.mutate({ now: `${utc}:00` }, { onSuccess: () => toast({ title: "Site clock moved", tone: "good" }) });
  return (
    <Page title="Site clock" subtitle="Every time rule in the app reads this clock: shifts, tier expiry, feed freshness and due dates. It stays where it is until you move it.">
      <div className="grid grid--2 grid--top">
        <Card title="Now on site" subtitle="Abu Dhabi time (UTC+4)">
          <p className="clock-now num">{meta.data ? siteTime(meta.data.site_now_local) : "…"}</p>
        </Card>
        <Card title="Move the clock">
          <div className="stack">
            <Field label="Site time in UTC" hint="Stored times are UTC; screens show site time.">
              {(p) => <Input {...p} type="datetime-local" value={value} onChange={(e) => setValue(e.target.value)} />}
            </Field>
            <Button variant="primary" icon={<CalendarClock />} busy={save.isPending} onClick={() => set(value)}>Set the clock</Button>
            <div className="stack stack--tight">
              <span className="section-title">Story moments</span>
              {PRESETS.map(([label, utc]) => (
                <Button key={utc} variant="secondary" onClick={() => set(utc)}>{label}</Button>
              ))}
            </div>
          </div>
        </Card>
      </div>
    </Page>
  );
}
