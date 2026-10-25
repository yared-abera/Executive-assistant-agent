import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const handlers: Record<string, (...args: unknown[]) => void> = {};
const emit = vi.fn();

vi.mock("../realtime/socket", () => ({
  getSocket: () => ({
    connected: true,
    on: (event: string, cb: (...args: unknown[]) => void) => {
      handlers[event] = cb;
    },
    off: vi.fn(),
    emit,
  }),
}));

import { useAgentStream } from "./useAgentStream";

describe("useAgentStream", () => {
  beforeEach(() => {
    emit.mockClear();
    for (const key of Object.keys(handlers)) delete handlers[key];
  });

  it("emits run_command and collects logs until agent_done", () => {
    const { result } = renderHook(() => useAgentStream());

    act(() => {
      handlers.connected?.({ sid: "1" });
      result.current.runCommand("Book a meeting");
    });

    expect(emit).toHaveBeenCalledWith("run_command", { command: "Book a meeting" });
    expect(result.current.running).toBe(true);

    act(() => {
      handlers.agent_log?.({ type: "thought", detail: "Checking calendar" });
      handlers.agent_done?.({
        final_response: "Done",
        logs: [{ type: "final_answer", detail: "Done" }],
        pending_actions: [{ id: 1, title: "Approve" }],
      });
    });

    expect(result.current.running).toBe(false);
    expect(result.current.finalResponse).toBe("Done");
    expect(result.current.logs.some((l) => l.type === "final_answer")).toBe(true);
  });
});
