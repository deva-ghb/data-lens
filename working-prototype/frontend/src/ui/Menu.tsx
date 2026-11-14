import * as RadixMenu from "@radix-ui/react-dropdown-menu";
import type { ReactElement, ReactNode } from "react";
import { cx } from "./cx";
import "./ui.css";

export type MenuItem =
  | {
      kind?: "item";
      label: string;
      onSelect: () => void;
      icon?: ReactNode;
      hint?: string;
      danger?: boolean;
      disabled?: boolean;
    }
  | { kind: "separator" }
  | { kind: "label"; label: string };

export type MenuProps = {
  /** The element that opens the menu, usually a Button. It must accept a ref. */
  trigger: ReactElement;
  items: MenuItem[];
  align?: "start" | "end";
  label?: string;
};

export function Menu({ trigger, items, align = "end", label }: MenuProps) {
  return (
    <RadixMenu.Root modal={false}>
      <RadixMenu.Trigger asChild>{trigger}</RadixMenu.Trigger>
      <RadixMenu.Portal>
        <RadixMenu.Content
          className="dl-popover dl-menu-content"
          align={align}
          side="bottom"
          sideOffset={4}
          collisionPadding={8}
          aria-label={label}
        >
          {items.map((item, index) => {
            if (item.kind === "separator") {
              return <RadixMenu.Separator key={`sep-${index}`} className="dl-menu-separator" />;
            }
            if (item.kind === "label") {
              return (
                <RadixMenu.Label key={`label-${index}`} className="dl-menu-label">
                  {item.label}
                </RadixMenu.Label>
              );
            }
            return (
              <RadixMenu.Item
                key={`${index}-${item.label}`}
                className={cx("dl-option", item.danger === true && "dl-option--danger")}
                disabled={item.disabled}
                onSelect={item.onSelect}
              >
                {item.icon !== undefined && (
                  <span className="dl-option__icon" aria-hidden="true">
                    {item.icon}
                  </span>
                )}
                <span className="dl-option__body">
                  <span className="dl-option__label">{item.label}</span>
                  {item.hint !== undefined && <span className="dl-option__hint">{item.hint}</span>}
                </span>
              </RadixMenu.Item>
            );
          })}
        </RadixMenu.Content>
      </RadixMenu.Portal>
    </RadixMenu.Root>
  );
}
