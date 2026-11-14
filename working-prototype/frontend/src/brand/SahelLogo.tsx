import { LogoFrame, type LogoProps } from "./LogoFrame";

/** Sahel Marine Services: a dhow's lateen sail over a curved hull. */
export function SahelLogo(props: LogoProps) {
  return (
    <LogoFrame {...props} name="Sahel Marine Services" lead="Sahel" rest="Marine Services">
      <path d="M15.5 6V21" stroke="var(--tint-sky-ink)" strokeWidth={2} strokeLinecap="round" />
      <path d="M6.5 19L26 3.5C25 11.5 21.5 17 15.5 19.5Z" fill="var(--series-4)" />
      <path d="M6.5 19L26 3.5" stroke="var(--tint-sand-ink)" strokeWidth={1.5} strokeLinecap="round" />
      <path d="M3.5 22H28.5C27 26 24.5 28 20.5 28H11.5C7.5 28 5 26 3.5 22Z" fill="var(--tint-sky-ink)" />
    </LogoFrame>
  );
}
