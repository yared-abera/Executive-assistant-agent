import { useEffect, useRef } from "react";
import type { AgentLogEntry } from "../types";

interface Props {
  logs: AgentLogEntry[];
  running: boolean;
}

function formatEntry(entry: AgentLogEntry): string {
  if (entry.type === "action") {
    const args = entry.arguments ? JSON.stringify(entry.arguments) : "";
    return `${entry.tool || "tool"} ${args}`.trim();
  }
  if (entry.type === "observation") return String(entry.result ?? "");
  return String(entry.detail ?? "");
}

export function AgentLogPanel({ logs, running }: Props) {
  const endRef = useRef<HTMLLIElement | null>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView?.({ behavior: "smooth", block: "nearest" });
  }, [logs]);

  return (
    <section className="panel order-logs" aria-labelledby="logs-heading">
      <h2 id="logs-heading">Agent activity</h2>
      <p className="muted">
        Live ReAct stream via Socket.IO {running ? "· running" : ""}
      </p>
      {logs.length === 0 ? (
        <p className="empty">Run a command to watch thoughts, tools, and observations.</p>
      ) : (
        <ul className="log-list">
          {logs.map((entry, i) => (
            <li
              key={`${entry.type}-${i}`}
              className="log-item"
              data-type={entry.type}
              ref={i === logs.length - 1 ? endRef : undefined}
            >
              <span className="log-type">{entry.type}</span>
              {formatEntry(entry)}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
