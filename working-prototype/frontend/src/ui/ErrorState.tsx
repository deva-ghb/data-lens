import { RefreshCw, TriangleAlert } from "lucide-react";
import { Button } from "./Button";
import "./ui.css";

export type ErrorStateProps = {
  title?: string;
  message: string;
  onRetry?: () => void;
  retryLabel?: string;
  retrying?: boolean;
};

export function ErrorState({
  title = "This could not be loaded",
  message,
  onRetry,
  retryLabel = "Try again",
  retrying = false,
}: ErrorStateProps) {
  return (
    <div className="dl-state dl-state--error" role="alert">
      <span className="dl-state__icon" aria-hidden="true">
        <TriangleAlert />
      </span>
      <p className="dl-state__title">{title}</p>
      <p className="dl-state__body">{message}</p>
      {onRetry !== undefined && (
        <div className="dl-state__action">
          <Button icon={<RefreshCw />} onClick={onRetry} busy={retrying}>
            {retryLabel}
          </Button>
        </div>
      )}
    </div>
  );
}
