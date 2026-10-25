import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";
import {
  deletePreference,
  fetchPreferences,
  savePreference,
} from "../api/client";
import type { StoredPreference } from "../types";

const CHIPS = [
  "No meetings before 10 AM",
  "No meetings on Monday",
  "15-minute buffer between meetings",
  "Prefer client calls over internal syncs when conflicted",
];

export function PreferenceForm() {
  const [preference, setPreference] = useState(CHIPS[0]);
  const [items, setItems] = useState<StoredPreference[]>([]);
  const [busy, setBusy] = useState(false);
  const [loadingList, setLoadingList] = useState(true);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoadingList(true);
    try {
      const data = await fetchPreferences();
      setItems(data.items || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load preferences");
    } finally {
      setLoadingList(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setMessage(null);
    setError(null);
    try {
      const res = await savePreference(preference.trim());
      setMessage(res.message || "Preference saved");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save preference");
    } finally {
      setBusy(false);
    }
  }

  async function onDelete(id: number) {
    setBusy(true);
    setMessage(null);
    setError(null);
    try {
      const res = await deletePreference(id);
      setMessage(res.message || "Preference deleted");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete preference");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="panel order-prefs" aria-labelledby="prefs-heading">
      <h2 id="prefs-heading">Preferences (RAG)</h2>
      <p className="muted">
        Stored in Supabase. The agent reminds you of these rules when scheduling — delete a
        rule here if you want to allow that day or time again.
      </p>
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

      <div className="pref-list" aria-live="polite">
        <h3 className="pref-list-title">Saved preferences</h3>
        {loadingList && <p className="muted">Loading…</p>}
        {!loadingList && items.length === 0 && (
          <p className="muted">No saved preferences yet.</p>
        )}
        <ul className="pref-items">
          {items.map((item) => (
            <li key={item.id} className="pref-item">
              <span className="pref-item-text">{item.content}</span>
              <button
                type="button"
                className="btn btn-danger"
                disabled={busy}
                onClick={() => void onDelete(item.id)}
              >
                Delete
              </button>
            </li>
          ))}
        </ul>
      </div>

      {message && <div className="success-banner">{message}</div>}
      {error && <div className="error-banner">{error}</div>}
    </section>
  );
}
