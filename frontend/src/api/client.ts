import type {
  ApiErrorBody,
  CalendarEvent,
  PendingAction,
} from "../types";

const API_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers || {}),
    },
    ...init,
  });

  const data = (await res.json().catch(() => ({}))) as T & ApiErrorBody;
  if (!res.ok) {
    const message = data.error || data.detail || `Request failed (${res.status})`;
    throw new Error(message);
  }
  return data;
}

export function fetchCalendarEvents(date: string) {
  return request<{ date: string; events: CalendarEvent[] }>(
    `/api/calendar/events/?date=${encodeURIComponent(date)}`,
  );
}

export function savePreference(preference: string) {
  return request<{ status: string; message: string; preference: string }>(
    "/api/agent/preference/",
    {
      method: "POST",
      body: JSON.stringify({ preference }),
    },
  );
}

export function fetchPending(status = "pending") {
  return request<{ items: PendingAction[] }>(
    `/api/agent/pending/?status=${encodeURIComponent(status)}`,
  );
}

export function approvePending(id: number) {
  return request<{ status: string; result: string; item?: PendingAction }>(
    `/api/agent/pending/${id}/approve/`,
    { method: "POST", body: "{}" },
  );
}

export function rejectPending(id: number) {
  return request<{ status: string; result: string; item?: PendingAction }>(
    `/api/agent/pending/${id}/reject/`,
    { method: "POST", body: "{}" },
  );
}

export { API_URL };
