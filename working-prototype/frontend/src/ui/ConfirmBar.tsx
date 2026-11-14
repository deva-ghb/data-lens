import { Button } from "./Button";
import "./ui.css";

export type ConfirmBarProps = {
  message: string;
  detail?: string;
  confirmLabel: string;
  onConfirm: () => void;
  cancelLabel?: string;
  onCancel?: () => void;
  busy?: boolean;
  danger?: boolean;
  disabled?: boolean;
};

/** A bar pinned to the bottom of its scroll area that asks a person to confirm a change. */
export function ConfirmBar({
  message,
  detail,
  confirmLabel,
  onConfirm,
  cancelLabel = "Cancel",
  onCancel,
  busy = false,
  danger = false,
  disabled = false,
}: ConfirmBarProps) {
  return (
    <div className="dl-confirm-bar" role="region" aria-label="Confirm change">
      <div className="dl-confirm-bar__text">
        <span className="dl-confirm-bar__message">{message}</span>
        {detail !== undefined && <span className="dl-confirm-bar__detail">{detail}</span>}
      </div>
      <div className="dl-confirm-bar__actions">
        {onCancel !== undefined && (
          <Button onClick={onCancel} disabled={busy}>
            {cancelLabel}
          </Button>
        )}
        <Button
          variant={danger ? "danger" : "primary"}
          onClick={onConfirm}
          busy={busy}
          disabled={disabled}
        >
          {confirmLabel}
        </Button>
      </div>
    </div>
  );
}
