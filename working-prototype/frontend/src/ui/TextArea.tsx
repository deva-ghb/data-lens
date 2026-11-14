import { forwardRef, type TextareaHTMLAttributes } from "react";
import { cx } from "./cx";
import "./ui.css";

export type TextAreaProps = TextareaHTMLAttributes<HTMLTextAreaElement> & { invalid?: boolean };

export const TextArea = forwardRef<HTMLTextAreaElement, TextAreaProps>(function TextArea(
  { invalid = false, className, rows = 4, ...rest },
  ref,
) {
  return (
    <textarea
      ref={ref}
      rows={rows}
      className={cx("dl-control", "dl-textarea", className)}
      aria-invalid={invalid || undefined}
      {...rest}
    />
  );
});
