// @vitest-environment jsdom
import "@testing-library/jest-dom/vitest";
import { act, cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { ToastProvider, useToast, type ToastInput } from "./Toast";

afterEach(() => {
  cleanup();
});

let show: (toast: ToastInput) => void = () => undefined;

function Capture() {
  show = useToast();
  return null;
}

describe("Toast", () => {
  it("never drops a problem toast to make room for newer ones", () => {
    render(
      <ToastProvider>
        <Capture />
      </ToastProvider>,
    );
    act(() => {
      show({ title: "Clinic feed is late", tone: "critical" });
      show({ title: "Saved one", tone: "good" });
      show({ title: "Saved two", tone: "good" });
      show({ title: "Saved three", tone: "good" });
      show({ title: "Saved four", tone: "good" });
    });
    expect(screen.getByText("Clinic feed is late")).toBeInTheDocument();
    expect(screen.queryByText("Saved one")).not.toBeInTheDocument();
    expect(screen.getByText("Saved four")).toBeInTheDocument();
  });
});
