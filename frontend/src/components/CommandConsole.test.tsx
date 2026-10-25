import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { CommandConsole } from "./CommandConsole";

afterEach(() => cleanup());

describe("CommandConsole", () => {
  it("submits the command text", async () => {
    const user = userEvent.setup();
    const onRun = vi.fn();
    render(<CommandConsole running={false} onRun={onRun} />);

    const box = screen.getByLabelText(/executive command/i);
    await user.clear(box);
    await user.type(box, "Schedule a sync tomorrow");
    await user.click(screen.getByRole("button", { name: /run command/i }));

    expect(onRun).toHaveBeenCalledWith("Schedule a sync tomorrow");
  });

  it("disables submit while agent is running", () => {
    render(<CommandConsole running={true} onRun={vi.fn()} />);
    expect(screen.getByRole("button", { name: /agent working/i })).toBeDisabled();
    expect(screen.getByLabelText(/executive command/i)).toBeDisabled();
  });
});
