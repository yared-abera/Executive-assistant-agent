import { useEffect } from "react";
import { AgentLogPanel } from "../components/AgentLogPanel";
import { CommandConsole } from "../components/CommandConsole";
import { ConnectionBadge } from "../components/ConnectionBadge";
import { NotificationToast } from "../components/NotificationToast";
import { PendingApprovals } from "../components/PendingApprovals";
import { PreferenceForm } from "../components/PreferenceForm";
import { SchedulePanel } from "../components/SchedulePanel";
import { useAgentStream } from "../hooks/useAgentStream";
import { useCalendar } from "../hooks/useCalendar";
import { usePendingActions } from "../hooks/usePendingActions";

export function DashboardPage() {
  const agent = useAgentStream();
  const calendar = useCalendar();
  const pending = usePendingActions();

  useEffect(() => {
    if (!agent.running && agent.finalResponse) {
      void calendar.refresh();
      void pending.refresh();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- refresh only when a run completes
  }, [agent.running, agent.finalResponse]);

  async function handleApprove(id: number) {
    await pending.approve(id);
    await calendar.refresh();
  }

  return (
    <div className="app-shell">
      <header className="hero">
        <div className="hero-top">
          <div>
            <h1 className="brand">Executive Assistant</h1>
            <p className="tagline">
              Schedule meetings, apply long-term preferences, and approve actions — live with your Gemini agent.
            </p>
          </div>
          <ConnectionBadge connected={agent.connected} />
        </div>
      </header>

      <div className="workspace">
        <CommandConsole running={agent.running} onRun={agent.runCommand} />

        <PendingApprovals
          items={pending.items}
          loading={pending.loading}
          error={pending.error}
          busyId={pending.busyId}
          onApprove={handleApprove}
          onReject={pending.reject}
        />

        <AgentLogPanel logs={agent.logs} running={agent.running} />

        <SchedulePanel
          date={calendar.date}
          events={calendar.events}
          loading={calendar.loading}
          error={calendar.error}
          onDateChange={calendar.setDate}
          onRefresh={() => void calendar.refresh()}
        />

        <PreferenceForm />

        <section className="panel order-answer" aria-labelledby="answer-heading">
          <h2 id="answer-heading">Final answer</h2>
          {agent.error && <div className="error-banner">{agent.error}</div>}
          {!agent.error && !agent.finalResponse && (
            <p className="empty">The agent’s closing response will appear here.</p>
          )}
          {agent.finalResponse && (
            <div className="answer-body">{agent.finalResponse}</div>
          )}
        </section>
      </div>

      <NotificationToast toasts={pending.toasts} onDismiss={pending.dismissToast} />
    </div>
  );
}
