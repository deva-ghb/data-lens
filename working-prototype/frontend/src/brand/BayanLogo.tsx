import { LogoFrame, type LogoProps } from "./LogoFrame";

// The arc shares the hat's centre so the two read as one figure: a sun rising behind the crown.
const CX = 16;
const CY = 21;
const ARC_R = 12.5;
const START = (205 * Math.PI) / 180;
const END = (325 * Math.PI) / 180;

function at(angle: number): string {
  const x = Math.round((CX + ARC_R * Math.cos(angle)) * 100) / 100;
  const y = Math.round((CY + ARC_R * Math.sin(angle)) * 100) / 100;
  return `${x} ${y}`;
}

const END_X = Math.round((CX + ARC_R * Math.cos(END)) * 100) / 100;
const END_Y = Math.round((CY + ARC_R * Math.sin(END)) * 100) / 100;

/** Bayan Manpower Contracting: a hard hat beneath a rising arc. */
export function BayanLogo(props: LogoProps) {
  return (
    <LogoFrame {...props} name="Bayan Manpower Contracting" lead="Bayan" rest="Manpower Contracting">
      <path
        d={`M${at(START)}A${ARC_R} ${ARC_R} 0 0 1 ${at(END)}`}
        stroke="var(--tint-periwinkle-ink)"
        strokeWidth={2}
        strokeLinecap="round"
      />
      <circle cx={END_X} cy={END_Y} r={2} fill="var(--tint-periwinkle-ink)" />
      <path d="M7 21C7 15.75 11.03 11.5 16 11.5C20.97 11.5 25 15.75 25 21Z" fill="var(--series-4)" />
      <path
        d="M14.6 11.6C15.06 11.53 15.52 11.5 16 11.5C16.48 11.5 16.94 11.53 17.4 11.6V21H14.6Z"
        fill="var(--tint-sand-ink)"
      />
      <rect x={4} y={20.5} width={24} height={4} rx={2} fill="var(--tint-sand-ink)" />
    </LogoFrame>
  );
}
