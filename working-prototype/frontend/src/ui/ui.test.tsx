// @vitest-environment jsdom
import "@testing-library/jest-dom/vitest";
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { afterEach, beforeAll, describe, expect, it, vi } from "vitest";
import { AiSection, type AiDraft } from "./AiSection";
import { Select } from "./Select";
import { TierChip } from "./TierChip";

// jsdom does not implement pointer capture or scrolling, which Radix calls.
beforeAll(() => {
  const proto = window.HTMLElement.prototype as unknown as Record<string, unknown>;
  proto["hasPointerCapture"] ??= () => false;
  proto["releasePointerCapture"] ??= () => undefined;
  proto["setPointerCapture"] ??= () => undefined;
  proto["scrollIntoView"] ??= () => undefined;
});

afterEach(() => {
  cleanup();
});

const shiftOptions = [
  { value: "day", label: "Day shift", hint: "06:00 to 18:00" },
  { value: "night", label: "Night shift", hint: "18:00 to 06:00" },
  { value: "relief", label: "Relief crew" },
];

function ControlledSelect({ onChange }: { onChange: (value: string) => void }) {
  const [value, setValue] = useState("day");
  return (
    <Select
      aria-label="Shift"
      value={value}
      onValueChange={(next) => {
        setValue(next);
        onChange(next);
      }}
      options={shiftOptions}
    />
  );
}

describe("Select", () => {
  it("Select opens, shows options, keyboard selects with ArrowDown+Enter", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<ControlledSelect onChange={onChange} />);

    const trigger = screen.getByRole("combobox", { name: "Shift" });
    expect(trigger).toHaveTextContent("Day shift");

    await user.click(trigger);

    const options = await screen.findAllByRole("option");
    expect(options.map((option) => option.textContent)).toEqual([
      expect.stringContaining("Day shift"),
      expect.stringContaining("Night shift"),
      expect.stringContaining("Relief crew"),
    ]);

    await user.keyboard("{ArrowDown}");
    await user.keyboard("{Enter}");

    expect(onChange).toHaveBeenCalledWith("night");
    expect(screen.queryAllByRole("option")).toHaveLength(0);
    expect(screen.getByRole("combobox", { name: "Shift" })).toHaveTextContent("Night shift");
  });
});

describe("Select clearing", () => {
  it("shows the placeholder again when the parent resets the value to an empty string", async () => {
    const user = userEvent.setup();
    const errors = vi.spyOn(console, "error").mockImplementation(() => undefined);
    const props = {
      "aria-label": "Shift",
      onValueChange: vi.fn(),
      options: shiftOptions,
      placeholder: "Choose a shift",
    };
    const { rerender } = render(<Select {...props} value="" />);
    expect(screen.getByRole("combobox", { name: "Shift" })).toHaveTextContent("Choose a shift");

    await user.click(screen.getByRole("combobox", { name: "Shift" }));
    await user.click(await screen.findByRole("option", { name: /Night shift/ }));
    expect(props.onValueChange).toHaveBeenCalledWith("night");
    rerender(<Select {...props} value="night" />);
    expect(screen.getByRole("combobox", { name: "Shift" })).toHaveTextContent("Night shift");

    rerender(<Select {...props} value="" />);
    expect(screen.getByRole("combobox", { name: "Shift" })).toHaveTextContent("Choose a shift");
    expect(errors).not.toHaveBeenCalled();
    errors.mockRestore();
  });
});

describe("TierChip", () => {
  it('TierChip renders the plain label "Reassign today" for reassign', () => {
    render(<TierChip tier="reassign" />);
    expect(screen.getByText("Reassign today")).toBeInTheDocument();
  });

  it("uses the spec names for every tier", () => {
    const tiers = ["fit", "fit_with_controls", "reassign", "refer", "unknown"] as const;
    const labels = tiers.map((tier) => {
      const { container, unmount } = render(<TierChip tier={tier} />);
      const text = container.textContent;
      unmount();
      return text;
    });
    expect(labels).toEqual(["Fit", "Fit with controls", "Reassign today", "Refer", "Unknown"]);
  });
});

const unavailableDraft: AiDraft = {
  id: "draft-1",
  kind: "warning_summary",
  content: "",
  sure: [],
  unsure: [],
  would_change: [],
  confidence: 0,
  reasoning: { evidence: [], rules: [], inferences: [], rejected: [] },
  status: "unavailable",
};

describe("AiSection", () => {
  it('AiSection with status unavailable shows "Draft not available" and an editable text area', async () => {
    const user = userEvent.setup();
    const onConfirm = vi.fn();
    const onEdit = vi.fn();
    render(
      <AiSection
        draft={unavailableDraft}
        onConfirm={onConfirm}
        onEdit={onEdit}
        confirmLabel="Save summary"
      />,
    );

    expect(screen.getByText("Draft not available")).toBeInTheDocument();
    const textArea = screen.getByRole("textbox");
    expect(textArea).toBeEnabled();

    await user.type(textArea, "Crew rested at 14:00.");
    expect(textArea).toHaveValue("Crew rested at 14:00.");
    expect(onEdit).toHaveBeenLastCalledWith("Crew rested at 14:00.");
  });
});

const readyDraft: AiDraft = {
  ...unavailableDraft,
  id: "draft-2",
  content: "Move Arjun Pillai to the reefer gate from 13:00.",
  sure: ["Fourth night in a row"],
  confidence: 0.8,
  status: "draft",
};

describe("AiSection updates", () => {
  it("shows the new draft text when a different draft arrives", () => {
    const props = { onConfirm: vi.fn(), onEdit: vi.fn(), confirmLabel: "Save summary" };
    const { rerender } = render(<AiSection draft={unavailableDraft} {...props} />);
    expect(screen.getByRole("textbox")).toHaveValue("");

    rerender(<AiSection draft={readyDraft} {...props} />);
    expect(screen.getByRole("textbox")).toHaveValue(readyDraft.content);
    expect(screen.queryByText("Draft not available")).not.toBeInTheDocument();
  });

  it("enables confirm once text is typed and passes the typed text to onConfirm", async () => {
    const user = userEvent.setup();
    const onConfirm = vi.fn();
    render(
      <AiSection draft={unavailableDraft} onConfirm={onConfirm} onEdit={vi.fn()} confirmLabel="Save summary" />,
    );
    const confirm = screen.getByRole("button", { name: "Save summary" });
    expect(confirm).toBeDisabled();

    await user.type(screen.getByRole("textbox"), "Crew rested at 14:00.");
    expect(confirm).toBeEnabled();
    await user.click(confirm);
    expect(onConfirm).toHaveBeenCalledWith("Crew rested at 14:00.");
  });
});
