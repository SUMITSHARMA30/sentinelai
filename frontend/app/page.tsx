"use client";

import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
import { Activity, AlertTriangle, BadgeCheck, RefreshCw, Shield, Zap, X } from "lucide-react";
import { Area, AreaChart, CartesianGrid, Pie, PieChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

type Tx = {
  transaction_id: string; created_at: string; amount: number; currency: string;
  merchant_category: string; channel: string; country: string; fraud_probability: number;
  risk_level: "low" | "medium" | "high"; status: string; reasons: string[];
  account_age_days: number; transactions_last_hour: number; distance_from_home_km: number;
  device_new: boolean; analyst_label: string;
};

type Metrics = {
  total_transactions: number; high_risk: number; medium_risk: number; low_risk: number;
  confirmed_fraud: number; model_version: string;
};

type BenchmarkMetrics = {
  threshold: number; precision: number; recall: number; f1: number;
  average_precision_pr_auc: number; roc_auc: number;
  confusion_matrix: { true_negative: number; false_positive: number; false_negative: number; true_positive: number };
  model_name: string; dataset: string; dataset_rows: number; fraud_rows: number;
  fraud_prevalence: number; train_rows: number; test_rows: number;
  features: string[]; split: string; trained_at_utc: string; warning: string;
};

type BenchmarkResult = {
  model_version: string; fraud_probability: number; threshold: number;
  prediction: string; warning: string;
};

type StreamMetrics = {
  total_processed: number;
  fraud_review: number;
  legitimate: number;
  fraud_review_rate: number;
  latest_processed_at: string | null;
  source_note: string;
};

type StreamEvent = {
  event_id: string;
  source?: string;
  fraud_probability: number;
  threshold: number;
  prediction: string;
  actual_class?: number | null;
  model_version?: string;
  processed_at?: string;
};

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const COLORS = ["#64e6a6", "#ffc766", "#ff637d"];
const money = (n: number) => new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(n);
const time = (s: string) => new Date(s).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });

export default function Home() {
  const [items, setItems] = useState<Tx[]>([]);
  const [metrics, setMetrics] = useState<Metrics>({ total_transactions: 0, high_risk: 0, medium_risk: 0, low_risk: 0, confirmed_fraud: 0, model_version: "demo-v1" });
  const [risk, setRisk] = useState("all");
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState<Tx | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [online, setOnline] = useState(false);

  const [benchmark, setBenchmark] = useState<BenchmarkMetrics | null>(null);
  const [benchmarkResult, setBenchmarkResult] = useState<BenchmarkResult | null>(null);
  const [benchmarkError, setBenchmarkError] = useState("");
  const [benchmarkBusy, setBenchmarkBusy] = useState(false);
  const [benchmarkJson, setBenchmarkJson] = useState("");
  const [benchmarkThreshold, setBenchmarkThreshold] = useState(0.5);
  const [streamMetrics, setStreamMetrics] = useState<StreamMetrics | null>(null);
  const [streamEvents, setStreamEvents] = useState<StreamEvent[]>([]);
  const [streamError, setStreamError] = useState("");

  const refresh = useCallback(async () => {
    try {
      const [t, m] = await Promise.all([fetch(`${API}/transactions?limit=200`), fetch(`${API}/metrics`)]);
      if (!t.ok || !m.ok) throw new Error("API request failed");
      const td = await t.json();
      setItems(td.items || []);
      setMetrics(await m.json());
      setOnline(true);
      setError("");
    } catch {
      setOnline(false);
      setError(`Cannot reach API at ${API}. Start the FastAPI backend on port 8000.`);
    }
  }, []);

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, 4000);
    return () => clearInterval(id);
  }, [refresh]);

  const refreshStream = useCallback(async () => {
    try {
      const [metricsRes, eventsRes] = await Promise.all([
        fetch(`${API}/stream/metrics`, { cache: "no-store" }),
        fetch(`${API}/stream/transactions?limit=12`, { cache: "no-store" }),
      ]);
      if (!metricsRes.ok || !eventsRes.ok) throw new Error("Streaming API unavailable");
      const metricsData: StreamMetrics = await metricsRes.json();
      const eventsData = await eventsRes.json();
      setStreamMetrics(metricsData);
      setStreamEvents(eventsData.items || []);
      setStreamError("");
    } catch {
      setStreamError("Streaming data unavailable. Check that Kafka events have been consumed and MongoDB is reachable.");
    }
  }, []);

  useEffect(() => {
    refreshStream();
    const id = setInterval(refreshStream, 3000);
    return () => clearInterval(id);
  }, [refreshStream]);

  useEffect(() => {
    let cancelled = false;
    async function loadBenchmark() {
      try {
        const res = await fetch(`${API}/benchmark/metrics`);
        if (!res.ok) throw new Error("Metrics request failed");
        const data: BenchmarkMetrics = await res.json();
        if (!cancelled) {
          setBenchmark(data);
          setBenchmarkError("");
        }
      } catch {
        if (!cancelled) setBenchmarkError("Could not load benchmark metrics. Check the backend and /benchmark/metrics endpoint.");
      }
    }
    loadBenchmark();
    return () => { cancelled = true; };
  }, []);

  async function generate() {
    setBusy(true);
    setError("");
    const sample = {
      amount: [249, 1299, 24999, 78500, 550][Math.floor(Math.random() * 5)],
      currency: "INR",
      merchant_category: ["grocery", "electronics", "food", "online", "fuel"][Math.floor(Math.random() * 5)],
      channel: ["online", "pos", "mobile"][Math.floor(Math.random() * 3)],
      country: Math.random() < .9 ? "IN" : "US",
      account_age_days: Math.random() < .12 ? 3 : Math.floor(Math.random() * 2000) + 30,
      transactions_last_hour: Math.random() < .12 ? 7 : Math.floor(Math.random() * 4),
      distance_from_home_km: Math.random() < .12 ? 480 : Math.floor(Math.random() * 35),
      device_new: Math.random() < .2
    };
    try {
      const res = await fetch(`${API}/transactions`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(sample) });
      if (!res.ok) throw new Error("Transaction request failed");
      await res.json();
      await refresh();
    } catch {
      setError(`Could not create transaction. Check that the API is running at ${API}.`);
    } finally {
      setBusy(false);
    }
  }

  async function label(tx: Tx, value: string) {
    try {
      const res = await fetch(`${API}/transactions/${tx.transaction_id}/label?label=${value}`, { method: "PATCH" });
      if (!res.ok) throw new Error();
      setSelected(null);
      await refresh();
    } catch {
      setError("Unable to update analyst label. Check the backend logs.");
    }
  }

  async function scoreBenchmark() {
    setBenchmarkBusy(true);
    setBenchmarkError("");
    setBenchmarkResult(null);
    try {
      const input = JSON.parse(benchmarkJson);
      const res = await fetch(`${API}/benchmark/score?threshold=${benchmarkThreshold}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(input),
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail ? JSON.stringify(data.detail) : "Scoring request failed");
      }
      setBenchmarkResult(data);
    } catch (e) {
      setBenchmarkError(e instanceof Error ? e.message : "Invalid request. Paste a complete JSON row from the dataset.");
    } finally {
      setBenchmarkBusy(false);
    }
  }

  const filtered = useMemo(() => items.filter(x =>
    (risk === "all" || x.risk_level === risk) &&
    `${x.transaction_id} ${x.merchant_category} ${x.channel} ${x.country}`.toLowerCase().includes(search.toLowerCase())
  ), [items, risk, search]);

  const trend = useMemo(() => {
    const buckets = new Map<string, { time: string; low: number; medium: number; high: number }>();
    for (const tx of [...items].reverse()) {
      const key = new Date(tx.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
      const b = buckets.get(key) || { time: key, low: 0, medium: 0, high: 0 };
      b[tx.risk_level]++;
      buckets.set(key, b);
    }
    return [...buckets.values()].slice(-12);
  }, [items]);

  const pie = [{ name: "Low", value: metrics.low_risk }, { name: "Medium", value: metrics.medium_risk }, { name: "High", value: metrics.high_risk }];

  return <main className="shell cyber-shell">
    <div className="cyber-grid" aria-hidden="true" />
    <div className="scanline" aria-hidden="true" />
    <header className="topbar">
      <div className="brand"><div className="logo">S</div><div><div className="eyebrow">FINANCIAL CRIME INTELLIGENCE</div><h1>Sentinel<span style={{ color: "var(--cyan)" }}>AI</span></h1></div></div>
      <div className="live"><span className="dot" style={{ background: online ? "var(--green)" : "var(--red)" }} />{online ? "API CONNECTED" : "API DISCONNECTED"}</div>
    </header>

    <section className="hero">
      <div><div className="eyebrow">COMMAND CENTER / OVERVIEW</div><h2>Fraud intelligence, <span style={{ color: "var(--cyan)" }}>in real time.</span></h2><p>Monitor payment behavior, investigate risk signals, and review suspicious transactions.</p></div>
      <div className="actions"><button className="btn" onClick={refresh}><RefreshCw size={13} style={{ verticalAlign: "middle", marginRight: 7 }} />Refresh</button><button className="btn primary" onClick={generate} disabled={busy}><Zap size={14} style={{ verticalAlign: "middle", marginRight: 7 }} />{busy ? "Scoring..." : "Generate transaction"}</button></div>
    </section>

    {error && <div className="notice">{error}</div>}

    <section className="card benchmark-card" style={{ marginBottom: 20, padding: 20 }}>
      <div className="section-head"><h3>Trained Fraud Model Benchmark</h3><span>HELD-OUT TEST RESULTS</span></div>
      {benchmark ? <>
        <p style={{ color: "var(--muted)", fontSize: 12 }}>{benchmark.model_name} · {benchmark.dataset}</p>
        <section className="grid">
          <Metric icon={<Shield size={16} />} title="ROC-AUC" value={`${(benchmark.roc_auc * 100).toFixed(2)}%`} foot="Ranking performance" />
          <Metric icon={<Activity size={16} />} title="Fraud recall" value={`${(benchmark.recall * 100).toFixed(2)}%`} foot="Share of fraud cases detected" color="var(--green)" />
          <Metric icon={<AlertTriangle size={16} />} title="Fraud precision" value={`${(benchmark.precision * 100).toFixed(2)}%`} foot="Flagged cases that were fraud" color="var(--yellow)" />
          <Metric icon={<BadgeCheck size={16} />} title="F1 score" value={`${(benchmark.f1 * 100).toFixed(2)}%`} foot="Precision/recall balance" />
        </section>
        <div className="benchmark-summary">
          <span><strong>{benchmark.dataset_rows.toLocaleString("en-IN")}</strong> total dataset rows</span>
          <span><strong>{benchmark.test_rows.toLocaleString("en-IN")}</strong> held-out test rows</span>
          <span><strong>{benchmark.fraud_rows.toLocaleString("en-IN")}</strong> fraud cases in dataset</span>
          <span><strong>{(benchmark.average_precision_pr_auc * 100).toFixed(2)}%</strong> PR-AUC</span>
        </div>
      </> : <p>{benchmarkError || "Loading benchmark metrics..."}</p>}

      <h3 style={{ marginTop: 24, marginBottom: 8 }}>Score a benchmark transaction</h3>
      <div style={{ margin: "12px 0 16px", padding: 14, border: "1px solid var(--border, #253145)", borderRadius: 10 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
          <label htmlFor="benchmark-threshold" style={{ fontWeight: 700 }}>Decision threshold</label>
          <strong>{(benchmarkThreshold * 100).toFixed(0)}%</strong>
        </div>
        <input
          id="benchmark-threshold"
          type="range"
          min="0.1"
          max="0.9"
          step="0.05"
          value={benchmarkThreshold}
          onChange={e => setBenchmarkThreshold(Number(e.target.value))}
          style={{ width: "100%", marginTop: 12, accentColor: "var(--cyan)" }}
        />
        <div style={{ display: "flex", justifyContent: "space-between", color: "var(--muted)", fontSize: 11 }}>
          <span>10% · More alerts</span><span>90% · Fewer alerts</span>
        </div>
        <p style={{ color: "var(--muted)", fontSize: 12, marginBottom: 0 }}>
          Higher thresholds generally reduce alerts but can miss more fraud. This changes the prediction cutoff, not the model's probability.
        </p>
      </div>
      <p style={{ color: "var(--muted)", fontSize: 12, lineHeight: 1.6 }}>
        Paste one complete JSON object containing Time, V1 through V28, and Amount. Use a row from creditcard.csv and exclude the Class column. These are PCA-transformed benchmark features, not the INR demo transaction fields above.
      </p>
      <textarea
        value={benchmarkJson}
        onChange={e => setBenchmarkJson(e.target.value)}
        placeholder={'Paste the full dataset row as JSON, e.g. {"Time": 0, "V1":  ... }'}
        aria-label="Benchmark transaction JSON"
        rows={7}
        style={{ width: "100%", boxSizing: "border-box", padding: 12, background: "var(--bg)", color: "inherit", border: "1px solid var(--border, #253145)", borderRadius: 8, fontFamily: "monospace", fontSize: 12, marginTop: 8 }}
      />
      <button className="btn primary" onClick={scoreBenchmark} disabled={benchmarkBusy || !benchmarkJson.trim()} style={{ marginTop: 10 }}>
        {benchmarkBusy ? "Scoring..." : "Score benchmark transaction"}
      </button>
      {benchmarkError && <div className="notice" style={{ marginTop: 12 }}>{benchmarkError}</div>}
      {benchmarkResult && <div className="card" style={{ marginTop: 16, padding: 16 }}>
        <div className="eyebrow">MODEL PREDICTION</div>
        <div className="metric-value">{(benchmarkResult.fraud_probability * 100).toFixed(2)}%</div>
        <p>Prediction: <strong>{benchmarkResult.prediction}</strong></p>
        <p style={{ color: "var(--muted)", fontSize: 12 }}>Threshold: {(benchmarkResult.threshold * 100).toFixed(0)}% · Model: {benchmarkResult.model_version}</p>
        <p style={{ color: "var(--muted)", fontSize: 12 }}>{benchmarkResult.warning}</p>
      </div>}
    </section>

    <section className="card" style={{ marginBottom: 20, padding: 20 }}>
      <div className="section-head">
        <h3>Kafka Streaming Monitor</h3>
        <span><i className="dot" style={{ display: "inline-block", marginRight: 7, background: streamMetrics ? "var(--green)" : "var(--red)" }} />AUTO-REFRESH · 3 SEC</span>
      </div>
      {streamMetrics ? <>
        <section className="grid">
          <Metric icon={<Activity size={16} />} title="Stream processed" value={streamMetrics.total_processed.toLocaleString("en-IN")} foot="Unique scored events in MongoDB" />
          <Metric icon={<AlertTriangle size={16} />} title="Fraud review" value={streamMetrics.fraud_review.toLocaleString("en-IN")} foot="Events above model threshold" color="var(--red)" />
          <Metric icon={<BadgeCheck size={16} />} title="Legitimate" value={streamMetrics.legitimate.toLocaleString("en-IN")} foot="Events below model threshold" color="var(--green)" />
          <Metric icon={<Shield size={16} />} title="Review rate" value={`${(streamMetrics.fraud_review_rate * 100).toFixed(2)}%`} foot="Share of streamed events flagged" color="var(--yellow)" />
        </section>
        <p style={{ color: "var(--muted)", fontSize: 12, margin: "12px 0 0" }}>{streamMetrics.source_note}</p>
        <div className="table-wrap" style={{ marginTop: 14 }}>
          <table><thead><tr><th>Event ID</th><th>Processed at</th><th>Fraud probability</th><th>Decision</th><th>Actual class</th></tr></thead>
            <tbody>{streamEvents.map(event => <tr key={event.event_id}>
              <td className="mono">{event.event_id.length > 20 ? `${event.event_id.slice(0, 20)}…` : event.event_id}</td>
              <td className="mono">{event.processed_at ? new Date(event.processed_at).toLocaleTimeString() : "—"}</td>
              <td className="score" style={{ color: event.prediction === "fraud_review" ? "var(--red)" : "var(--green)" }}>{(event.fraud_probability * 100).toFixed(2)}%</td>
              <td><span className={`risk ${event.prediction === "fraud_review" ? "high" : "low"}`}>{event.prediction}</span></td>
              <td>{event.actual_class === 1 ? "Fraud" : event.actual_class === 0 ? "Legitimate" : "Unknown"}</td>
            </tr>)}</tbody>
          </table>
          {streamEvents.length === 0 && <div className="empty">No stream events yet. Start the Kafka producer and consumer.</div>}
        </div>
      </> : <p style={{ color: "var(--muted)" }}>{streamError || "Loading Kafka stream metrics…"}</p>}
      {streamError && streamMetrics && <div className="notice" style={{ marginTop: 12 }}>{streamError}</div>}
      <button className="btn" onClick={refreshStream} style={{ marginTop: 12 }}><RefreshCw size={13} style={{ verticalAlign: "middle", marginRight: 7 }} />Refresh stream</button>
    </section>

    <section className="grid">
      <Metric icon={<Activity size={16} />} title="Transactions observed" value={metrics.total_transactions.toLocaleString("en-IN")} foot="Records currently available" />
      <Metric icon={<Shield size={16} />} title="High-risk transactions" value={metrics.high_risk.toLocaleString("en-IN")} foot="Require priority review" color="var(--red)" />
      <Metric icon={<AlertTriangle size={16} />} title="Medium-risk transactions" value={metrics.medium_risk.toLocaleString("en-IN")} foot="Require additional checks" color="var(--yellow)" />
      <Metric icon={<BadgeCheck size={16} />} title="Confirmed fraud labels" value={metrics.confirmed_fraud.toLocaleString("en-IN")} foot="Analyst feedback recorded" color="var(--green)" />
    </section>

    <section className="split">
      <div className="card"><div className="section-head"><h3>Risk activity timeline</h3><span>RECENT RECORDS</span></div><div className="legend"><span><i style={{ background: COLORS[0] }} />Low risk</span><span><i style={{ background: COLORS[1] }} />Medium</span><span><i style={{ background: COLORS[2] }} />High</span></div><div className="chart"><ResponsiveContainer width="100%" height="100%"><AreaChart data={trend}><defs><linearGradient id="highFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#ff637d" stopOpacity={.28} /><stop offset="100%" stopColor="#ff637d" stopOpacity={0} /></linearGradient></defs><CartesianGrid stroke="#253145" strokeDasharray="3 5" vertical={false} /><XAxis dataKey="time" tick={{ fill: "#8190a9", fontSize: 10 }} axisLine={false} tickLine={false} /><YAxis allowDecimals={false} tick={{ fill: "#8190a9", fontSize: 10 }} axisLine={false} tickLine={false} /><Tooltip contentStyle={{ background: "#101622", border: "1px solid #253145", borderRadius: 9, fontSize: 12 }} /><Area type="monotone" dataKey="low" stackId="1" stroke="#64e6a6" fill="#64e6a6" fillOpacity={.1} /><Area type="monotone" dataKey="medium" stackId="1" stroke="#ffc766" fill="#ffc766" fillOpacity={.12} /><Area type="monotone" dataKey="high" stackId="1" stroke="#ff637d" fill="url(#highFill)" /></AreaChart></ResponsiveContainer></div></div>
      <div className="card"><div className="section-head"><h3>Risk distribution</h3><span>MODEL OUTPUT</span></div><div style={{ height: 205, position: "relative" }}><ResponsiveContainer width="100%" height="100%"><PieChart><Pie data={pie} dataKey="value" nameKey="name" innerRadius={58} outerRadius={82} paddingAngle={4} stroke="none">{pie.map((p, i) => <Cell key={p.name} fill={COLORS[i]} />)}</Pie><Tooltip contentStyle={{ background: "#101622", border: "1px solid #253145", borderRadius: 9, fontSize: 12 }} /></PieChart></ResponsiveContainer><div style={{ position: "absolute", inset: 0, display: "grid", placeContent: "center", textAlign: "center", pointerEvents: "none" }}><strong style={{ fontSize: 27 }}>{metrics.total_transactions}</strong><span style={{ fontSize: 10, color: "var(--muted)" }}>TOTAL SCORED</span></div></div><div className="legend" style={{ justifyContent: "center" }}>{pie.map((p, i) => <span key={p.name}><i style={{ background: COLORS[i] }} />{p.name} {p.value}</span>)}</div></div>
    </section>

    <section className="card table-card">
      <div className="table-head"><div><div className="eyebrow">INVESTIGATION QUEUE</div><h3 style={{ margin: "7px 0 0", fontSize: 16 }}>Recent transactions <span style={{ color: "var(--muted)", fontSize: 12, fontWeight: 500 }}>({filtered.length})</span></h3></div><div className="filters"><input aria-label="Search transactions" placeholder="Search merchant, ID..." value={search} onChange={e => setSearch(e.target.value)} /><select aria-label="Filter risk" value={risk} onChange={e => setRisk(e.target.value)}><option value="all">All risk levels</option><option value="high">High risk</option><option value="medium">Medium risk</option><option value="low">Low risk</option></select></div></div>
      <div className="table-wrap"><table><thead><tr><th>Transaction</th><th>Time</th><th>Amount</th><th>Channel</th><th>Risk score</th><th>Risk level</th><th>Status</th><th>Review</th></tr></thead><tbody>
        {filtered.map(tx => <tr key={tx.transaction_id}><td className="mono">{tx.transaction_id.slice(0, 8).toUpperCase()}</td><td className="mono">{time(tx.created_at)}</td><td style={{ fontWeight: 800 }}>{money(tx.amount)}</td><td>{tx.channel.toUpperCase()}</td><td className="score" style={{ color: tx.risk_level === "high" ? "var(--red)" : tx.risk_level === "medium" ? "var(--yellow)" : "var(--green)" }}>{(tx.fraud_probability * 100).toFixed(1)}%</td><td><span className={`risk ${tx.risk_level}`}>{tx.risk_level}</span></td><td>{tx.status}</td><td><button className="smallbtn" onClick={() => setSelected(tx)}>Investigate ↗</button></td></tr>)}
      </tbody></table>{filtered.length === 0 && <div className="empty">{online ? "No matching transactions yet. Generate a transaction to get started." : "Connect the backend to load transaction data."}</div>}</div>
    </section>
    <footer className="footer"><span>SENTINELAI · MODEL {metrics.model_version.toUpperCase()} · EDUCATIONAL DEMO</span><span>Risk score is a model estimate, not proof of fraud.</span></footer>

    {selected && <div className="modalback" onClick={() => setSelected(null)}><aside className="drawer" onClick={e => e.stopPropagation()}><div className="drawer-head"><div><div className="eyebrow">CASE REVIEW</div><h2>Transaction details</h2></div><button className="btn" aria-label="Close" onClick={() => setSelected(null)}><X size={16} /></button></div><div className="card" style={{ marginBottom: 14 }}><div style={{ color: "var(--muted)", fontSize: 11 }}>TRANSACTION ID</div><div className="mono" style={{ margin: "7px 0 14px", overflowWrap: "anywhere" }}>{selected.transaction_id}</div><div className="metric-value" style={{ margin: "4px 0" }}>{money(selected.amount)}</div><span className={`risk ${selected.risk_level}`}>{selected.risk_level} risk</span><span style={{ marginLeft: 10, color: "var(--muted)", fontSize: 12 }}>{(selected.fraud_probability * 100).toFixed(1)}% model score</span></div><div className="detailgrid">{[["Merchant category", selected.merchant_category], ["Channel", selected.channel], ["Country", selected.country], ["Account age", `${selected.account_age_days} days`], ["Transactions/hour", String(selected.transactions_last_hour)], ["Distance", `${selected.distance_from_home_km} km`], ["New device", selected.device_new ? "Yes" : "No"], ["Analyst label", selected.analyst_label]].map(([k, v]) => <div className="detail" key={k}><small>{k}</small><strong>{v}</strong></div>)}</div><h3 style={{ fontSize: 14, marginTop: 24 }}>Risk signals</h3><ul className="reasons">{selected.reasons.map(r => <li key={r}>{r}</li>)}</ul><h3 style={{ fontSize: 14, marginTop: 24 }}>Analyst decision</h3><p style={{ fontSize: 12, color: "var(--muted)" }}>Use this demo action to record review feedback. In production, decisions require authenticated, audited workflows.</p><div className="label-actions"><button className="btn" onClick={() => label(selected, "confirmed_fraud")}>Confirm fraud</button><button className="btn primary" onClick={() => label(selected, "legitimate")}>Mark legitimate</button><button className="btn" onClick={() => label(selected, "unknown")}>Reset label</button></div></aside></div>}
  </main>;
}

function Metric({ icon, title, value, foot, color }: { icon: ReactNode; title: string; value: string; foot: string; color?: string }) {
  return <div className="card"><div className="metric-head"><span>{title}</span><span className="metric-icon" style={{ color: color || "var(--cyan)" }}>{icon}</span></div><div className="metric-value">{value}</div><div className="metric-foot">{foot}</div></div>;
}
