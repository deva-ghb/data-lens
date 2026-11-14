import { CircleAlert } from "lucide-react";
import { forwardRef, useId, type InputHTMLAttributes, type ReactNode } from "react";
import { cx } from "./cx";
import "./ui.css";

/** Props a Field hands to its control so the label, hint and error are announced. */
export type FieldControlProps = {
  id: string;
  "aria-describedby"?: string;
  invalid: boolean;
};

export type FieldProps = {
  label: string;
  hint?: string;
  error?: string;
  optional?: boolean;
  className?: string;
  children: (control: FieldControlProps) => ReactNode;
};

export function Field({ label, hint, error, optional = false, className, children }: FieldProps) {
  const id = useId();
  const hintId = `${id}-hint`;
  const errorId = `${id}-error`;
  const describedBy = [hint !== undefined ? hintId : null, error !== undefined ? errorId : null]
    .filter(Boolean)
    .join(" ");
  return (
    <div className={cx("dl-field", className)}>
      <label className="dl-field__label" htmlFor={id}>
        {label}
        {optional && <span className="dl-field__optional">(optional)</span>}
      </label>
      {children({
        id,
        "aria-describedby": describedBy === "" ? undefined : describedBy,
        invalid: error !== undefined,
      })}
      {hint !== undefined && error === undefined && (
        <p id={hintId} className="dl-field__hint">
          {hint}
        </p>
      )}
      {error !== undefined && (
        <p id={errorId} className="dl-field__error" role="alert">
          <CircleAlert aria-hidden="true" />
          {error}
        </p>
      )}
    </div>
  );
}

export type InputProps = InputHTMLAttributes<HTMLInputElement> & { invalid?: boolean };

export const Input = forwardRef<HTMLInputElement, InputProps>(function Input(
  { invalid = false, className, ...rest },
  ref,
) {
  return (
    <input
      ref={ref}
      className={cx("dl-control", className)}
      aria-invalid={invalid || undefined}
      {...rest}
    />
  );
});
