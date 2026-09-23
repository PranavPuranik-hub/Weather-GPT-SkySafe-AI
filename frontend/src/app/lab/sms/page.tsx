"use client";

import { useState } from 'react';
import Link from 'next/link';
import { ArrowLeft, Send, Phone } from 'lucide-react';
import { getApiUrl } from '@/lib/api';

export default function SMSLab() {
  const [messages, setMessages] = useState([
    { type: 'in', text: 'SKYSAFE SEVERE CYCLONE CUTTACK. Evacuate to nearest shelter. REPLY 1=SAFE 2=HELP 3=WATER' }
  ]);
  const [input, setInput] = useState('');

  const handleSend = async () => {
    if (!input) return;
    
    // Add to UI
    setMessages(prev => [...prev, { type: 'out', text: input }]);
    
    // Send to backend webhook
    await fetch(getApiUrl('/api/sms/webhook'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ Body: input, From: "+919876543210", WardId: "Ward 7" })
    });
    
    setInput('');
  };

  return (
    <div className="min-h-screen bg-slate-900 flex items-center justify-center p-4">
      <div className="w-80 h-[600px] bg-black rounded-[3rem] border-8 border-slate-800 flex flex-col relative overflow-hidden shadow-2xl">
        {/* Phone Speaker Notch */}
        <div className="absolute top-0 inset-x-0 h-6 bg-slate-800 rounded-b-xl mx-auto w-32 flex items-center justify-center">
          <div className="w-12 h-1 bg-black rounded-full"></div>
        </div>

        {/* Header */}
        <div className="bg-emerald-600 text-white p-4 pt-8 flex items-center gap-3">
          <Link href="/"><ArrowLeft className="w-5 h-5" /></Link>
          <div className="font-bold flex-1">579-7233 (SKYSAFE)</div>
          <Phone className="w-4 h-4" />
        </div>

        {/* Message Thread */}
        <div className="flex-1 bg-slate-100 p-4 overflow-y-auto flex flex-col gap-3">
          <div className="text-center text-xs text-slate-400 font-semibold mb-2">Today 14:00</div>
          {messages.map((m, i) => (
            <div key={i} className={`max-w-[85%] rounded-2xl p-3 text-sm ${m.type === 'in' ? 'bg-white text-black self-start rounded-tl-none shadow-sm' : 'bg-emerald-500 text-white self-end rounded-tr-none'}`}>
              {m.text}
            </div>
          ))}
        </div>

        {/* Input Area */}
        <div className="bg-white p-3 flex gap-2 border-t">
          <input 
            type="text" 
            value={input}
            onChange={(e) => setInput(e.target.value)}
            className="flex-1 bg-slate-100 rounded-full px-4 py-2 text-black text-sm outline-none"
            placeholder="Text Message"
            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
          />
          <button 
            onClick={handleSend}
            className="w-10 h-10 rounded-full bg-emerald-500 flex items-center justify-center text-white"
          >
            <Send className="w-4 h-4 ml-1" />
          </button>
        </div>
      </div>
    </div>
  );
}
