import { useEffect, useState } from "react";
import * as api from "../api/client";
import { ErrorBanner } from "../components/ErrorBanner";
import type { ApiError, OpenAIState } from "../types";

interface SettingsPageProps {
  // Le flux "Générateur" garde sa propre copie du solde (affichée sur la
  // tuile GPT Image 2) — sans ce callback, une modification ici resterait
  // invisible tant qu'aucune génération OpenAI n'a eu lieu.
  onBalanceUpdated: () => void;
}

export function SettingsPage({ onBalanceUpdated }: SettingsPageProps) {
  const [state, setState] = useState<OpenAIState | null>(null);
  const [balanceInput, setBalanceInput] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);

  useEffect(() => {
    api
      .getOpenAIBalance()
      .then((data) => {
        setState(data);
        setBalanceInput(data.balance_usd.toFixed(2));
      })
      .catch((err: ApiError) => setError(err));
  }, []);

  async function handleSave(event: React.FormEvent) {
    event.preventDefault();
    const parsed = Number(balanceInput);
    if (Number.isNaN(parsed) || parsed < 0) return;

    setSaving(true);
    setError(null);
    try {
      const data = await api.putOpenAIBalance(parsed);
      setState(data);
      setBalanceInput(data.balance_usd.toFixed(2));
      onBalanceUpdated();
    } catch (err) {
      setError(err as ApiError);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="settings-page">
      <h2>Settings</h2>
      <p className="settings-page__intro">
        GPT Image 2 balance is estimated locally — this app has no way to read your real OpenAI
        account balance. Update it here after topping up your OpenAI account.
      </p>

      {error && <ErrorBanner error={error} />}

      <form className="card settings-page__balance-card" onSubmit={handleSave}>
        <label htmlFor="openai-balance">Current OpenAI balance (USD)</label>
        <div className="settings-page__balance-row">
          <input
            id="openai-balance"
            type="number"
            min={0}
            step={0.01}
            value={balanceInput}
            onChange={(event) => setBalanceInput(event.target.value)}
            disabled={!state || saving}
          />
          <button type="submit" className="btn btn--accent2 btn--sm" disabled={!state || saving}>
            {saving ? "Saving…" : "Save"}
          </button>
        </div>
      </form>

      {state && (
        <div className="card settings-page__pricing-card">
          <p className="settings-page__section-label">Pricing (estimated, read-only)</p>
          <p className="settings-page__pricing-line">
            ~${state.estimated_cost_per_generation_usd.toFixed(2)} per generation (1024×1024,
            medium quality)
          </p>
          <ul className="settings-page__pricing-detail">
            <li>${(state.price_per_text_input_token_usd * 1_000_000).toFixed(2)} / 1M text input tokens</li>
            <li>${(state.price_per_image_input_token_usd * 1_000_000).toFixed(2)} / 1M image input tokens</li>
            <li>
              ${(state.price_per_cached_image_input_token_usd * 1_000_000).toFixed(2)} / 1M cached
              image input tokens
            </li>
            <li>${(state.price_per_output_token_usd * 1_000_000).toFixed(2)} / 1M output tokens</li>
          </ul>
          <p className="settings-page__pricing-note">
            The real cost is calculated from the tokens actually used by each generation, and
            deducted from your balance automatically — this per-generation figure is only an
            estimate shown before you generate.
          </p>
        </div>
      )}
    </div>
  );
}
