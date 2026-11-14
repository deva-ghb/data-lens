import "./ui.css";

export type Status = "good" | "warning" | "critical" | "neutral";

/** A coloured dot always paired with its label, so the state never relies on colour alone. */
export function StatusDot({ status, label }: { status: Status; label: string }) {
  return (
    <span className={`dl-dot dl-dot--${status}`}>
      <span className="dl-dot__mark" aria-hidden="true" />
      {label}
    </span>
  );
}
