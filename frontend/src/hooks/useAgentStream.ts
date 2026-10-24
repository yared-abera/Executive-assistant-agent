import { useCallback, useEffect, useState } from "react";
import { getSocket } from "../realtime/socket";
import type { AgentDonePayload, AgentLogEntry } from "../types";

export function useAgentStream() {
  const [logs, setLogs] = useState<AgentLogEntry[]>([]);
  const [running, setRunning] = useState(false);
  const [finalResponse, setFinalResponse] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    const socket = getSocket();

    const onConnect = () => setConnected(true);
    const onDisconnect = () => setConnected(false);
    const onStatus = () => {
      setRunning(true);
      setError(null);
    };
    const onLog = (entry: AgentLogEntry) => {
      setLogs((prev) => [...prev, entry]);
    };
    const onDone = (payload: AgentDonePayload) => {
      setRunning(false);
      if (payload.logs?.length) {
        setLogs(payload.logs);
      }
      setFinalResponse(payload.final_response ?? null);
      setError(payload.error ?? null);
    };

    socket.on("connect", onConnect);
    socket.on("disconnect", onDisconnect);
    socket.on("connected", onConnect);
    socket.on("agent_status", onStatus);
    socket.on("agent_log", onLog);
    socket.on("agent_done", onDone);

    if (socket.connected) setConnected(true);

    return () => {
      socket.off("connect", onConnect);
      socket.off("disconnect", onDisconnect);
      socket.off("connected", onConnect);
      socket.off("agent_status", onStatus);
      socket.off("agent_log", onLog);
      socket.off("agent_done", onDone);
    };
  }, []);

  const runCommand = useCallback((command: string) => {
    const trimmed = command.trim();
    if (!trimmed) return;
    setLogs([]);
    setFinalResponse(null);
    setError(null);
    setRunning(true);
    getSocket().emit("run_command", { command: trimmed });
  }, []);

  return {
    logs,
    running,
    finalResponse,
    error,
    connected,
    runCommand,
  };
}
