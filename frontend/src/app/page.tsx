import Link from 'next/link';
import { Shield, LayoutDashboard, Volume2, Smartphone, MessageSquare } from 'lucide-react';

export default function Home() {
  return (
    <div className="flex flex-col gap-8 py-4">
      {/* Hero Section */}
      <div className="text-center space-y-3">
        <h1 className="text-3xl sm:text-4xl font-black text-white tracking-tight">
          Action Intelligence for Weather Disasters
        </h1>
        <p className="text-slate-300 text-base sm:text-lg max-w-xl mx-auto leading-relaxed">
          Turning official weather alerts (SACHET/IMD) into simple, life-saving, multilingual voice & SMS actions.
        </p>
      </div>

      {/* Main Portal Links - Three Primary Views */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 my-2">
        {/* WeatherGPT Chat Card */}
        <Link 
          href="/chat"
          className="group relative bg-gradient-to-b from-emerald-950/40 to-slate-900 hover:to-slate-850 border border-emerald-500/40 hover:border-emerald-400 rounded-2xl p-6 transition-all duration-200 shadow-xl flex flex-col justify-between"
        >
          <div className="space-y-3">
            <div className="w-12 h-12 rounded-xl bg-emerald-600/20 text-emerald-400 flex items-center justify-center font-bold border border-emerald-500/30">
              <MessageSquare className="w-6 h-6" />
            </div>
            <div className="flex items-center gap-2">
              <h2 className="text-xl font-bold text-white group-hover:text-emerald-400 transition-colors">
                WeatherGPT Chat
              </h2>
              <span className="px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 text-[10px] font-bold">
                SIH26068
              </span>
            </div>
            <p className="text-slate-300 text-xs leading-relaxed">
              Conversational AI with WhatsApp UI, voice-notes, claim-ledger proofs, and emergency alert drills.
            </p>
          </div>
          <div className="mt-6 flex items-center justify-between text-emerald-400 font-bold text-sm pt-4 border-t border-slate-800">
            <span>Launch Chatbot</span>
            <span className="text-lg group-hover:translate-x-1 transition-transform">→</span>
          </div>
        </Link>

        {/* Citizen View Card */}
        <Link 
          href="/citizen"
          className="group relative bg-slate-800 hover:bg-slate-750 border border-slate-700 hover:border-blue-500 rounded-2xl p-6 transition-all duration-200 shadow-xl flex flex-col justify-between"
        >
          <div className="space-y-3">
            <div className="w-12 h-12 rounded-xl bg-blue-600/20 text-blue-400 flex items-center justify-center font-bold border border-blue-500/30">
              <Shield className="w-6 h-6" />
            </div>
            <h2 className="text-xl font-bold text-white group-hover:text-blue-400 transition-colors">
              Citizen Portal
            </h2>
            <p className="text-slate-300 text-xs leading-relaxed">
              Simple, high-contrast, voice-first advisories tailored for citizens on low-cost devices.
            </p>
          </div>
          <div className="mt-6 flex items-center justify-between text-blue-400 font-bold text-sm pt-4 border-t border-slate-700/60">
            <span>Open Citizen Portal</span>
            <span className="text-lg group-hover:translate-x-1 transition-transform">→</span>
          </div>
        </Link>

        {/* Command Dashboard Card */}
        <Link 
          href="/dashboard"
          className="group relative bg-slate-800 hover:bg-slate-750 border border-slate-700 hover:border-amber-500 rounded-2xl p-6 transition-all duration-200 shadow-xl flex flex-col justify-between"
        >
          <div className="space-y-3">
            <div className="w-12 h-12 rounded-xl bg-amber-600/20 text-amber-400 flex items-center justify-center font-bold border border-amber-500/30">
              <LayoutDashboard className="w-6 h-6" />
            </div>
            <h2 className="text-xl font-bold text-white group-hover:text-amber-400 transition-colors">
              Command Dashboard
            </h2>
            <p className="text-slate-300 text-xs leading-relaxed">
              Live decision matrix for disaster officials with prioritized resource allocation and SitRep generation.
            </p>
          </div>
          <div className="mt-6 flex items-center justify-between text-amber-400 font-bold text-sm pt-4 border-t border-slate-700/60">
            <span>Open Command Portal</span>
            <span className="text-lg group-hover:translate-x-1 transition-transform">→</span>
          </div>
        </Link>
      </div>

      {/* Feature Highlights Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 border-t border-slate-800 pt-6">
        <div className="flex gap-3 p-4 rounded-xl bg-slate-800/40 border border-slate-800">
          <Volume2 className="w-5 h-5 text-blue-400 shrink-0 mt-0.5" />
          <div>
            <h3 className="font-semibold text-white text-sm">Voice & Low Literacy First</h3>
            <p className="text-xs text-slate-400 mt-0.5">30-second localized voice notes and visual action icons.</p>
          </div>
        </div>
        <div className="flex gap-3 p-4 rounded-xl bg-slate-800/40 border border-slate-800">
          <Smartphone className="w-5 h-5 text-blue-400 shrink-0 mt-0.5" />
          <div>
            <h3 className="font-semibold text-white text-sm">Works Offline & Low Bandwidth</h3>
            <p className="text-xs text-slate-400 mt-0.5">Optimized PWA for ₹5,000 Android phones and spotty signals.</p>
          </div>
        </div>
      </div>
    </div>
  );
}
