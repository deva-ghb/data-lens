import { useGet } from "../api/hooks";
import { Page } from "../layout/AppShell";
import { Card } from "../ui/Card";
import { Table, type Column } from "../ui/Table";
import { Loaded } from "./common";
import "./pages.css";

type Group = { code: string; name: string; defined_by: string; proposal: string; people: number; cards: number; unsafe_per_100_cards: number; multiplier: number; assessed: boolean };

export function Groups() {
  const groups = useGet<Group[]>("/api/groups");
  const columns: Column<Group>[] = [
    { key: "name", header: "Group", render: (g) => <span className="stack stack--tight"><strong>{g.name}</strong><span className="xsmall muted">{g.defined_by}</span></span> },
    { key: "people", header: "People", numeric: true, render: (g) => g.people, width: 90 },
    { key: "rate", header: "Unsafe acts per 100 cards", numeric: true, render: (g) => g.unsafe_per_100_cards.toFixed(1), width: 190 },
    { key: "mult", header: "Against the site", numeric: true, render: (g) => <span className={g.multiplier > 1.05 ? "num build__up" : "num"}>{g.assessed ? `× ${g.multiplier.toFixed(2)}` : "Not assessed"}</span>, width: 150 },
    { key: "proposal", header: "What the copilot proposes", render: (g) => <span className="small">{g.proposal}</span> },
  ];
  return (
    <Page
      title="Behavioural groups"
      subtitle="Groups of 20 or more people with the same training path and exposure. A group is a signal, not a list: names never appear against a group, and origin, nationality, religion and language are never inputs."
    >
      <Loaded query={groups}>
        {(rows) => (
          <Card flush>
            <Table caption="Behavioural groups" columns={columns} rows={rows} rowKey={(g) => g.code} />
          </Card>
        )}
      </Loaded>
      <p className="small muted">
        Experienced lashers on the site induction and those on an extended night rotation share training and tenure. They differ only in roster, and that difference in unsafe-act rate is the evidence for the roster rule. The behavioural layer points at the system, not the person.
      </p>
    </Page>
  );
}
