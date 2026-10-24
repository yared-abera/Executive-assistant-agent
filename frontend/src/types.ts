export type AgentLogType = "thought" | "action" | "observation" | "final_answer";

export interface AgentLogEntry {
  type: AgentLogType | string;
  detail?: string;
  tool?: string;
  arguments?: Record<string, unknown>;
  result?: string;
}

export interface PendingAction {
  id: number;
  action_type: string;
  title: string;
  summary: string;
  payload: Record<string, unknown>;
  status: string;
  result?: string;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface CalendarEvent {
  id?: string;
  summary: string;
  start: string;
  end: string;
  attendees?: string[];
  status?: string;
  source?: string;
}

export interface AgentDonePayload {
  final_response?: string | null;
  logs?: AgentLogEntry[];
  pending_actions?: PendingAction[];
  error?: string | null;
}

export interface AppNotification {
  type: string;
  title?: string;
  summary?: string;
  item?: unknown;
}

export interface ApiErrorBody {
  error?: string;
  detail?: string;
}
