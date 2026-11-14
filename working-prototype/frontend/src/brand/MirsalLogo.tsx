import { LogoFrame, type LogoProps } from "./LogoFrame";

/**
 * Mirsal Terminals: a ship-to-shore quay crane in side profile. The portal stands
 * on the quay, the boom reaches out over the water, and a container hangs from
 * the trolley above a wave line.
 */
export function MirsalLogo(props: LogoProps) {
  return (
    <LogoFrame {...props} name="Mirsal Terminals" lead="Mirsal" rest="Terminals">
      <g stroke="var(--tint-periwinkle-ink)" strokeLinecap="round" strokeLinejoin="round">
        <path d="M24 10V3.5" strokeWidth={2} />
        <path d="M24 3.5L4.5 9.5M24 3.5L28.5 9.5" strokeWidth={1.5} />
        <path d="M3 10H29" strokeWidth={2} />
        <path d="M9.5 11V14.5M11.5 11V14.5" strokeWidth={1} />
      </g>
      <path
        d="M18 23V11H27V23H24.75V16A2.25 2.25 0 0 0 20.25 16V23Z"
        fill="var(--tint-periwinkle-ink)"
      />
      <rect x={7.25} y={14.5} width={6.5} height={4} rx={0.75} fill="var(--series-5)" />
      <path
        d="M3 26.5C5.17 24.83 7.33 24.83 9.5 26.5C11.67 28.17 13.83 28.17 16 26.5C18.17 24.83 20.33 24.83 22.5 26.5C24.67 28.17 26.83 28.17 29 26.5"
        stroke="var(--series-5)"
        strokeWidth={2}
        strokeLinecap="round"
      />
    </LogoFrame>
  );
}
