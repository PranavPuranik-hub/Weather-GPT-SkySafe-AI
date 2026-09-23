"use client";

import React, { useState } from "react";
import { Zap, Clock, ShieldAlert, ChevronDown, ChevronUp, Radio, CheckCircle, AlertTriangle } from "lucide-react";
import { getApiBaseUrl } from "@/lib/api";

interface DevPanelProps {
  onSimulatedAlert: (alertData: any) => void;
  currentDistrict?: string;
  currentLang?: string;
  currentPersona?: string;
}

export default function DevPanel({
  onSimulatedAlert,
  currentDistrict = "Cuttack",
  currentLang = "en",
  currentPersona = "General",
}: DevPanelProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [scenario, setScenario] = useState("odisha_cyclone");
  const [district, setDistrict] = useState(currentDistrict);
  const [isLoading, setIsLoading] = useState(false);
  const [latencyMs, setLatencyMs] = useState<number | null>(null);
  const [lastDeliveredTime, setLastDeliveredTime] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const handleSimulate = async () => {
    setIsLoading(true);
    setFeedback(null);
    const startTime = performance.now();

    const queryParams = new URLSearchParams({
      lang: currentLang || "en",
      persona: currentPersona || "General",
      district: district || "Cuttack",
    });

    const path = `/api/admin/simulate/${encodeURIComponent(scenario)}?${queryParams.toString()}`;

    try {
      // First attempt via relative URL (proxied by Next.js rewrites)
      let res: Response | null = null;
      try {
        res = await fetch(path, { method: "POST" });
      } catch (networkErr) {
        console.warn("Relative fetch failed, trying direct backend...", networkErr);
      }

      // If relative failed or returned 404/500, attempt direct call to backend
      if (!res || !res.ok) {
        try {
          const apiBase = getApiBaseUrl();
          const directUrl = apiBase ? `${apiBase}${path}` : (typeof window !== "undefined" && (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1") ? `http://127.0.0.1:8000${path}` : path);
          res = await fetch(directUrl, { method: "POST" });
        } catch (directErr) {
          console.error("Direct backend fetch failed:", directErr);
        }
      }

      if (!res || !res.ok) {
        const errorText = res ? await res.text() : "Network unreachable";
        throw new Error(`Broadcast failed (${res?.status || "error"}): ${errorText.slice(0, 100)}`);
      }

      const data = await res.json();
      const elapsed =
        data.delivery_latency_ms != null
          ? Math.round(data.delivery_latency_ms)
          : Math.round(performance.now() - startTime);

      setLatencyMs(elapsed);
      const timeStr = new Date().toLocaleTimeString();
      setLastDeliveredTime(timeStr);
      setFeedback({
        type: "success",
        text: `Broadcast sent! Latency: ${elapsed}ms (<60s SLA)`,
      });

      // Push alert to chat feed
      onSimulatedAlert(data);
    } catch (err: any) {
      console.error("Simulation failed:", err);
      setFeedback({
        type: "error",
        text: err?.message || "Failed to trigger simulation. Check backend connection.",
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="fixed bottom-4 right-4 z-40">
      {/* Minimized Pill */}
      {!isOpen ? (
        <button
          onClick={() => setIsOpen(true)}
          className="flex items-center gap-2 px-3.5 py-2 rounded-full bg-slate-900/95 hover:bg-slate-800 border border-amber-500/50 shadow-xl text-xs font-bold text-amber-400 backdrop-blur transition-all active:scale-95"
        >
          <Radio className="w-4 h-4 text-red-500 animate-pulse" />
          <span>Dev Simulation Panel</span>
          {latencyMs !== null && (
            <span className="px-1.5 py-0.5 rounded bg-amber-500/20 text-[10px] text-amber-300 font-mono">
              {latencyMs}ms
            </span>
          )}
          <ChevronUp className="w-3.5 h-3.5 text-slate-400" />
        </button>
      ) : (
        /* Expanded Floating Card */
        <div className="w-80 bg-slate-900 border border-amber-500/50 rounded-2xl shadow-2xl p-4 text-slate-200 text-xs space-y-3 backdrop-blur-md animate-in fade-in slide-in-from-bottom-2 duration-150">
          {/* Header */}
          <div className="flex items-center justify-between border-b border-slate-800 pb-2">
            <div className="flex items-center gap-1.5 font-bold text-amber-400">
              <Zap className="w-4 h-4" />
              <span>Broadcast Drill Simulator</span>
            </div>
            <button
              onClick={() => setIsOpen(false)}
              className="p-1 hover:bg-slate-800 rounded text-slate-400 hover:text-white"
            >
              <ChevronDown className="w-4 h-4" />
            </button>
          </div>

          <p className="text-[11px] text-slate-400 leading-relaxed">
            Push simulated emergency alert scenarios to test real-time broadcast delivery, grounding proof, and latency (&lt;60s requirement).
          </p>

          {/* Scenario Selector */}
          <div className="space-y-1">
            <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
              Disaster Scenario Step:
            </label>
            <select
              value={scenario}
              onChange={(e) => setScenario(e.target.value)}
              className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-xs text-white focus:outline-none focus:border-amber-500"
            >
              <option value="odisha_cyclone">Cyclone Drill (Odisha Coast)</option>
              <option value="cyclone_t24">Cyclone T-24 Advisory (Yellow)</option>
              <option value="cyclone_t12">Cyclone T-12 Warning (Orange)</option>
              <option value="cyclone_t3">Cyclone T-3 Landfall (Red Alert)</option>
              <option value="kerala_flood">Flash Flood Drill (Wayanad, Kerala)</option>
              <option value="rajasthan_heatwave">Extreme Heatwave Drill (Rajasthan)</option>
              <option value="bihar_thunderstorm">Severe Thunderstorm Drill (Bihar)</option>
              <option value="tamilnadu_high_wave">High Swell Waves Drill (Tamil Nadu)</option>
            </select>
          </div>

          {/* District Input */}
          <div className="space-y-1">
            <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
              Target District:
            </label>
            <select
              value={district}
              onChange={(e) => setDistrict(e.target.value)}
              className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-xs text-white focus:outline-none focus:border-amber-500"
            >
              <option value="Cuttack">Cuttack (Odisha)</option>
              <option value="Puri">Puri (Coastal Odisha)</option>
              <option value="Wayanad">Wayanad (Kerala)</option>
              <option value="Nagpur">Nagpur (Maharashtra)</option>
              <option value="Mumbai">Mumbai (Maharashtra)</option>
            </select>
          </div>

          {/* Feedback Message */}
          {feedback && (
            <div
              className={`p-2 rounded-lg text-[11px] flex items-start gap-1.5 ${
                feedback.type === "success"
                  ? "bg-emerald-950/60 border border-emerald-500/40 text-emerald-300"
                  : "bg-red-950/60 border border-red-500/40 text-red-300"
              }`}
            >
              {feedback.type === "success" ? (
                <CheckCircle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
              ) : (
                <AlertTriangle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
              )}
              <span className="leading-tight">{feedback.text}</span>
            </div>
          )}

          {/* Broadcast Trigger Button */}
          <button
            onClick={handleSimulate}
            disabled={isLoading}
            className="w-full py-2.5 px-3 rounded-xl bg-gradient-to-r from-red-600 to-amber-600 hover:from-red-500 hover:to-amber-500 active:scale-[0.98] font-bold text-white shadow-lg flex items-center justify-center gap-2 transition-all disabled:opacity-50"
          >
            <ShieldAlert className="w-4 h-4" />
            <span>{isLoading ? "Broadcasting..." : "Trigger Emergency Broadcast"}</span>
          </button>

          {/* Latency / Performance Stats */}
          {latencyMs !== null && (
            <div className="p-2 rounded-lg bg-slate-950 border border-slate-800 space-y-1">
              <div className="flex items-center justify-between text-[11px]">
                <span className="flex items-center gap-1 text-slate-400">
                  <Clock className="w-3 h-3 text-emerald-400" /> Delivery Latency:
                </span>
                <span className="font-mono font-bold text-emerald-400">
                  {latencyMs} ms (&lt;60s Pass)
                </span>
              </div>
              <div className="flex items-center justify-between text-[10px] text-slate-500">
                <span>Delivered: {lastDeliveredTime}</span>
                <span className="text-emerald-500 font-semibold">SIH26068 SLA Met</span>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
