"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { ArrowLeft, RefreshCw } from "lucide-react";
import { getApiUrl } from "@/lib/api";

function MetricCard({ title, value, sub }: { title: string; value: any; sub?: string }) {
  return (
    <div className="bg-slate-900 rounded-xl p-4 border border-slate-800">
      <p className="text-xs text-slate-400 uppercase tracking-wider mb-1">{title}</p>
      <p className="text-2xl font-black text-white">{value ?? "N/A"}</p>
      {sub && <p className="text-xs text-slate-500 mt-1 font-mono">{sub}</p>}
    </div>
  );
}

export default function MetricsPage() {
  const [data, setData] = useState<any>(null);
  const [lastRefresh, setLastRefresh] = useState<string>("");

  const fetchMetrics = async () => {
    try {
      const res = await fetch(getApiUrl("/api/eval/metrics"));
      const json = await res.json();
      setData(json);
      setLastRefresh(new Date().toLocaleTimeString());
    } catch {}
  };

  useEffect(() => {
    fetchMetrics();
    const id = setInterval(fetchMetrics, 5000);
    return () => clearInterval(id);
  }, []);

  if (!data) return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center text-slate-400">
      Loading metrics…
    </div>
  );

  const ac = data.alert_counts ?? {};
  const il = data.ingest_latency ?? {};
  const lp = data.llm_path_breakdown ?? {};
  const bl = data.broadcast_latency ?? {};
  const lc = data.language_coverage ?? {};
  const rc = data.report_confirmation_latency ?? {};

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-6">
      <div className="max-w-6xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <Link href="/lab" className="p-2 rounded-lg hover:bg-slate-800 text-slate-400">
              <ArrowLeft className="w-5 h-5" />
            </Link>
            <h1 className="text-2xl font-black text-white">📊 Live Metrics</h1>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-xs text-slate-500">Last refresh: {lastRefresh}</span>
            {data.source_outage_active && (
              <span className="px-2 py-1 rounded bg-red-900/50 text-red-300 text-xs font-bold">⚠️ SOURCE OUTAGE ACTIVE</span>
            )}
            <button onClick={fetchMetrics} className="p-2 rounded-lg hover:bg-slate-800 text-slate-400">
              <RefreshCw className="w-4 h-4" />
            </button>
          </div>
        </div>

        <p className="text-xs text-slate-500 mb-6 font-mono">
          All values derived from live database queries. No hardcoded numbers. Generated: {data.generated_at}
        </p>

        <h2 className="text-sm font-bold text-slate-300 uppercase mb-3">Alert Pipeline</h2>
        <div className="grid grid-cols-4 gap-4 mb-6">
          <MetricCard title="Total Alerts" value={ac.total} sub={ac.source} />
          <MetricCard title="Active Alerts" value={ac.active} sub="alerts.is_expired = false" />
          <MetricCard title="Simulated/Drill" value={ac.simulated} sub="alerts.is_simulation = true" />
          <MetricCard title="Expired" value={ac.expired} sub="alerts.is_expired = true" />
        </div>

        <h2 className="text-sm font-bold text-slate-300 uppercase mb-3">Feed Ingest Latency</h2>
        <div className="grid grid-cols-2 gap-4 mb-6">
          <MetricCard title="p50 Ingest Lag" value={il.p50_seconds != null ? `${il.p50_seconds}s` : "N/A"} sub={il.source} />
          <MetricCard title="p95 Ingest Lag" value={il.p95_seconds != null ? `${il.p95_seconds}s` : "N/A"} sub={il.source} />
        </div>

        <h2 className="text-sm font-bold text-slate-300 uppercase mb-3">LLM Pipeline</h2>
        <div className="grid grid-cols-2 gap-4 mb-6">
          <div className="bg-slate-900 rounded-xl p-4 border border-slate-800">
            <p className="text-xs text-slate-400 uppercase tracking-wider mb-3">Path Breakdown</p>
            {lp.total_events === 0 ? (
              <p className="text-slate-500 text-sm">No events yet. Trigger a broadcast to populate.</p>
            ) : (
              <div className="space-y-2">
                {Object.entries(lp.breakdown ?? {}).map(([path, cnt]) => (
                  <div key={path} className="flex items-center justify-between">
                    <span className="text-sm font-mono text-slate-300">{path}</span>
                    <span className="font-bold text-white">{String(cnt)}</span>
                  </div>
                ))}
                <p className="text-xs text-slate-500 pt-2 font-mono">{lp.source}</p>
              </div>
            )}
          </div>
          <div className="grid grid-rows-2 gap-4">
            <MetricCard title="p50 Delivery Latency" value={bl.p50_ms != null ? `${bl.p50_ms}ms` : "N/A"} sub={bl.source} />
            <MetricCard title="p95 Delivery Latency" value={bl.p95_ms != null ? `${bl.p95_ms}ms` : "N/A"} sub={bl.source} />
          </div>
        </div>

        <h2 className="text-sm font-bold text-slate-300 uppercase mb-3">Coverage & Reports</h2>
        <div className="grid grid-cols-3 gap-4 mb-6">
          <MetricCard title="Language Coverage" value={lc.count} sub={lc.languages?.join(", ") || "No data"} />
          <MetricCard title="Avg Report→Confirm" value={rc.avg_seconds != null ? `${rc.avg_seconds}s` : "N/A"} sub={rc.source} />
          <MetricCard title="Confirmed Wards" value={rc.count} sub="ward_states.state = Confirmed" />
        </div>
      </div>
    </div>
  );
}
