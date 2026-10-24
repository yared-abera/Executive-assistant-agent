import { useState } from "react";
import type { FormEvent } from "react";

interface Props {
  running: boolean;
  onRun: (command: string) => void;
}

const EXAMPLES = [
  "Check my schedule for tomorrow and propose a 30 min sync at 11:30 AM",
  "Schedule a 30 minute meeting with David next Monday at 2 PM",
  "Send a follow-up email to teammate@example.com about tomorrow's sync",
];

export function CommandConsole({ running, onRun }: Props) {
  const [command, setCommand] = useState(EXAMPLES[0]);

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    onRun(command);
  }

  return (
    <section className="panel order-command" aria-labelledby="command-heading">
      <h2 id="command-heading">Command</h2>
      <p className="muted">
        Natural language goes to the Gemini agent — calendar, preferences, and email tools run on the backend.
      </p>
      <form className="command-form" onSubmit={handleSubmit}>
        <textarea
          value={command}
          onChange={(e) => setCommand(e.target.value)}
          placeholder="e.g. Schedule a 30 min sync with David tomorrow at 11:30 AM"
          disabled={running}
          aria-label="Executive command"
        />
        <div className="chips" aria-label="Example commands">
          {EXAMPLES.map((ex) => (
            <button
              key={ex}
              type="button"
              className="chip"
              disabled={running}
              onClick={() => setCommand(ex)}
            >
              {ex.slice(0, 42)}…
            </button>
          ))}
        </div>
        <div className="command-actions">
          <button className="btn btn-primary" type="submit" disabled={running || !command.trim()}>
            {running ? "Agent working…" : "Run command"}
          </button>
        </div>
      </form>
    </section>
  );
}
