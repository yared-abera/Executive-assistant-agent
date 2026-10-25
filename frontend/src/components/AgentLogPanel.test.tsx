import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { AgentLogPanel } from "./AgentLogPanel";

describe("AgentLogPanel", () => {
  it("shows empty state", () => {
    render(<AgentLogPanel logs={[]} running={false} />);
    expect(screen.getByText(/run a command/i)).toBeInTheDocument();
  });

  it("renders thought action observation final_answer for UI balance", () => {
    render(
      <AgentLogPanel
        running={false}
        logs={[
          { type: "thought", detail: "Retrieved rules" },
          { type: "action", tool: "check_calendar_conflicts", arguments: { date_str: "2026-10-26" } },
          { type: "observation", result: "No events" },
          { type: "final_answer", detail: "All clear." },
        ]}
      />,
    );
    expect(screen.getByText(/retrieved rules/i)).toBeInTheDocument();
    expect(screen.getByText(/check_calendar_conflicts/i)).toBeInTheDocument();
    expect(screen.getByText(/no events/i)).toBeInTheDocument();
    expect(screen.getByText(/all clear/i)).toBeInTheDocument();
  });
});
