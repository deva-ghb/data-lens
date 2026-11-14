import type { ReactNode } from "react";
import { ErrorState } from "../ui/ErrorState";
import { Skeleton } from "../ui/Skeleton";
import type { ApiError } from "../api/client";

/** Loading, error or content: the three states every screen has. */
export function Loaded<T>({
  query,
  children,
  lines = 6,
}: {
  query: { isPending: boolean; isError: boolean; error: ApiError | null; data: T | undefined; refetch: () => unknown };
  children: (data: T) => ReactNode;
  lines?: number;
}) {
  if (query.isPending) return <Skeleton lines={lines} />;
  if (query.isError || query.data === undefined) {
    return (
      <ErrorState
        title={query.error?.status === 403 ? "Not available for your role" : "This could not be loaded"}
        message={query.error?.message ?? "Please try again."}
        onRetry={query.error?.status === 403 ? undefined : () => query.refetch()}
      />
    );
  }
  return <>{children(query.data)}</>;
}

export function pct(value: number): string {
  return `${Math.round(value * 100)}%`;
}

/** A heading line: short, and not a sentence or a numbered item. */
function isHeading(line: string): boolean {
  const t = line.trim();
  const last = t.charAt(t.length - 1);
  const first = t.charAt(0);
  return t.length > 0 && t.length <= 60 && last !== "." && last !== ":" && !(first >= "0" && first <= "9");
}

/** Drafted text as sections: blocks split on blank lines, a short first line becomes the block's heading. */
export function Prose({ text }: { text: string }) {
  const blocks = text
    .split("\n\n")
    .map((b) => b.split("\n").filter((l) => l.trim() !== ""))
    .filter((b) => b.length > 0);
  return (
    <div className="prose-blocks">
      {blocks.map((lines, i) => {
        const head = lines.length > 1 && isHeading(lines[0] ?? "") ? lines[0] : null;
        const body = head ? lines.slice(1) : lines;
        return (
          <section key={i} className="prose-block">
            {head && <h3 className="prose-block__head">{head}</h3>}
            {body.map((l, j) => (
              <p key={j} className="prose-block__line">
                {l}
              </p>
            ))}
          </section>
        );
      })}
    </div>
  );
}

/** "2026-06-13" reads "13 Jun". */
export function shortDate(isoDate: string): string {
  return new Date(`${isoDate.slice(0, 10)}T12:00:00Z`).toLocaleDateString("en-GB", { day: "numeric", month: "short", timeZone: "UTC" });
}

export function titleCase(text: string): string {
  const spaced = text.split("_").join(" ");
  return spaced.charAt(0).toUpperCase() + spaced.slice(1);
}
