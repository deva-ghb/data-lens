import { LogoFrame, type LogoProps } from "./LogoFrame";

const CENTER = 16;
const OUTER = 12.5;
const INNER = 6.5;

type Point = [number, number];

function round(value: number): number {
  return Math.round(value * 100) / 100;
}

/** The hexagonal opening of a camera aperture, corners pointing left and right. */
const HEX: Point[] = Array.from({ length: 6 }, (_, k) => {
  const angle = (Math.PI / 3) * k;
  return [CENTER + INNER * Math.cos(angle), CENTER + INNER * Math.sin(angle)];
});

/**
 * Each blade edge runs along one side of the opening and carries on until it
 * meets the lens rim, which is what makes the shape read as an aperture.
 */
const BLADES: string = HEX.map((start, k) => {
  const end = HEX[(k + 1) % 6] as Point;
  const dx = end[0] - start[0];
  const dy = end[1] - start[1];
  const length = Math.hypot(dx, dy);
  const ux = dx / length;
  const uy = dy / length;
  // Solve |start + t*u - center| = OUTER for the positive root.
  const ox = start[0] - CENTER;
  const oy = start[1] - CENTER;
  const b = ox * ux + oy * uy;
  const c = ox * ox + oy * oy - OUTER * OUTER;
  const t = -b + Math.sqrt(b * b - c);
  return `M${round(start[0])} ${round(start[1])}L${round(start[0] + ux * t)} ${round(start[1] + uy * t)}`;
}).join("");

const OPENING = `${HEX.map(([x, y], k) => `${k === 0 ? "M" : "L"}${round(x)} ${round(y)}`).join("")}Z`;

/** Data Lens: a lens aperture with a pulse line running through its opening. */
export function DataLensLogo(props: LogoProps) {
  return (
    <LogoFrame {...props} name="Data Lens" lead="Data" rest="Lens">
      <circle cx={CENTER} cy={CENTER} r={OUTER} fill="var(--tint-periwinkle-fill)" />
      <path d={OPENING} fill="var(--color-page)" />
      <path d={BLADES} stroke="var(--color-accent)" strokeWidth={1.25} strokeLinecap="round" />
      <circle cx={CENTER} cy={CENTER} r={OUTER} stroke="var(--color-accent)" strokeWidth={2} />
      <path
        d="M10.5 16H12.75L14.25 13L16.5 19L18.25 14.5L19.25 16H21.5"
        stroke="var(--tint-periwinkle-ink)"
        strokeWidth={2}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </LogoFrame>
  );
}
