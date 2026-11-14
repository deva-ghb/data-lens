import * as RadixDialog from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import type { ReactNode } from "react";
import { Button } from "./Button";
import { cx } from "./cx";
import "./ui.css";

export type DialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description?: string;
  children?: ReactNode;
  footer?: ReactNode;
  size?: "md" | "lg";
};

export function Dialog({
  open,
  onOpenChange,
  title,
  description,
  children,
  footer,
  size = "md",
}: DialogProps) {
  return (
    <RadixDialog.Root open={open} onOpenChange={onOpenChange}>
      <RadixDialog.Portal>
        <RadixDialog.Overlay className="dl-dialog-overlay" />
        <RadixDialog.Content
          className={cx("dl-dialog", size === "lg" && "dl-dialog--lg")}
          {...(description === undefined ? { "aria-describedby": undefined } : {})}
        >
          <div className="dl-dialog__header">
            <div className="dl-dialog__titles">
              <RadixDialog.Title className="dl-dialog__title">{title}</RadixDialog.Title>
              {description !== undefined && (
                <RadixDialog.Description className="dl-dialog__description">
                  {description}
                </RadixDialog.Description>
              )}
            </div>
            <RadixDialog.Close asChild>
              <Button
                variant="ghost"
                size="sm"
                iconOnly
                icon={<X />}
                aria-label="Close"
                className="dl-dialog__close"
              />
            </RadixDialog.Close>
          </div>
          {children !== undefined && <div className="dl-dialog__body">{children}</div>}
          {footer !== undefined && <div className="dl-dialog__footer">{footer}</div>}
        </RadixDialog.Content>
      </RadixDialog.Portal>
    </RadixDialog.Root>
  );
}
