import Link from 'next/link';
import { Volume2, ShieldAlert, ArrowLeft } from 'lucide-react';

export default function CitizenPage() {
  return (
    <div className="space-y-6 py-4">
      <div className="flex items-center justify-between">
        <Link 
          href="/" 
          className="inline-flex items-center gap-1.5 text-sm font-semibold text-blue-400 hover:text-blue-300"
        >
          <ArrowLeft className="w-4 h-4" /> Back to Home
        </Link>
        <span className="text-xs px-2.5 py-1 rounded-full bg-red-950 text-red-300 border border-red-800 font-medium">
          Active Warning Demo
        </span>
      </div>

      <header className="space-y-1">
        <h1 className="text-2xl sm:text-3xl font-bold text-white">Citizen Action Portal</h1>
        <p className="text-slate-400 text-sm">District: <strong className="text-white">Cuttack, Odisha</strong></p>
      </header>

      {/* Main Action Card - High Contrast & Large Text */}
      <div className="bg-gradient-to-br from-red-950/60 to-slate-900 border-2 border-red-600/80 rounded-2xl p-6 shadow-2xl space-y-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 bg-red-600/20 text-red-400 rounded-xl border border-red-500/40">
            <ShieldAlert className="w-8 h-8" />
          </div>
          <div>
            <h2 className="text-xl font-extrabold text-white">Heavy Cyclone & Flood Alert</h2>
            <p className="text-xs text-red-300 font-mono">Issued by IMD / NDMA SACHET (CAP)</p>
          </div>
        </div>

        {/* Audio Action Button */}
        <button className="w-full bg-blue-600 hover:bg-blue-500 active:scale-[0.98] text-white font-bold py-4 px-6 rounded-xl text-lg flex items-center justify-center gap-3 shadow-lg transition-transform">
          <Volume2 className="w-7 h-7" />
          <span>Listen to Voice Action (Hindi / Odia)</span>
        </button>

        {/* Conversational AI Chat Button */}
        <Link
          href="/chat"
          className="w-full bg-emerald-600 hover:bg-emerald-500 active:scale-[0.98] text-white font-bold py-4 px-6 rounded-xl text-lg flex items-center justify-center gap-3 shadow-lg transition-transform"
        >
          <Volume2 className="w-6 h-6" />
          <span>Ask WeatherGPT Chat & Voice Assistant →</span>
        </Link>

        {/* Grounded Action Bullet Points */}
        <div className="bg-slate-950/80 rounded-xl p-4 border border-slate-800 space-y-2 text-slate-200">
          <h3 className="font-bold text-sm text-blue-400 uppercase tracking-wide">Immediate Do&apos;s:</h3>
          <ul className="list-disc list-inside space-y-1 text-sm font-medium">
            <li>Move to nearest concrete shelter immediately.</li>
            <li>Keep emergency light and drinking water ready.</li>
            <li>Do not stand under trees or electric poles.</li>
          </ul>
        </div>
      </div>
    </div>
  );
}
