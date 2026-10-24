import { useState } from "react";
import type { FormEvent } from "react";
import { savePreference } from "../api/client";

const CHIPS = [
  "No meetings before 10 AM",
  "15-minute buffer between meetings",
  "Prefer client calls over internal syncs when conflicted",
];

export function PreferenceForm() {
  const [preference, setPreference] = useState(CHIPS[0]);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setMessage(null);
    setError(null);
    try {
      const res = await savePreference(preference.trim());
      setMessage(res.message || "Preference saved");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save preference");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="panel order-prefs" aria-labelledby="prefs-heading">
      <h2 id="prefs-heading">Preferences (RAG)</h2>
      <p className="muted">Stored in Supabase for future scheduling context.</p>
      <div className="chips">
        {CHIPS.map((c) => (
          <button key={c} type="button" className="chip" onClick={() => setPreference(c)}>
            {c}
          </button>
        ))}
      </div>
      <form onSubmit={onSubmit}>
        <div className="field">
          <label htmlFor="pref">Executive rule</label>
          <textarea
            id="pref"
            value={preference}
            onChange={(e) => setPreference(e.target.value)}
            rows={3}
          />
        </div>
        <button className="btn btn-primary" type="submit" disabled={busy || !preference.trim()}>
          {busy ? "Saving…" : "Save preference"}
        </button>
      </form>
      {message && <div className="success-banner">{message}</div>}
      {error && <div className="error-banner">{error}</div>}
    </section>
  );
}
