import { LogoFrame, type LogoProps } from "./LogoFrame";

/** Mirsal Village Clinic: a palm leaf inside a soft-cornered cross. */
export function ClinicLogo(props: LogoProps) {
  return (
    <LogoFrame {...props} name="Mirsal Village Clinic" lead="Mirsal" rest="Village Clinic">
      <path
        d="M11 7.5C11 5.57 12.57 4 14.5 4H17.5C19.43 4 21 5.57 21 7.5V11H24.5C26.43 11 28 12.57 28 14.5V17.5C28 19.43 26.43 21 24.5 21H21V24.5C21 26.43 19.43 28 17.5 28H14.5C12.57 28 11 26.43 11 24.5V21H7.5C5.57 21 4 19.43 4 17.5V14.5C4 12.57 5.57 11 7.5 11H11Z"
        fill="var(--tint-mint-fill)"
        stroke="var(--tint-mint-ink)"
        strokeWidth={2}
        strokeLinejoin="round"
      />
      <path d="M10.5 21.5C10.5 15 15 10.5 21.5 10.5C21.5 17 17 21.5 10.5 21.5Z" fill="var(--series-2)" />
      <path
        d="M11.5 20.5L19.5 12.5M14 18V15.25M14 18H16.75M16.5 15.5V13M16.5 15.5H19"
        stroke="var(--color-page)"
        strokeWidth={1.25}
        strokeLinecap="round"
      />
    </LogoFrame>
  );
}
