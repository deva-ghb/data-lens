import { LoaderCircle } from "lucide-react";
import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from "react";
import { cx } from "./cx";
import "./ui.css";

export type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";

export type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant;
  size?: "md" | "sm";
  icon?: ReactNode;
  /** Square button with only an icon; pass aria-label. */
  iconOnly?: boolean;
  block?: boolean;
  busy?: boolean;
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  {
    variant = "secondary",
    size = "md",
    icon,
    iconOnly = false,
    block = false,
    busy = false,
    type = "button",
    className,
    disabled,
    children,
    ...rest
  },
  ref,
) {
  return (
    <button
      ref={ref}
      type={type}
      className={cx(
        "dl-btn",
        `dl-btn--${variant}`,
        size === "sm" && "dl-btn--sm",
        iconOnly && "dl-btn--icon",
        block && "dl-btn--block",
        className,
      )}
      disabled={disabled === true || busy}
      aria-busy={busy || undefined}
      {...rest}
    >
      {busy ? <LoaderCircle className="dl-btn__spinner" aria-hidden="true" /> : icon}
      {iconOnly ? null : children}
    </button>
  );
});
