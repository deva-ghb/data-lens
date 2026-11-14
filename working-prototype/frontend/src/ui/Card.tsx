import type { ReactNode } from "react";
import { cx } from "./cx";
import "./ui.css";

export type CardProps = {
  title?: string;
  subtitle?: string;
  actions?: ReactNode;
  /** Body runs edge to edge, for tables and lists. */
  flush?: boolean;
  className?: string;
  children: ReactNode;
};

export function Card({ title, subtitle, actions, flush = false, className, children }: CardProps) {
  const hasHeader = title !== undefined || actions !== undefined;
  return (
    <section className={cx("dl-card", flush && "dl-card--flush", className)} aria-label={title}>
      {hasHeader && (
        <header className="dl-card__header">
          <div className="dl-card__titles">
            {title !== undefined && <h3 className="dl-card__title">{title}</h3>}
            {subtitle !== undefined && <p className="dl-card__subtitle">{subtitle}</p>}
          </div>
          {actions !== undefined && <div className="dl-card__actions">{actions}</div>}
        </header>
      )}
      <div className="dl-card__body">{children}</div>
    </section>
  );
}
