import { afterEach, describe, expect, it, vi } from "vitest";
import {
  approvePending,
  deletePreference,
  fetchCalendarEvents,
  fetchPending,
  fetchPreferences,
  rejectPending,
  savePreference,
} from "./client";

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

function mockJson(data: unknown, ok = true, status = 200) {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok,
      status,
      json: async () => data,
    }),
  );
}

describe("api client", () => {
  it("fetches calendar events for a date", async () => {
    mockJson({
      date: "2026-10-26",
      events: [{ summary: "Sync", start: "2026-10-26T10:00:00", end: "2026-10-26T10:30:00" }],
    });
    const data = await fetchCalendarEvents("2026-10-26");
    expect(data.date).toBe("2026-10-26");
    expect(data.events).toHaveLength(1);
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/calendar/events/?date=2026-10-26"),
      expect.any(Object),
    );
  });

  it("saves a preference", async () => {
    mockJson(
      { status: "success", message: "Stored", preference: "No meetings before 10 AM" },
      true,
      201,
    );
    const data = await savePreference("No meetings before 10 AM");
    expect(data.status).toBe("success");
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/agent/preference/"),
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("lists and deletes preferences", async () => {
    mockJson({ items: [{ id: 3, content: "No meetings on monday" }] });
    const listed = await fetchPreferences();
    expect(listed.items[0].id).toBe(3);
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/agent/preferences/"),
      expect.any(Object),
    );

    mockJson({ status: "success", message: "Deleted preference: 'No meetings on monday'" });
    await expect(deletePreference(3)).resolves.toMatchObject({ status: "success" });
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/agent/preference/3/"),
      expect.objectContaining({ method: "DELETE" }),
    );
  });

  it("lists and mutates pending actions", async () => {
    mockJson({ items: [{ id: 1, title: "Approve", status: "pending" }] });
    const listed = await fetchPending();
    expect(listed.items[0].id).toBe(1);

    mockJson({ status: "executed", result: "ok" });
    await expect(approvePending(1)).resolves.toMatchObject({ status: "executed" });

    mockJson({ status: "rejected", result: "Rejected by user" });
    await expect(rejectPending(2)).resolves.toMatchObject({ status: "rejected" });
  });

  it("throws JSON error bodies", async () => {
    mockJson({ error: "No command provided" }, false, 400);
    await expect(savePreference("")).rejects.toThrow("No command provided");
  });
});
