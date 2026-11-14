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

describe("TierChip", () => {
  it('TierChip renders the plain label "Reassign today" for reassign', () => {
    render(<TierChip tier="reassign" />);
    expect(screen.getByText("Reassign today")).toBeInTheDocument();
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
