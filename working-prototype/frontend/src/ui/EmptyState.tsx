import { Inbox } from "lucide-react";
import type { ReactNode } from "react";
import "./ui.css";

export type EmptyStateProps = {
  title: string;
  body?: string;
  icon?: ReactNode;
  action?: ReactNode;
};

export function EmptyState({ title, body, icon, action }: EmptyStateProps) {
  return (
    <div className="dl-state">
      <span className="dl-state__icon" aria-hidden="true">
        {icon ?? <Inbox />}
      </span>
      <p className="dl-state__title">{title}</p>
      {body !== undefined && <p className="dl-state__body">{body}</p>}
      {action !== undefined && <div className="dl-state__action">{action}</div>}
    </div>
  );
}
