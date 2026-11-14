import { ArrowLeftRight, CircleCheck, CircleHelp, ShieldCheck, Stethoscope } from "lucide-react";
import type { ComponentType, SVGProps } from "react";
import { cx } from "./cx";
import "./ui.css";

export type Tier = "fit" | "fit_with_controls" | "reassign" | "refer" | "unknown";

type TierLook = {
  label: string;
  tone: "good" | "warning" | "critical" | "lilac" | "neutral";
  Icon: ComponentType<SVGProps<SVGSVGElement>>;
};

export const TIER_LOOK: Record<Tier, TierLook> = {
  fit: { label: "Fit for duty", tone: "good", Icon: CircleCheck },
  fit_with_controls: { label: "Fit with extra controls", tone: "warning", Icon: ShieldCheck },
  reassign: { label: "Reassign today", tone: "critical", Icon: ArrowLeftRight },
  refer: { label: "Refer to clinic", tone: "lilac", Icon: Stethoscope },
  unknown: { label: "Unknown", tone: "neutral", Icon: CircleHelp },
};

export function TierChip({ tier, size = "md" }: { tier: Tier; size?: "md" | "lg" }) {
  const look = TIER_LOOK[tier];
  return (
    <span className={cx("dl-chip", `dl-chip--${look.tone}`, size === "lg" && "dl-chip--lg")}>
      <look.Icon aria-hidden="true" />
      {look.label}
    </span>
  );
}
