import type { ReactNode } from "react";
import "./brand.css";

export type LogoProps = {
  /** Height of the mark in pixels. The wordmark scales with it. */
  size?: number;
  variant?: "mark" | "full";
  className?: string;
};

type FrameProps = LogoProps & {
  name: string;
  /** The wordmark in two weights: a strong lead word and a lighter remainder. */
  lead: string;
  rest?: string;
  children: ReactNode;
};

/** Shared layout for every organisation logo: a 32 unit drawn mark plus an optional wordmark. */
export function LogoFrame({ size = 32, variant = "full", className, name, lead, rest, children }: FrameProps) {
  const mark = (
    <svg
      className="dl-logo__mark"
      width={size}
      height={size}
      viewBox="0 0 32 32"
      fill="none"
      role={variant === "mark" ? "img" : undefined}
      aria-label={variant === "mark" ? name : undefined}
      aria-hidden={variant === "mark" ? undefined : true}
      focusable="false"
    >
      {children}
    </svg>
  );
  if (variant === "mark") {
    return <span className={["dl-logo", className].filter(Boolean).join(" ")}>{mark}</span>;
  }
  return (
    <span
      className={["dl-logo", className].filter(Boolean).join(" ")}
      role="img"
      aria-label={name}
      style={{ gap: Math.round(size * 0.3), fontSize: Math.max(12, Math.round(size * 0.5)) }}
    >
      {mark}
      <span className="dl-logo__word" aria-hidden="true">
        <span className="dl-logo__lead">{lead}</span>
        {rest !== undefined && <span className="dl-logo__rest"> {rest}</span>}
      </span>
    </span>
  );
}
