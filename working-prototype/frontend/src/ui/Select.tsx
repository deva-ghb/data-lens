import * as RadixSelect from "@radix-ui/react-select";
import { Check, ChevronDown, ChevronUp } from "lucide-react";
import { cx } from "./cx";
import "./ui.css";

export type SelectOption = { value: string; label: string; hint?: string; disabled?: boolean };

export type SelectProps = {
  value: string | undefined;
  onValueChange: (value: string) => void;
  options: SelectOption[];
  placeholder?: string;
  disabled?: boolean;
  id?: string;
  name?: string;
  className?: string;
  invalid?: boolean;
  "aria-label"?: string;
  "aria-labelledby"?: string;
  "aria-describedby"?: string;
};

export function Select({
  value,
  onValueChange,
  options,
  placeholder = "Choose one",
  disabled = false,
  id,
  name,
  className,
  invalid = false,
  ...aria
}: SelectProps) {
  return (
    <RadixSelect.Root
      value={value === "" ? undefined : value}
      onValueChange={onValueChange}
      disabled={disabled}
      name={name}
    >
      <RadixSelect.Trigger
        id={id}
        className={cx("dl-control", "dl-select-trigger", className)}
        aria-invalid={invalid || undefined}
        {...aria}
      >
        <span className="dl-select-trigger__value">
          <RadixSelect.Value placeholder={placeholder} />
        </span>
        <RadixSelect.Icon className="dl-select-trigger__icon">
          <ChevronDown aria-hidden="true" />
        </RadixSelect.Icon>
      </RadixSelect.Trigger>
      <RadixSelect.Portal>
        <RadixSelect.Content
          className="dl-popover dl-select-content"
          position="popper"
          side="bottom"
          align="start"
          sideOffset={4}
          collisionPadding={8}
        >
          <RadixSelect.ScrollUpButton className="dl-select-scroll">
            <ChevronUp aria-hidden="true" />
          </RadixSelect.ScrollUpButton>
          <RadixSelect.Viewport className="dl-select-viewport">
            {options.map((option) => (
              <RadixSelect.Item
                key={option.value}
                value={option.value}
                disabled={option.disabled}
                className="dl-option"
              >
                <span className="dl-option__body">
                  <RadixSelect.ItemText>
                    <span className="dl-option__label">{option.label}</span>
                  </RadixSelect.ItemText>
                  {option.hint !== undefined && (
                    <span className="dl-option__hint">{option.hint}</span>
                  )}
                </span>
                <span className="dl-option__check">
                  <RadixSelect.ItemIndicator>
                    <Check aria-hidden="true" />
                  </RadixSelect.ItemIndicator>
                </span>
              </RadixSelect.Item>
            ))}
          </RadixSelect.Viewport>
          <RadixSelect.ScrollDownButton className="dl-select-scroll">
            <ChevronDown aria-hidden="true" />
          </RadixSelect.ScrollDownButton>
        </RadixSelect.Content>
      </RadixSelect.Portal>
    </RadixSelect.Root>
  );
}
