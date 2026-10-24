import type { PendingAction } from "../types";

interface Props {
  items: PendingAction[];
  loading: boolean;
  error: string | null;
  busyId: number | null;
  onApprove: (id: number) => void;
  onReject: (id: number) => void;
}

export function PendingApprovals({
  items,
  loading,
  error,
  busyId,
  onApprove,
  onReject,
}: Props) {
  return (
    <section className="panel order-approvals" aria-labelledby="approvals-heading">
      <h2 id="approvals-heading">Approvals</h2>
      <p className="muted">One-click execute for proposed bookings and reschedule emails.</p>
      {loading && <p className="empty">Loading…</p>}
      {error && <div className="error-banner">{error}</div>}
      {!loading && items.length === 0 && (
        <p className="empty">No pending actions. Conflict proposals and declines appear here.</p>
      )}
      <ul className="approval-list">
        {items.map((item) => (
          <li key={item.id} className="approval-item new">
            <strong>{item.title}</strong>
            <p className="muted" style={{ margin: "0.35rem 0 0" }}>
              {item.summary}
            </p>
            <div className="approval-actions">
              <button
                type="button"
                className="btn btn-ok"
                disabled={busyId === item.id}
                onClick={() => onApprove(item.id)}
              >
                Approve
              </button>
              <button
                type="button"
                className="btn btn-danger"
                disabled={busyId === item.id}
                onClick={() => onReject(item.id)}
              >
                Reject
              </button>
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
