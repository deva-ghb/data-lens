import { useState } from "react";
import { useGet, useSend } from "../api/hooks";
import { Page } from "../layout/AppShell";
import { Button } from "../ui/Button";
import { Card } from "../ui/Card";
import { Field, Input } from "../ui/Field";
import { Stat } from "../ui/Stat";
import { Loaded } from "./common";
import "./pages.css";

type Inputs = { lti_per_year: number; hot_share: number; night_share: number; acted_on: number; effectiveness: number; workdays_per_injury: number };
type Impact = { inputs: Inputs; attributable_lti: number; lti_avoided: number; workdays_avoided: number; not_counted: string[] };

const LABELS: [keyof Inputs, string, string][] = [
  ["lti_per_year", "Lost-time injuries a year", "Per terminal"],
  ["hot_share", "Share on hot-exposure days", "0 to 1"],
  ["night_share", "Share on a fourth or later night", "0 to 1"],
  ["acted_on", "Share of warnings acted on", "0 to 1"],
  ["effectiveness", "Effectiveness of the action", "0 to 1"],
  ["workdays_per_injury", "Workdays lost per injury", "Days"],
];

export function Impact() {
  const base = useGet<Impact>("/api/analytics/impact");
  const calc = useSend<Inputs, Impact>("POST", "/api/analytics/impact");
  const [inputs, setInputs] = useState<Inputs | null>(null);
  return (
    <Page title="Impact" subtitle="Injuries and workdays avoided, from inputs you can change. Replace them with your own baselines.">
      <Loaded query={base}>
        {(b) => {
          const current = inputs ?? b.inputs;
          const result = calc.data ?? b;
          return (
            <div className="grid grid--main-side">
              <Card title="Inputs">
                <div className="grid grid--2">
                  {LABELS.map(([key, label, hint]) => (
                    <Field key={key} label={label} hint={hint}>
                      {(p) => <Input {...p} type="number" step="any" value={current[key]} onChange={(e) => setInputs({ ...current, [key]: Number(e.target.value) })} />}
                    </Field>
                  ))}
                </div>
                <div className="row" style={{ marginTop: 16 }}>
                  <Button variant="primary" busy={calc.isPending} onClick={() => calc.mutate(current)}>Recalculate</Button>
                </div>
              </Card>
              <div className="stack">
                <Stat label="Lost-time injuries avoided a year" value={result.lti_avoided.toFixed(1)} />
                <Stat label="Workdays avoided a year" value={String(result.workdays_avoided)} />
                <Card title="Not counted here">
                  <ul className="list">{result.not_counted.map((t) => <li key={t} className="small">{t}</li>)}</ul>
                  <p className="xsmall muted">A pilot measures each of these directly.</p>
                </Card>
              </div>
            </div>
          );
        }}
      </Loaded>
    </Page>
  );
}
