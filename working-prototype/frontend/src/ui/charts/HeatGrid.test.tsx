// @vitest-environment jsdom
import "@testing-library/jest-dom/vitest";
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it } from "vitest";
import { HeatGrid } from "./HeatGrid";

afterEach(() => {
  cleanup();
});

describe("HeatGrid", () => {
  it("is a single tab stop and moves between cells with the arrow keys", async () => {
    const user = userEvent.setup();
    render(
      <>
        <button type="button">Before</button>
        <HeatGrid
          label="Reassign rate"
          rows={["Gang 1", "Gang 2"]}
          columns={["Mon", "Tue"]}
          values={[
            [0.1, 0.2],
            [null, 0.4],
          ]}
          formatValue={(v) => `${Math.round(v * 100)}%`}
        />
        <button type="button">After</button>
      </>,
    );
    await user.click(screen.getByRole("button", { name: "Before" }));
    await user.tab();
    expect(screen.getByRole("gridcell", { name: "Gang 1, Mon: 10%" })).toHaveFocus();

    await user.keyboard("{ArrowRight}");
    expect(screen.getByRole("gridcell", { name: "Gang 1, Tue: 20%" })).toHaveFocus();
    await user.keyboard("{ArrowDown}{ArrowLeft}");
    expect(screen.getByRole("gridcell", { name: "Gang 2, Mon: hidden" })).toHaveFocus();

    await user.tab();
    expect(screen.getByRole("button", { name: "After" })).toHaveFocus();
  });
});
