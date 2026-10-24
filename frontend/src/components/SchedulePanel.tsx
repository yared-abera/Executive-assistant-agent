import type { CalendarEvent } from "../types";

interface Props {
  date: string;
  events: CalendarEvent[];
  loading: boolean;
  error: string | null;
  onDateChange: (date: string) => void;
  onRefresh: () => void;
}

function formatRange(ev: CalendarEvent) {
  try {
    const start = new Date(ev.start);
    const end = new Date(ev.end);
    const opts: Intl.DateTimeFormatOptions = { hour: "numeric", minute: "2-digit" };
    return `${start.toLocaleTimeString([], opts)} – ${end.toLocaleTimeString([], opts)}`;
  } catch {
    return `${ev.start} – ${ev.end}`;
  }
}

export function SchedulePanel({
  date,
  events,
  loading,
  error,
  onDateChange,
  onRefresh,
}: Props) {
  return (
    <section className="panel order-schedule" aria-labelledby="schedule-heading">
      <h2 id="schedule-heading">Schedule</h2>
      <div className="field">
        <label htmlFor="schedule-date">Date</label>
        <input
          id="schedule-date"
          type="date"
          value={date}
          onChange={(e) => onDateChange(e.target.value)}
        />
      </div>
      <div className="command-actions">
        <button type="button" className="btn btn-ghost" onClick={onRefresh} disabled={loading}>
          {loading ? "Loading…" : "Refresh"}
        </button>
      </div>
      {error && <div className="error-banner">{error}</div>}
      {!error && events.length === 0 && !loading && (
        <p className="empty">No events on this day (live Google Calendar).</p>
      )}
      <ul className="event-list">
        {events.map((ev) => (
          <li key={ev.id || `${ev.start}-${ev.summary}`} className="event-item">
            <div className="event-time">{formatRange(ev)}</div>
            <strong>{ev.summary}</strong>
          </li>
        ))}
      </ul>
    </section>
  );
}
