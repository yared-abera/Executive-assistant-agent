import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { SchedulePanel } from "./SchedulePanel";

describe("SchedulePanel", () => {
  it("lists live calendar events and refreshes", async () => {
    const user = userEvent.setup();
    const onRefresh = vi.fn();
    render(
      <SchedulePanel
        date="2026-10-26"
        events={[
          {
            id: "1",
            summary: "Team Sync",
            start: "2026-10-26T10:00:00",
            end: "2026-10-26T11:00:00",
          },
        ]}
        loading={false}
        error={null}
        onDateChange={vi.fn()}
        onRefresh={onRefresh}
      />,
    );

    expect(screen.getByText("Team Sync")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /refresh/i }));
    expect(onRefresh).toHaveBeenCalled();
  });

  it("shows empty calendar message", () => {
    render(
      <SchedulePanel
        date="2026-10-26"
        events={[]}
        loading={false}
        error={null}
        onDateChange={vi.fn()}
        onRefresh={vi.fn()}
      />,
    );
    expect(screen.getByText(/no events on this day/i)).toBeInTheDocument();
  });
});
