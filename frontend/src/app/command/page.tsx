"use client";

import { useState, useEffect } from 'react';
import dynamic from 'next/dynamic';
import Link from 'next/link';
import { ArrowLeft, CheckCircle2, XCircle, ShieldAlert, Navigation, Megaphone } from 'lucide-react';

const CommandMap = dynamic(() => import('./CommandMap'), { ssr: false });

export default function CommandPage() {
  const [role, setRole] = useState("Officer");
  const [state, setState] = useState<any>(null);
  const [health, setHealth] = useState<any>(null);
  const [expandedRationale, setExpandedRationale] = useState<number | null>(null);

  // Broadcast composer state
  const [targetWard, setTargetWard] = useState("");
  const [template, setTemplate] = useState("EVAC");

  const loadState = async () => {
    const res = await fetch('http://localhost:8000/api/decision/state');
    const data = await res.json();
    setState(data);
  };

  const loadHealth = async () => {
    const res = await fetch('http://localhost:8000/api/decision/health');
    const data = await res.json();
    setHealth(data);
  };

  useEffect(() => {
    loadState();
    loadHealth();

    const es = new EventSource('http://localhost:8000/api/reports/ward_state_stream');
    es.onmessage = () => {
      loadState();
    };
    return () => es.close();
  }, []);

  const handleAction = async (allocation: any, action: string) => {
    if (role !== "Officer") return alert("Viewer mode cannot execute actions.");
    
    await fetch('http://localhost:8000/api/decision/action', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        ward_id: allocation.ward_id,
        action: action,
        resource_type: allocation.resource_type,
        qty: allocation.qty,
        db_resource_id: allocation.db_resource_id,
        rationale: allocation.rationale,
        user_role: role
      })
    });
    loadState();
  };

  const handleBroadcast = async () => {
    if (role !== "Officer") return alert("Viewer mode cannot execute actions.");
    if (!targetWard) return alert("Select a ward");
    
    await fetch('http://localhost:8000/api/decision/broadcast', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        ward_id: targetWard,
        template_id: template,
        slots: {
          ward: targetWard,
          shelter: "Nearest Relief Camp",
          severity: "High",
          hazard: "Cyclone",
          time: "14:00"
        }
      })
    });
    alert("Broadcast dispatched successfully and logged in ledger.");
  };

  if (!state) return <div className="p-8 text-white">Loading Command Matrix...</div>;

  return (
    <div className="min-h-screen flex flex-col bg-slate-950 text-slate-300">
      {/* Header & Health Strip */}
      <header className="border-b border-slate-800 bg-slate-900/50 p-4 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link href="/" className="text-blue-400 hover:text-blue-300">
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <ShieldAlert className="w-5 h-5 text-red-500" />
            SkySafe Command Center
          </h1>
        </div>
        
        <div className="flex items-center gap-6 text-sm">
          {health && (
            <>
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
                SACHET: {health.sachet_status} (TTR: {health.time_to_ready_p50_ms}ms)
              </div>
              <div className="flex items-center gap-2 border-l border-slate-700 pl-4">
                IMD Model: {health.imd_model_sync}
              </div>
            </>
          )}
          <select 
            value={role} 
            onChange={(e) => setRole(e.target.value)}
            className="bg-slate-800 border border-slate-700 rounded px-2 py-1 text-white text-xs"
          >
            <option value="Officer">Officer (R/W)</option>
            <option value="Viewer">Viewer (R)</option>
          </select>
        </div>
      </header>

      <div className="flex-1 flex overflow-hidden">
        {/* Left Column: Map */}
        <div className="flex-1 border-r border-slate-800 relative">
          <CommandMap wards={state.wards} shelters={state.shelters} depots={state.depots} />
        </div>

        {/* Right Column: Actions & Broadcast */}
        <div className="w-96 flex flex-col bg-slate-900/80 overflow-y-auto">
          <div className="p-4 border-b border-slate-800">
            <h2 className="text-lg font-bold text-white mb-3">Resource Optimizer</h2>
            <div className="space-y-4">
              {state.allocations.length === 0 ? (
                <p className="text-sm text-emerald-400">All high-risk wards are currently resourced.</p>
              ) : (
                state.allocations.map((alloc: any, idx: number) => (
                  <div key={idx} className="bg-slate-800 rounded-lg p-3 border border-slate-700">
                    <p className="text-sm font-semibold text-white mb-2">
                      {idx + 1}. Send {alloc.qty} {alloc.resource_type} from {alloc.depot_name} to {alloc.ward_name}
                    </p>
                    <p className="text-xs text-slate-400 mb-3 flex items-center gap-1">
                      <Navigation className="w-3 h-3" /> ETA: {alloc.eta_min} min
                    </p>
                    
                    {role === "Officer" && (
                      <div className="flex gap-2 mb-3">
                        <button onClick={() => handleAction(alloc, "Dispatch")} className="flex-1 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold py-1.5 rounded flex items-center justify-center gap-1">
                          <CheckCircle2 className="w-3 h-3" /> Dispatch
                        </button>
                        <button onClick={() => handleAction(alloc, "Dismiss")} className="flex-1 bg-slate-700 hover:bg-slate-600 text-white text-xs font-bold py-1.5 rounded flex items-center justify-center gap-1">
                          <XCircle className="w-3 h-3" /> Dismiss
                        </button>
                      </div>
                    )}

                    <div className="text-xs">
                      <button 
                        onClick={() => setExpandedRationale(expandedRationale === idx ? null : idx)}
                        className="text-blue-400 hover:underline font-medium mb-1"
                      >
                        {expandedRationale === idx ? "Hide Ledger" : "View 'Why' Ledger"}
                      </button>
                      {expandedRationale === idx && (
                        <div className="mt-2 space-y-1 bg-slate-950 p-2 rounded border border-slate-800">
                          {alloc.ledger.map((f: any, fIdx: number) => (
                            <div key={fIdx} className="flex justify-between items-start gap-2">
                              <div>
                                <span className="font-semibold text-slate-300">{f.factor}:</span> {f.value}
                                <div className="text-[10px] text-slate-500 font-mono mt-0.5">SRC: {f.source}</div>
                              </div>
                              <span className="text-emerald-400 font-mono">+{f.score.toFixed(1)}</span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          <div className="p-4">
            <h2 className="text-lg font-bold text-white mb-3">Validated Broadcast</h2>
            <div className="bg-slate-800 p-3 rounded-lg border border-slate-700">
              <label className="block text-xs font-semibold text-slate-400 mb-1">Target Area</label>
              <select 
                value={targetWard} 
                onChange={(e) => setTargetWard(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 rounded p-1.5 text-sm text-white mb-3"
              >
                <option value="">-- Select Ward --</option>
                {state.wards.map((w: any) => (
                  <option key={w.ward_id} value={w.ward_id}>{w.name}</option>
                ))}
              </select>

              <label className="block text-xs font-semibold text-slate-400 mb-1">Official Template</label>
              <select 
                value={template} 
                onChange={(e) => setTemplate(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 rounded p-1.5 text-sm text-white mb-3"
              >
                <option value="EVAC">Urgent Evacuation</option>
                <option value="WARN">Incoming Hazard Warning</option>
              </select>

              <div className="bg-slate-950 p-2 rounded text-sm font-mono text-amber-400 mb-3 border border-amber-900/50">
                {template === "EVAC" && `URGENT: Evacuate [${targetWard || 'ward'}] to [Nearest Relief Camp]. Danger level [High].`}
                {template === "WARN" && `WARNING: [Cyclone] incoming at [14:00]. Stay indoors.`}
              </div>

              {role === "Officer" && (
                <button 
                  onClick={handleBroadcast}
                  className="w-full bg-blue-600 hover:bg-blue-500 text-white font-bold text-sm py-2 rounded flex items-center justify-center gap-2"
                >
                  <Megaphone className="w-4 h-4" /> Issue Broadcast
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
