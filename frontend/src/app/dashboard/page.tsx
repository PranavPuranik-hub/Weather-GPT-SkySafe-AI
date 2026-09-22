"use client";

import Link from 'next/link';
import { ArrowLeft, Activity, Users, Truck, AlertTriangle } from 'lucide-react';
import { useEffect, useState } from 'react';

export default function DashboardPage() {
  const [wardState, setWardState] = useState("Predicted");

  useEffect(() => {
    const eventSource = new EventSource('http://localhost:8000/api/reports/ward_state_stream');

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.ward_id === "Ward 7") {
          setWardState(data.state);
        }
      } catch (e) {
        console.error("SSE parse error", e);
      }
    };

    return () => {
      eventSource.close();
    };
  }, []);

  return (
    <div className="space-y-6 py-4">
      <div className="flex items-center justify-between">
        <Link 
          href="/" 
          className="inline-flex items-center gap-1.5 text-sm font-semibold text-blue-400 hover:text-blue-300"
        >
          <ArrowLeft className="w-4 h-4" /> Back to Home
        </Link>
        <span className="text-xs px-2.5 py-1 rounded-full bg-amber-950 text-amber-300 border border-amber-800 font-medium">
          Official Decision Matrix
        </span>
      </div>

      <header className="space-y-1">
        <h1 className="text-2xl sm:text-3xl font-bold text-white">Disaster Command Dashboard</h1>
        <p className="text-slate-400 text-sm">Real-time action intelligence & resource optimization matrix.</p>
      </header>

      {/* Overview Stat Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="bg-slate-800/80 border border-slate-700 p-4 rounded-xl space-y-1">
          <div className="flex items-center text-amber-400 gap-1.5 text-xs font-semibold">
            <AlertTriangle className="w-4 h-4" /> Active Alerts
          </div>
          <p className="text-2xl font-bold text-white">3</p>
        </div>
        <div className="bg-slate-800/80 border border-slate-700 p-4 rounded-xl space-y-1">
          <div className="flex items-center text-blue-400 gap-1.5 text-xs font-semibold">
            <Users className="w-4 h-4" /> At-Risk Pop.
          </div>
          <p className="text-2xl font-bold text-white">45,000</p>
        </div>
        <div className="bg-slate-800/80 border border-slate-700 p-4 rounded-xl space-y-1">
          <div className="flex items-center text-emerald-400 gap-1.5 text-xs font-semibold">
            <Truck className="w-4 h-4" /> Relief Units
          </div>
          <p className="text-2xl font-bold text-white">12 Teams</p>
        </div>
        <div className="bg-slate-800/80 border border-slate-700 p-4 rounded-xl space-y-1">
          <div className="flex items-center text-purple-400 gap-1.5 text-xs font-semibold">
            <Activity className="w-4 h-4" /> System Health
          </div>
          <p className="text-2xl font-bold text-emerald-400">100%</p>
        </div>
      </div>

      {/* Ward Status Monitor */}
      <div className="bg-slate-800/50 border border-slate-700 rounded-2xl p-5 space-y-3 shadow-xl">
        <h2 className="text-lg font-bold text-white">Live Ward Status (Zero-Trust Cluster)</h2>
        <div className="flex items-center gap-4">
          <div className="bg-slate-900 border border-slate-700 rounded-lg p-4 flex-1">
            <h3 className="text-sm font-semibold text-slate-300">Ward 7</h3>
            <p className="text-xs text-slate-500">Incoming Citizen Reports</p>
          </div>
          <div className="text-white font-bold text-xl">
             -&gt; 
          </div>
          <div className={`border rounded-lg p-4 flex-1 text-center font-bold transition-colors duration-500 ${wardState === 'Confirmed' ? 'bg-red-900/50 border-red-500 text-red-400' : wardState === 'Reported' ? 'bg-amber-900/50 border-amber-500 text-amber-400' : 'bg-slate-800 border-slate-600 text-slate-300'}`}>
            {wardState.toUpperCase()}
          </div>
        </div>
        <div className="flex items-center justify-between mt-2">
          <p className="text-xs text-slate-400">Status auto-elevates when 3+ independent citizens report from the same area.</p>
          <button 
            onClick={() => {
              setWardState("Predicted");
              fetch('http://localhost:8000/api/reports/simulate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ ward_id: "Ward 7", count: 5, text: "Water entered my home" })
              });
            }}
            className="text-xs font-bold bg-blue-600 hover:bg-blue-500 text-white py-1.5 px-3 rounded-lg shadow-sm transition-colors"
          >
            Trigger Simulation
          </button>
        </div>
      </div>

      {/* Priority Action Table */}
      <div className="bg-slate-800/50 border border-slate-700 rounded-2xl p-5 space-y-3 shadow-xl">
        <h2 className="text-lg font-bold text-white">Prioritized District Action Allocation</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-slate-300">
            <thead className="text-xs uppercase bg-slate-900/80 text-slate-400 border-b border-slate-700">
              <tr>
                <th className="px-4 py-3">District</th>
                <th className="px-4 py-3">Severity</th>
                <th className="px-4 py-3">Recommended Action</th>
                <th className="px-4 py-3">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800">
              <tr>
                <td className="px-4 py-3 font-bold text-white">Cuttack</td>
                <td className="px-4 py-3 text-red-400 font-semibold">RED WARNING</td>
                <td className="px-4 py-3">Deploy 4 NDRF Teams to Mahanadi Basin</td>
                <td className="px-4 py-3 text-emerald-400 font-medium">DISPATCHED</td>
              </tr>
              <tr>
                <td className="px-4 py-3 font-bold text-white">Puri</td>
                <td className="px-4 py-3 text-amber-400 font-semibold">ORANGE ALERT</td>
                <td className="px-4 py-3">Issue Coastal Evacuation Voice Broadcast</td>
                <td className="px-4 py-3 text-amber-400 font-medium">PENDING</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
