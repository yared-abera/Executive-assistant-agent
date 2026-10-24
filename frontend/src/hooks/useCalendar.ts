import { useCallback, useEffect, useState } from "react";
import { fetchCalendarEvents } from "../api/client";
import type { CalendarEvent } from "../types";

function todayISO() {
  return new Date().toISOString().slice(0, 10);
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
