import { LogoFrame, type LogoProps } from "./LogoFrame";

/** Mirsal Terminals: a ship-to-shore quay crane standing over a wave line. */
export function MirsalLogo(props: LogoProps) {
  return (
    <LogoFrame {...props} name="Mirsal Terminals" lead="Mirsal" rest="Terminals">
      <g stroke="var(--tint-periwinkle-ink)" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
        <path d="M3.5 9.5H28.5" />
        <path d="M5.5 9.5L13.5 3.5L27 9.5" />
        <path d="M10 9.5L13.5 3.5L17 9.5" />
        <path d="M10 9.5V22.5M17 9.5V22.5M10 15.5H17" />
        <path d="M23.5 9.5V13" />
      </g>
      <rect x={20.75} y={13} width={5.5} height={4} rx={0.75} fill="var(--series-5)" />
      <path
        d="M3 26.5C5.17 24.83 7.33 24.83 9.5 26.5C11.67 28.17 13.83 28.17 16 26.5C18.17 24.83 20.33 24.83 22.5 26.5C24.67 28.17 26.83 28.17 29 26.5"
        stroke="var(--series-5)"
        strokeWidth={2}
        strokeLinecap="round"
      />
    </LogoFrame>
  );
}
