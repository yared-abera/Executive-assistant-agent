import type { AppNotification } from "../types";

interface Props {
  toasts: AppNotification[];
  onDismiss: (index: number) => void;
}

export function NotificationToast({ toasts, onDismiss }: Props) {
  if (!toasts.length) return null;

  return (
    <div className="toast-stack" aria-live="polite">
      {toasts.map((t, i) => (
        <div key={`${t.type}-${i}`} className="toast">
          <strong>{t.title || t.type}</strong>
          {t.summary && <div style={{ marginTop: "0.25rem", opacity: 0.9 }}>{t.summary}</div>}
          <button type="button" onClick={() => onDismiss(i)}>
            Dismiss
          </button>
        </div>
      ))}
    </div>
  );
}
