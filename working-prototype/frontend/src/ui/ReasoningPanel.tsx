import "./ui.css";

export type Reasoning = {
  evidence: string[];
  rules: string[];
  inferences: string[];
  rejected: string[];
};

const GROUPS: Array<{ key: keyof Reasoning; heading: string }> = [
  { key: "evidence", heading: "What it looked at" },
  { key: "rules", heading: "Rules it applied" },
  { key: "inferences", heading: "What it worked out" },
  { key: "rejected", heading: "What it ruled out" },
];

export function BulletList({ items, none = "None recorded" }: { items: string[]; none?: string }) {
  if (items.length === 0) {
    return <p className="dl-list__none">{none}</p>;
  }
  return (
    <ul className="dl-list">
      {items.map((item, index) => (
        <li key={`${index}-${item}`}>{item}</li>
      ))}
    </ul>
  );
}

export function ReasoningPanel({ reasoning }: { reasoning: Reasoning }) {
  return (
    <div className="dl-reasoning">
      {GROUPS.map((group) => (
        <section key={group.key} className="dl-reasoning__group" aria-label={group.heading}>
          <h4 className="dl-reasoning__heading">{group.heading}</h4>
          <BulletList items={reasoning[group.key]} />
        </section>
      ))}
    </div>
  );
}
