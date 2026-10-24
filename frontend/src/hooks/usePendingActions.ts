import { useCallback, useEffect, useState } from "react";
import {
  approvePending,
  fetchPending,
  rejectPending,
} from "../api/client";
import { getSocket } from "../realtime/socket";
import type { AppNotification, PendingAction } from "../types";

export function usePendingActions() {
  const [items, setItems] = useState<PendingAction[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [toasts, setToasts] = useState<AppNotification[]>([]);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchPending("pending");
      setItems(data.items || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load approvals");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  useEffect(() => {
    const socket = getSocket();

    const onPending = (item: PendingAction) => {
      setItems((prev) => {
        if (prev.some((p) => p.id === item.id)) {
          return prev.map((p) => (p.id === item.id ? item : p));
        }
        return [item, ...prev];
      });
    };

    const onNotification = (n: AppNotification) => {
      setToasts((prev) => [...prev, n]);
      if (n.type === "pending_action" && n.item) {
        onPending(n.item as PendingAction);
      }
    };

    const onDone = (payload: { pending_actions?: PendingAction[] }) => {
      if (payload.pending_actions?.length) {
        setItems((prev) => {
          const map = new Map(prev.map((p) => [p.id, p]));
          for (const item of payload.pending_actions!) {
            map.set(item.id, item);
          }
          return Array.from(map.values()).filter((p) => p.status === "pending");
        });
      }
    };

    socket.on("pending_action", onPending);
    socket.on("notification", onNotification);
    socket.on("agent_done", onDone);

    return () => {
      socket.off("pending_action", onPending);
      socket.off("notification", onNotification);
      socket.off("agent_done", onDone);
    };
  }, []);

  const dismissToast = useCallback((index: number) => {
    setToasts((prev) => prev.filter((_, i) => i !== index));
  }, []);

  const approve = useCallback(async (id: number) => {
    setBusyId(id);
    setError(null);
    try {
      await approvePending(id);
      setItems((prev) => prev.filter((p) => p.id !== id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Approve failed");
    } finally {
      setBusyId(null);
    }
  }, []);

  const reject = useCallback(async (id: number) => {
    setBusyId(id);
    setError(null);
    try {
      await rejectPending(id);
      setItems((prev) => prev.filter((p) => p.id !== id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Reject failed");
    } finally {
      setBusyId(null);
    }
  }, []);

  return {
    items,
    loading,
    error,
    busyId,
    toasts,
    dismissToast,
    refresh,
    approve,
    reject,
  };
}
