import { Download, Ellipsis, Pencil, Plus, Trash2, UserRoundCog } from "lucide-react";
import { useState, type ReactNode } from "react";
import { BayanLogo } from "../brand/BayanLogo";
import { ClinicLogo } from "../brand/ClinicLogo";
import { DataLensLogo } from "../brand/DataLensLogo";
import type { LogoProps } from "../brand/LogoFrame";
import { MirsalLogo } from "../brand/MirsalLogo";
import { SahelLogo } from "../brand/SahelLogo";
import { AiSection, type AiDraft } from "../ui/AiSection";
import { Button } from "../ui/Button";
import { Card } from "../ui/Card";
import { BarChart } from "../ui/charts/BarChart";
import { HeatGrid } from "../ui/charts/HeatGrid";
import { LineChart } from "../ui/charts/LineChart";
import { Sparkline } from "../ui/charts/Sparkline";
import { ConfirmBar } from "../ui/ConfirmBar";
import { Dialog } from "../ui/Dialog";
import { EmptyState } from "../ui/EmptyState";
import { ErrorState } from "../ui/ErrorState";
import { Field, Input } from "../ui/Field";
import { Menu } from "../ui/Menu";
import { ReasoningPanel } from "../ui/ReasoningPanel";
import { Select } from "../ui/Select";
import { Skeleton } from "../ui/Skeleton";
import { Stat } from "../ui/Stat";
import { StatusDot, type Status } from "../ui/StatusDot";
import { Table } from "../ui/Table";
import { TabPanel, Tabs } from "../ui/Tabs";
import { TextArea } from "../ui/TextArea";
import { TierChip, type Tier } from "../ui/TierChip";
import { useToast } from "../ui/Toast";
import "./kit.css";

/*
 * Development-only gallery of every shared component and logo, rendered with
 * realistic props so the kit can be reviewed and screenshotted in one place.
 * None of this data reaches a real screen.
 */

const SWATCHES: Array<{ group: string; tokens: string[] }> = [
  {
    group: "Surfaces and text",
    tokens: [
      "color-page",
      "color-canvas",
      "color-wash",
      "color-border",
      "color-border-strong",
      "color-text",
      "color-text-secondary",
      "color-text-muted",
    ],
  },
  { group: "Accent", tokens: ["color-accent", "color-accent-hover", "color-accent-soft", "color-accent-ink"] },
  {
    group: "Tints",
    tokens: [
      "tint-periwinkle-fill",
      "tint-mint-fill",
      "tint-sand-fill",
      "tint-rose-fill",
      "tint-lilac-fill",
      "tint-sky-fill",
    ],
  },
  { group: "Chart series", tokens: ["series-1", "series-2", "series-3", "series-4", "series-5", "series-6"] },
  { group: "Sequential", tokens: ["seq-1", "seq-2", "seq-3", "seq-4", "seq-5", "seq-6"] },
];

const BERTHS = [
  { value: "b1", label: "Berth 1", hint: "Container quay, north" },
  { value: "b2", label: "Berth 2", hint: "Container quay, north" },
  { value: "b3", label: "Berth 3", hint: "Container quay, south" },
  { value: "b4", label: "Berth 4", hint: "Ro-ro ramp" },
  { value: "b5", label: "Berth 5", hint: "Bulk and break-bulk" },
  { value: "b6", label: "Berth 6", hint: "Reefer stack" },
  { value: "b7", label: "Berth 7", hint: "Empty depot" },
  { value: "b8", label: "Berth 8", hint: "Inspection yard" },
  { value: "b9", label: "Berth 9", hint: "Feeder vessels" },
  { value: "b10", label: "Berth 10", hint: "Lashing gang base" },
];

const SHIFTS = [
  { value: "day", label: "Day shift" },
  { value: "night", label: "Night shift" },
  { value: "relief", label: "Relief crew" },
];

type CrewRow = {
  id: string;
  name: string;
  role: string;
  employer: ReactNode;
  tier: Tier;
  checkIn: { status: Status; label: string };
  nights: number;
};

const CREW: CrewRow[] = [
  {
    id: "1",
    name: "Rashid Al Mansoori",
    role: "Crane operator",
    employer: <MirsalLogo size={20} variant="mark" />,
    tier: "fit",
    checkIn: { status: "good", label: "Checked in 05:42" },
    nights: 0,
  },
  {
    id: "2",
    name: "Joseph Mwangi",
    role: "Lashing gang",
    employer: <BayanLogo size={20} variant="mark" />,
    tier: "fit_with_controls",
    checkIn: { status: "good", label: "Checked in 05:51" },
    nights: 3,
  },
  {
    id: "3",
    name: "Arjun Pillai",
    role: "Reach stacker driver",
    employer: <SahelLogo size={20} variant="mark" />,
    tier: "reassign",
    checkIn: { status: "warning", label: "Late, 06:14" },
    nights: 4,
  },
  {
    id: "4",
    name: "Samuel Okoro",
    role: "Signaller",
    employer: <BayanLogo size={20} variant="mark" />,
    tier: "refer",
    checkIn: { status: "critical", label: "Clinic flag" },
    nights: 1,
  },
  {
    id: "5",
    name: "Omar Haddad",
    role: "Lashing gang",
    employer: <MirsalLogo size={20} variant="mark" />,
    tier: "unknown",
    checkIn: { status: "neutral", label: "No check-in" },
    nights: 2,
  },
];

const DRAFT: AiDraft = {
  id: "kit-draft",
  kind: "reassignment_note",
  content:
    "Arjun Pillai is on his fourth night in a row and the yard reading is in heat tier 2 from 13:00. Move him to the reefer gate for the afternoon and keep a second driver on the reach stacker.",
  sure: ["Fourth consecutive night shift", "Heat tier 2 forecast from 13:00"],
  unsure: ["Whether the 06:14 check-in was a late arrival or a scanner fault"],
  would_change: ["A clinic note clearing him for full duty", "Cloud cover dropping the reading below 30"],
  confidence: 0.78,
  reasoning: {
    evidence: ["Roster: nights on 11, 12, 13 and 14 Nov", "Yard sensor forecast 31.2 at 13:00"],
    rules: ["Fourth consecutive night raises the risk score", "Heat tier 2 and above needs extra controls"],
    inferences: ["Combined effect moves him from fit with controls to reassign"],
    rejected: ["Age and employer were not used"],
  },
  status: "draft",
  model: "assistant",
};

const UNAVAILABLE: AiDraft = { ...DRAFT, id: "kit-unavailable", content: "", status: "unavailable" };

const CONFIRMED: AiDraft = {
  ...DRAFT,
  id: "kit-confirmed",
  status: "confirmed",
  confirmed_by: "Fatima Al Zaabi",
};

const LOGOS: Array<{ name: string; Logo: (props: LogoProps) => ReactNode }> = [
  { name: "Data Lens", Logo: DataLensLogo },
  { name: "Mirsal Terminals", Logo: MirsalLogo },
  { name: "Sahel Marine Services", Logo: SahelLogo },
  { name: "Bayan Manpower Contracting", Logo: BayanLogo },
  { name: "Mirsal Village Clinic", Logo: ClinicLogo },
];

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="kit-section">
      <h2 className="kit-section__title">{title}</h2>
      {children}
    </section>
  );
}

export default function Kit() {
  const toast = useToast();
  const [berth, setBerth] = useState("b3");
  const [shift, setShift] = useState<string>("");
  const [tab, setTab] = useState("roster");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [note, setNote] = useState("");

  return (
    <div className="kit">
      <header className="kit-header">
        <DataLensLogo size={28} />
        <span className="kit-header__tag">Component kit</span>
      </header>

      <main className="kit-main">
        <Section title="Colour">
          <div className="kit-swatch-groups">
            {SWATCHES.map((group) => (
              <div key={group.group} className="kit-swatch-group">
                <h3 className="kit-label">{group.group}</h3>
                <div className="kit-swatches">
                  {group.tokens.map((token) => (
                    <div key={token} className="kit-swatch">
                      <span className="kit-swatch__chip" style={{ background: `var(--${token})` }} />
                      <span className="kit-swatch__name">{token}</span>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </Section>

        <Section title="Type">
          <div className="kit-type">
            <h1>Shift readiness, Berth 3</h1>
            <h2>Night crew before the 18:00 handover</h2>
            <h3>Heat tier 2 from 13:00</h3>
            <p>
              Body text sits at 14 px on a 20 px line. Times and figures use tabular numerals:{" "}
              <span className="num">05:42, 31.2, 1,284</span>.
            </p>
            <p className="kit-label">Labels and column heads are small, light grey and never bold.</p>
          </div>
        </Section>

        <Section title="Buttons">
          <div className="kit-row">
            <Button variant="primary" icon={<Plus />}>
              Add worker
            </Button>
            <Button>Export list</Button>
            <Button variant="ghost" icon={<Download />}>
              Download
            </Button>
            <Button variant="danger" icon={<Trash2 />}>
              Remove from shift
            </Button>
            <Button variant="primary" busy>
              Saving
            </Button>
            <Button disabled>Not allowed</Button>
            <Button iconOnly icon={<Pencil />} aria-label="Edit" />
          </div>
          <div className="kit-row">
            <Button size="sm" variant="primary">
              Approve
            </Button>
            <Button size="sm">Decline</Button>
            <Button size="sm" variant="ghost">
              View details
            </Button>
          </div>
        </Section>

        <Section title="Form controls">
          <div className="kit-form">
            <Field label="Berth" hint="Ten berths, the list scrolls inside its menu.">
              {(control) => (
                <Select
                  id={control.id}
                  aria-describedby={control["aria-describedby"]}
                  value={berth}
                  onValueChange={setBerth}
                  options={BERTHS}
                />
              )}
            </Field>
            <Field label="Shift" error="Choose a shift before saving.">
              {(control) => (
                <Select
                  id={control.id}
                  aria-describedby={control["aria-describedby"]}
                  invalid={control.invalid}
                  value={shift}
                  onValueChange={setShift}
                  options={SHIFTS}
                  placeholder="Choose a shift"
                />
              )}
            </Field>
            <Field label="Gang" hint="Locked while the permit is open.">
              {(control) => (
                <Select
                  id={control.id}
                  aria-describedby={control["aria-describedby"]}
                  value="g4"
                  onValueChange={() => undefined}
                  options={[{ value: "g4", label: "Gang 4, lashing" }]}
                  disabled
                />
              )}
            </Field>
            <Field label="Work email">
              {(control) => (
                <Input
                  id={control.id}
                  aria-describedby={control["aria-describedby"]}
                  type="email"
                  placeholder="firstname.lastname@mirsalterminals.com"
                />
              )}
            </Field>
            <Field label="Badge number" error="Badge numbers have six digits.">
              {(control) => (
                <Input
                  id={control.id}
                  aria-describedby={control["aria-describedby"]}
                  invalid={control.invalid}
                  defaultValue="40217"
                />
              )}
            </Field>
            <Field label="Handover note" optional className="kit-form__wide">
              {(control) => (
                <TextArea
                  id={control.id}
                  value={note}
                  onChange={(event) => setNote(event.target.value)}
                  placeholder="Anything the next shift should know"
                />
              )}
            </Field>
          </div>
        </Section>

        <Section title="Menu and dialog">
          <div className="kit-row">
            <Menu
              label="Worker actions"
              trigger={
                <Button iconOnly variant="ghost" icon={<Ellipsis />} aria-label="Worker actions" />
              }
              items={[
                { kind: "label", label: "Arjun Pillai" },
                { label: "Edit details", icon: <Pencil />, onSelect: () => undefined },
                {
                  label: "Change employer",
                  icon: <UserRoundCog />,
                  hint: "Moves the record to another contractor",
                  onSelect: () => undefined,
                },
                { label: "Export record", icon: <Download />, onSelect: () => undefined, disabled: true },
                { kind: "separator" },
                { label: "Remove from shift", icon: <Trash2 />, danger: true, onSelect: () => undefined },
              ]}
            />
            <Menu
              align="start"
              trigger={<Button>Open menu</Button>}
              items={[
                { label: "Day shift", onSelect: () => undefined },
                { label: "Night shift", onSelect: () => undefined },
                { label: "Relief crew", onSelect: () => undefined },
              ]}
            />
            <Button onClick={() => setDialogOpen(true)}>Open dialog</Button>
            <Button
              onClick={() =>
                toast({ title: "Reassignment saved", body: "Arjun Pillai moves to the reefer gate at 13:00.", tone: "good" })
              }
            >
              Show toast
            </Button>
            <Button
              onClick={() =>
                toast({ title: "Clinic feed is late", body: "Last update 07:10. Warnings drop one level.", tone: "critical" })
              }
            >
              Show problem toast
            </Button>
          </div>
          <Dialog
            open={dialogOpen}
            onOpenChange={setDialogOpen}
            title="Reassign Arjun Pillai?"
            description="He moves from the reach stacker to the reefer gate from 13:00 today."
            footer={
              <>
                <Button onClick={() => setDialogOpen(false)}>Cancel</Button>
                <Button variant="primary" onClick={() => setDialogOpen(false)}>
                  Reassign
                </Button>
              </>
            }
          >
            <Field label="Reason shown to the foreman">
              {(control) => <TextArea id={control.id} rows={3} defaultValue="Fourth night in a row in heat tier 2." />}
            </Field>
          </Dialog>
        </Section>

        <Section title="Tabs, table, chips">
          <Tabs
            label="Shift views"
            value={tab}
            onValueChange={setTab}
            tabs={[
              { value: "roster", label: "Roster", count: CREW.length },
              { value: "permits", label: "Permits", count: 3 },
              { value: "warnings", label: "Warnings", count: 1 },
              { value: "history", label: "History" },
            ]}
          >
            <TabPanel value="roster">
              <Table
                caption="Night crew, Berth 3"
                rows={CREW}
                rowKey={(row) => row.id}
                onRowClick={() => undefined}
                columns={[
                  {
                    key: "name",
                    header: "Worker",
                    render: (row) => (
                      <span className="kit-person">
                        <span className="kit-person__name">{row.name}</span>
                        <span className="kit-person__role">{row.role}</span>
                      </span>
                    ),
                  },
                  { key: "employer", header: "Employer", render: (row) => row.employer },
                  { key: "checkin", header: "Check-in", render: (row) => <StatusDot {...row.checkIn} /> },
                  { key: "nights", header: "Nights in a row", numeric: true, render: (row) => row.nights },
                  { key: "tier", header: "Readiness", render: (row) => <TierChip tier={row.tier} /> },
                ]}
              />
            </TabPanel>
            <TabPanel value="permits">
              <EmptyState title="No open permits" body="Permits issued for this shift will appear here." />
            </TabPanel>
            <TabPanel value="warnings">
              <EmptyState title="No warnings" />
            </TabPanel>
            <TabPanel value="history">
              <EmptyState title="No history yet" />
            </TabPanel>
          </Tabs>
          <div className="kit-row">
            {(["fit", "fit_with_controls", "reassign", "refer", "unknown"] as Tier[]).map((tier) => (
              <TierChip key={tier} tier={tier} />
            ))}
          </div>
          <div className="kit-row">
            <TierChip tier="reassign" size="lg" />
            <StatusDot status="good" label="On time" />
            <StatusDot status="warning" label="Running late" />
            <StatusDot status="critical" label="Clinic flag" />
            <StatusDot status="neutral" label="No check-in" />
          </div>
        </Section>

        <Section title="Cards and figures">
          <div className="kit-stats">
            <Stat
              label="Crew on shift"
              value="142"
              delta={{ text: "+6", direction: "up", good: true, period: "vs last night" }}
            />
            <Stat
              label="Reassign today"
              value="3"
              delta={{ text: "+2", direction: "up", good: false, period: "vs last night" }}
              trend={[1, 0, 2, 1, 1, 2, 1, 3]}
            />
            <Stat label="Peak heat reading" value="31.2" unit="°C" trend={[27.4, 28.1, 29.6, 30.2, 31.2, 30.8]} />
            <Stat
              label="Unknown check-ins"
              value="5"
              delta={{ text: "0", direction: "flat", good: true, period: "vs last night" }}
            />
          </div>
          <div className="kit-cards">
            <Card title="Heat reading, Berth 3" subtitle="Wet bulb globe temperature, 15 Nov" actions={<Button size="sm" variant="ghost">Details</Button>}>
              <LineChart
                label="Heat reading by hour at Berth 3"
                categories={["06:00", "07:00", "08:00", "09:00", "10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00", "17:00"]}
                series={[
                  { id: "b3", label: "Berth 3", values: [26.1, 26.8, 27.5, 28.4, 29.1, 29.8, 30.4, 31.2, 31.0, 30.3, 29.2, 28.0] },
                ]}
                zeroBased={false}
                reference={{ value: 30, label: "Heat tier 2" }}
                formatValue={(v) => v.toFixed(0)}
              />
            </Card>
            <Card title="Reassignments by week" subtitle="All berths">
              <LineChart
                label="Reassignments by week, three berths"
                categories={["Wk 40", "Wk 41", "Wk 42", "Wk 43", "Wk 44", "Wk 45", "Wk 46"]}
                series={[
                  { id: "n", label: "North quay", values: [4, 6, 5, 8, 7, 9, 11] },
                  { id: "s", label: "South quay", values: [3, 3, 4, 4, 6, 5, 6] },
                  { id: "r", label: "Reefer yard", values: [1, 2, 2, 1, 3, 2, 4] },
                ]}
              />
            </Card>
            <Card title="Late check-ins by gang" subtitle="Last 14 days">
              <BarChart
                label="Late check-ins by gang"
                orientation="columns"
                data={[
                  { label: "Gang 1", value: 4 },
                  { label: "Gang 2", value: 9 },
                  { label: "Gang 3", value: 6 },
                  { label: "Gang 4", value: 12 },
                  { label: "Gang 5", value: null },
                  { label: "Gang 6", value: 3 },
                ]}
              />
            </Card>
            <Card title="Warnings by employer" subtitle="This month">
              <BarChart
                label="Warnings by employer"
                orientation="bars"
                data={[
                  { label: "Mirsal Terminals", value: 18 },
                  { label: "Bayan Manpower", value: 11 },
                  { label: "Sahel Marine", value: 7 },
                  { label: "Agency pool", value: null },
                ]}
              />
            </Card>
          </div>
          <Card title="Reassign rate by gang and night" subtitle="Share of crew moved, last 7 nights">
            <HeatGrid
              label="Reassign rate by gang and night"
              rows={["Gang 1", "Gang 2", "Gang 3", "Gang 4"]}
              columns={["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]}
              values={[
                [0.02, 0.04, 0.03, 0.06, 0.05, 0.08, 0.04],
                [0.05, 0.07, 0.1, 0.12, 0.09, 0.14, 0.11],
                [0.01, 0.02, null, 0.03, 0.02, 0.04, 0.03],
                [0.08, 0.11, 0.15, 0.18, 0.16, 0.2, 0.17],
              ]}
              domain={[0, 0.2]}
              formatValue={(v) => `${Math.round(v * 100)}%`}
              note="Hidden: fewer than 10 people"
            />
          </Card>
          <div className="kit-row">
            <span className="kit-label">Sparkline</span>
            <Sparkline values={[3, 4, 2, 5, 6, 4, 7, 8]} label="Reassignments" />
          </div>
        </Section>

        <Section title="Drafts for a person to confirm">
          <div className="kit-ai">
            <AiSection draft={DRAFT} onConfirm={() => undefined} onEdit={() => undefined} confirmLabel="Confirm note" />
            <AiSection
              draft={UNAVAILABLE}
              onConfirm={() => undefined}
              onEdit={() => undefined}
              confirmLabel="Save note"
            />
            <AiSection draft={CONFIRMED} onConfirm={() => undefined} onEdit={() => undefined} confirmLabel="Confirm note" />
            <Card title="How this was worked out">
              <ReasoningPanel reasoning={DRAFT.reasoning} />
            </Card>
          </div>
        </Section>

        <Section title="Confirm bar">
          <p className="kit-label">Pinned to the bottom of the screen on real pages; shown in place here.</p>
          <div className="kit-frame">
            <ConfirmBar
              message="3 reassignments ready to send"
              detail="Foremen are told at the start of the 13:00 break."
              confirmLabel="Send to foremen"
              onConfirm={() => undefined}
              onCancel={() => undefined}
            />
          </div>
        </Section>

        <Section title="Empty, error and loading">
          <div className="kit-states">
            <Card>
              <EmptyState
                title="No crew on this shift yet"
                body="Crew appear here once the planner publishes the roster."
                action={<Button variant="primary">Open planner</Button>}
              />
            </Card>
            <Card>
              <ErrorState message="The roster service did not answer. Your changes are kept." onRetry={() => undefined} />
            </Card>
            <Card title="Loading">
              <div className="kit-skeletons">
                <Skeleton height={20} width="40%" />
                <Skeleton lines={3} />
                <Skeleton height={120} />
              </div>
            </Card>
          </div>
        </Section>

        <Section title="Logos">
          <div className="kit-logos">
            {LOGOS.map(({ name, Logo }) => (
              <div key={name} className="kit-logo-row">
                <Logo size={160} variant="mark" />
                <div className="kit-logo-sizes">
                  <Logo size={48} variant="mark" />
                  <Logo size={32} variant="mark" />
                  <Logo size={20} variant="mark" />
                </div>
                <div className="kit-logo-full">
                  <Logo size={40} />
                  <Logo size={24} />
                </div>
              </div>
            ))}
          </div>
        </Section>
      </main>
    </div>
  );
}
