interface Props {
  connected: boolean;
}

export function ConnectionBadge({ connected }: Props) {
  return (
    <div
      className={`connection ${connected ? "live" : ""}`}
      title={connected ? "Socket.IO connected" : "Connecting…"}
    >
      <span className="dot" aria-hidden />
      {connected ? "Live" : "Offline"}
    </div>
  );
}
