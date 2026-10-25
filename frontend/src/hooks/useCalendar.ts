import { useCallback, useEffect, useState } from "react";
import { fetchCalendarEvents } from "../api/client";
import type { CalendarEvent } from "../types";

/** Local calendar date (not UTC) so midnight near UTC+ offsets stays correct. */
function todayISO() {
  const now = new Date();
  const y = now.getFullYear();
  const m = String(now.getMonth() + 1).padStart(2, "0");
  const d = String(now.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

export function useCalendar(initialDate = todayISO()) {
  const [date, setDate] = useState(initialDate);
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async (d = date) => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchCalendarEvents(d);
      setEvents(data.events || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load calendar");
      setEvents([]);
    } finally {
      setLoading(false);
    }
  }, [date]);

  useEffect(() => {
    void refresh(date);
  }, [date, refresh]);

  return { date, setDate, events, loading, error, refresh };
}
