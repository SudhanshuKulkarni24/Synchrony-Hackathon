import { useEffect, useState } from "react";
import { Activity, ArrowUpRight, ShieldAlert, ShieldCheck } from "lucide-react";

const API_URL = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000";

type ScoreResponse = {
  decision_id: string;
  correlation_id: string;
  decision: string;
  combined_risk: number;
  reason_codes: string[];
  rule_version: string;
  feature_schema_version: string;
  model_version: string;
  model_fallback: boolean;
};

type CaseRecord = {
  case_id: string;
  decision_id: string;
  status: "OPEN" | "CLOSED";
  outcome: string | null;
  reason_codes: string[];
  created_at: string;
  updated_at: string;
};

const initialSignals = {
  applications_last_24h: 1,
  is_new_device: false,
  identity_match_score: 0.96,
  device_account_count: 1,
  payment_account_count: 1,
  ip_risk_score: 0.08,
};

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!response.ok) throw new Error(`API request failed (${response.status})`);
  return response.json() as Promise<T>;
}

function App() {
  const [signals, setSignals] = useState(initialSignals);
  const [result, setResult] = useState<ScoreResponse | null>(null);
  const [cases, setCases] = useState<CaseRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadCases = async () => {
    try {
      setCases(await request<CaseRecord[]>("/api/v1/cases"));
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to load cases");
    }
  };

  useEffect(() => {
    void loadCases();
  }, []);

  const scoreApplication = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await request<ScoreResponse>("/api/v1/fraud/score", {
        method: "POST",
        body: JSON.stringify({ ...signals, correlation_id: crypto.randomUUID() }),
      });
      setResult(response);
      await loadCases();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to score application");
    } finally {
      setLoading(false);
    }
  };

  const updateCase = async (caseId: string, outcome: string) => {
    try {
      await request(`/api/v1/cases/${caseId}`, {
        method: "PATCH",
        body: JSON.stringify({ status: "CLOSED", outcome }),
      });
      await loadCases();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to update case");
    }
  };

  const setSignal = (key: keyof typeof signals, value: string | boolean) => {
    setSignals((current) => ({
      ...current,
      [key]: typeof value === "boolean" ? value : Number(value),
    }));
  };

  const openCases = cases.filter((item) => item.status === "OPEN").length;

  return (
    <main className="shell">
      <header className="masthead">
        <div className="brand-lockup">
          <div className="brand-mark"><ShieldCheck size={20} /></div>
          <div><p className="overline">Digital lending intelligence</p><h1>Sentinel</h1></div>
        </div>
        <div className="status-pill"><span className="pulse" /> Scoring engine online</div>
      </header>

      <section className="hero-copy">
        <div><p className="overline accent">Live risk command center</p><h2>Make the right call<br /><em>before loss lands.</em></h2></div>
        <p className="hero-note">A transparent decision layer for fast, explainable lending risk assessment.</p>
      </section>

      {error && <div className="error-banner">{error}</div>}

      <section className="workspace-grid">
        <article className="panel simulator-panel">
          <div className="panel-heading"><div><p className="overline">01 / Decision simulator</p><h3>Test a lending event</h3></div><Activity size={19} /></div>
          <div className="field-grid">
            <label>Applications / 24h<input type="number" min="0" value={signals.applications_last_24h} onChange={(event) => setSignal("applications_last_24h", event.target.value)} /></label>
            <label>Identity match<input type="number" min="0" max="1" step="0.01" value={signals.identity_match_score} onChange={(event) => setSignal("identity_match_score", event.target.value)} /></label>
            <label>Accounts / device<input type="number" min="1" value={signals.device_account_count} onChange={(event) => setSignal("device_account_count", event.target.value)} /></label>
            <label>Accounts / payment<input type="number" min="1" value={signals.payment_account_count} onChange={(event) => setSignal("payment_account_count", event.target.value)} /></label>
            <label className="wide">Network risk <span>{signals.ip_risk_score.toFixed(2)}</span><input type="range" min="0" max="1" step="0.01" value={signals.ip_risk_score} onChange={(event) => setSignal("ip_risk_score", event.target.value)} /></label>
            <label className="toggle-row"><input type="checkbox" checked={signals.is_new_device} onChange={(event) => setSignal("is_new_device", event.target.checked)} /><span>New device detected</span></label>
          </div>
          <button className="primary-button" onClick={scoreApplication} disabled={loading}>{loading ? "Evaluating..." : "Evaluate application"}<ArrowUpRight size={17} /></button>
        </article>

        <article className={`panel result-panel ${result ? "has-result" : ""}`}>
          <div className="panel-heading"><div><p className="overline">02 / Decision signal</p><h3>{result ? "Assessment complete" : "Awaiting assessment"}</h3></div>{result?.decision === "DECLINE" ? <ShieldAlert size={19} /> : <ShieldCheck size={19} />}</div>
          {result ? <>
            <div className={`decision-label decision-${result.decision.toLowerCase()}`}>{result.decision.replace("_", " ")}</div>
            <div className="risk-meter"><div className="meter-head"><span>Combined risk</span><strong>{Math.round(result.combined_risk * 100)}%</strong></div><div className="meter-track"><div style={{ width: `${result.combined_risk * 100}%` }} /></div></div>
            <div className="evidence"><p className="overline">Evidence</p>{result.reason_codes.length ? result.reason_codes.map((reason) => <span key={reason}>{reason.replaceAll("_", " ")}</span>) : <span className="quiet">No rule flags detected</span>}</div>
            <dl className="metadata"><div><dt>Model</dt><dd>{result.model_version}</dd></div><div><dt>Decision ID</dt><dd>{result.decision_id.slice(0, 12)}...</dd></div></dl>
          </> : <div className="empty-result"><ShieldCheck size={38} /><p>Configure signals and run an assessment to see the model evidence.</p></div>}
        </article>
      </section>

      <section className="panel queue-panel">
        <div className="panel-heading"><div><p className="overline">03 / Operations queue</p><h3>Review cases <span className="count-badge">{openCases} open</span></h3></div><button className="text-button" onClick={() => void loadCases()}>Refresh</button></div>
        {cases.length === 0 ? <p className="quiet queue-empty">No review cases yet. Suspicious applications will appear here.</p> : <div className="case-list">{cases.map((item) => <div className="case-row" key={item.case_id}><div><strong>{item.case_id.slice(0, 12)}</strong><p>{item.reason_codes.join(" · ") || "Model threshold"}</p></div><span className={`case-status ${item.status.toLowerCase()}`}>{item.status}</span>{item.status === "OPEN" && <select defaultValue="" onChange={(event) => event.target.value && void updateCase(item.case_id, event.target.value)}><option value="" disabled>Resolve...</option><option value="CONFIRMED_FRAUD">Confirmed fraud</option><option value="LEGITIMATE">Legitimate</option><option value="INCONCLUSIVE">Inconclusive</option></select>}</div>)}</div>}
      </section>
    </main>
  );
}

export default App;