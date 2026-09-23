"use client";

import { useState, useEffect, useRef } from "react";
import Link from "next/link";
import {
  Play, Pause, SkipForward, AlertTriangle, Activity,
  Zap, WifiOff, FileText, ArrowLeft
} from "lucide-react";

const SCENARIOS = [
  "kerala_flood", "odisha_cyclone", "rajasthan_heatwave",
  "cyclone_t24", "cyclone_t12", "cyclone_t3", "flood", "heatwave"
];
const SPEEDS = [1, 10, 60];

export default function LabPage() {
  const [scenario, setScenario] = useState("odisha_cyclone");
  const [speed, setSpeed] = useState(1);
  const [clockState, setClockState] = useState<any>(null);
  const [tick, setTick] = useState(0);
  const [outageActive, setOutageActive] = useState(false);
  const [outageLoading, setOutageLoading] = useState(false);
  const [log, setLog] = useState<string[]>([]);
  const esRef = useRef<EventSource | null>(null);

  const addLog = (msg: string) => setLog(prev => [msg, ...prev].slice(0, 50));

  // Connect to clock SSE stream
  useEffect(() => {
    const es = new EventSource("http://localhost:8000/api/eval/clock/stream");
    esRef.current = es;
    es.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        if (data.tick) {
          setTick(data.tick);
          addLog(`⏱ Tick ${data.tick} — ${data.scenario} @ ${data.speed}x`);
        }
      } catch {}
    };
    return () => es.close();
  }, []);

  const fetchClockState = async () => {
    const res = await fetch("http://localhost:8000/api/eval/clock/state");
    setClockState(await res.json());
  };

  const clockAction = async (action: string, body?: any) => {
    await fetch(`http://localhost:8000/api/eval/clock/${action}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: body ? JSON.stringify(body) : undefined,
    });
    fetchClockState();
    addLog(`Clock: ${action}${body ? ` — ${JSON.stringify(body)}` : ""}`);
  };

  const toggleOutage = async () => {
    setOutageLoading(true);
    const res = await fetch("http://localhost:8000/api/eval/outage", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ enabled: !outageActive }),
    });
    const data = await res.json();
    setOutageActive(data.source_outage_active);
    addLog(`Source outage: ${data.source_outage_active ? "⚠️ ACTIVE" : "✓ Off"}`);
    setOutageLoading(false);
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-4">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <Link href="/" className="p-2 rounded-lg hover:bg-slate-800 text-slate-400">
              <ArrowLeft className="w-5 h-5" />
            </Link>
            <h1 className="text-2xl font-black text-white">🧪 SkySafe AI — Lab & Evaluation</h1>
          </div>
          <div className="flex gap-2">
            <Link href="/lab/metrics" className="px-3 py-1.5 rounded-lg bg-blue-600/20 hover:bg-blue-600/40 text-blue-300 text-sm font-semibold flex items-center gap-1">
              <Activity className="w-4 h-4" /> Live Metrics
            </Link>
            <Link href="/lab/breakit" className="px-3 py-1.5 rounded-lg bg-red-600/20 hover:bg-red-600/40 text-red-300 text-sm font-semibold flex items-center gap-1">
              <Zap className="w-4 h-4" /> Break-it Panel
            </Link>
            <a href="http://localhost:8000/api/eval/report" target="_blank" rel="noreferrer"
              className="px-3 py-1.5 rounded-lg bg-emerald-600/20 hover:bg-emerald-600/40 text-emerald-300 text-sm font-semibold flex items-center gap-1">
              <FileText className="w-4 h-4" /> Evidence Report
            </a>
          </div>
        </div>

        <div className="grid grid-cols-12 gap-4">
          {/* Control Panel */}
          <div className="col-span-3 space-y-4">
            <div className="bg-slate-900 rounded-xl p-4 border border-slate-800">
              <h2 className="text-sm font-bold text-slate-300 uppercase tracking-wider mb-3">Scenario Replay</h2>

              <label className="text-xs text-slate-400 block mb-1">Scenario</label>
              <select value={scenario} onChange={e => setScenario(e.target.value)}
                className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white mb-3 focus:outline-none focus:border-blue-500">
                {SCENARIOS.map(s => <option key={s} value={s}>{s}</option>)}
              </select>

              <label className="text-xs text-slate-400 block mb-1">Speed</label>
              <div className="flex gap-2 mb-4">
                {SPEEDS.map(s => (
                  <button key={s} onClick={() => setSpeed(s)}
                    className={`flex-1 py-1.5 rounded-lg text-xs font-bold border transition-all ${speed === s ? "bg-blue-600 border-blue-500 text-white" : "bg-slate-800 border-slate-700 text-slate-400"}`}>
                    {s}×
                  </button>
                ))}
              </div>

              <div className="flex gap-2">
                <button onClick={() => clockAction("start", { scenario, speed })}
                  className="flex-1 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-sm flex items-center justify-center gap-1">
                  <Play className="w-4 h-4" /> Play
                </button>
                <button onClick={() => clockAction("pause")}
                  className="px-3 py-2 rounded-lg bg-amber-600/30 hover:bg-amber-600/50 text-amber-300 border border-amber-700">
                  <Pause className="w-4 h-4" />
                </button>
                <button onClick={() => clockAction("step")}
                  className="px-3 py-2 rounded-lg bg-slate-700 hover:bg-slate-600 text-slate-300">
                  <SkipForward className="w-4 h-4" />
                </button>
              </div>

              {/* Tick indicator */}
              <div className="mt-3 flex items-center justify-between text-xs text-slate-500">
                <span>Current tick</span>
                <span className="font-mono text-blue-400 font-bold">{tick}</span>
              </div>
            </div>

            {/* Source Outage */}
            <div className="bg-slate-900 rounded-xl p-4 border border-slate-800">
              <h2 className="text-sm font-bold text-slate-300 uppercase tracking-wider mb-3">Source Outage Sim</h2>
              <button onClick={toggleOutage} disabled={outageLoading}
                className={`w-full py-2 rounded-lg font-bold text-sm flex items-center justify-center gap-2 border transition-all ${outageActive ? "bg-red-900/50 border-red-700 text-red-300" : "bg-slate-800 border-slate-700 text-slate-300 hover:bg-slate-700"}`}>
                <WifiOff className="w-4 h-4" />
                {outageActive ? "⚠️ OUTAGE ACTIVE — Click to restore" : "Simulate Live Feed Outage"}
              </button>
              <p className="text-xs text-slate-500 mt-2">
                When active, the live feed raises a simulated error. System falls back to cached DB/fixtures. Citizen chat remains graceful.
              </p>
            </div>

            {/* Event Log */}
            <div className="bg-slate-900 rounded-xl p-4 border border-slate-800">
              <h2 className="text-sm font-bold text-slate-300 uppercase tracking-wider mb-2">Event Log</h2>
              <div className="h-40 overflow-y-auto font-mono text-xs text-slate-400 space-y-1">
                {log.length === 0 && <p className="text-slate-600">No events yet…</p>}
                {log.map((l, i) => <div key={i} className="border-b border-slate-800/50 pb-0.5">{l}</div>)}
              </div>
            </div>
          </div>

          {/* Three live views */}
          <div className="col-span-9 grid grid-rows-1 gap-4">
            <div className="grid grid-cols-3 gap-4 h-[calc(100vh-160px)]">
              <div className="flex flex-col">
                <div className="text-xs font-bold text-slate-400 uppercase mb-2 flex items-center gap-1">
                  💬 Citizen Chat
                </div>
                <iframe src="/chat" className="flex-1 rounded-xl border border-slate-800 bg-slate-900" />
              </div>
              <div className="flex flex-col">
                <div className="text-xs font-bold text-slate-400 uppercase mb-2">
                  🗺️ Command Center
                </div>
                <iframe src="/command" className="flex-1 rounded-xl border border-slate-800 bg-slate-900" />
              </div>
              <div className="flex flex-col">
                <div className="text-xs font-bold text-slate-400 uppercase mb-2">
                  📱 SMS Simulator
                </div>
                <iframe src="/lab/sms" className="flex-1 rounded-xl border border-slate-800 bg-slate-900" />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
