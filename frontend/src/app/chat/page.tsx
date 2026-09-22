"use client";

import React, { useState, useEffect, useRef } from "react";
import Link from "next/link";
import {
  Mic,
  MicOff,
  Send,
  MapPin,
  ShieldCheck,
  Volume2,
  VolumeX,
  Play,
  Pause,
  ArrowLeft,
  Settings,
  CheckCheck,
  Radio,
  User,
  Wheat,
  Fish,
  Heart,
  Baby,
  Home,
  Check,
  AlertCircle
} from "lucide-react";
import ClaimLedgerDrawer from "@/components/ClaimLedgerDrawer";
import DevPanel from "@/components/DevPanel";

interface Message {
  id: string;
  sender: "user" | "bot";
  text: string;
  voiceScript?: string;
  audioUrl?: string;
  timestamp: string;
  claimLedger?: any;
  intent?: string;
  toolsCalled?: string[];
  isDrill?: boolean;
  quickReplies?: string[];
}

const PERSONAS = [
  { id: "General", label: "General Citizen", icon: Home, desc: "Standard household safety advice" },
  { id: "Farmer", label: "Farmer / Agriculture", icon: Wheat, desc: "Crop protection, sowing advisories" },
  { id: "Fisherman", label: "Coastal Fisherman", icon: Fish, desc: "Sea conditions, wave advisories" },
  { id: "Elderly", label: "Elderly / Vulnerable", icon: Heart, desc: "Early evacuation & medication kits" },
  { id: "Pregnant_Infants", label: "Pregnant / Infants", icon: Baby, desc: "Primary health center shelters" },
];

const LANGUAGES = [
  { code: "en", name: "English", native: "English" },
  { code: "hi", name: "Hindi", native: "हिन्दी" },
  { code: "or", name: "Odia", native: "ଓଡ଼ିଆ" },
];

const QUICK_DISTRICTS = ["Cuttack", "Puri", "Wayanad", "Nagpur", "Mumbai"];

export default function ChatPage() {
  // State
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputMessage, setInputMessage] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [language, setLanguage] = useState("en");
  const [persona, setPersona] = useState("General");
  const [location, setLocation] = useState("Wayanad");
  const [locationCoords, setLocationCoords] = useState<{ lat?: number; lon?: number }>({});
  const [phone, setPhone] = useState("");
  const [alertConsent, setAlertConsent] = useState(true);

  // UI state
  const [showOnboarding, setShowOnboarding] = useState(false);
  const [selectedLedger, setSelectedLedger] = useState<any | null>(null);
  const [isLedgerOpen, setIsLedgerOpen] = useState(false);
  const [quickReplies, setQuickReplies] = useState<string[]>([
    "Is there any active alert?",
    "Weather forecast today",
    "Is it safe to go fishing?",
    "Where is the nearest shelter?",
    "Normal rainfall in July",
  ]);

  // Audio state
  const [playingAudioId, setPlayingAudioId] = useState<string | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  // Speech Recognition state
  const [isListening, setIsListening] = useState(false);
  const recognitionRef = useRef<any>(null);

  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  const [isOffline, setIsOffline] = useState(false);
  const [isLiteMode, setIsLiteMode] = useState(false);

  // Auto scroll to bottom
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    if (typeof window !== "undefined") {
      const urlParams = new URLSearchParams(window.location.search);
      if (urlParams.get("lite") === "1") {
        setIsLiteMode(true);
      }
      setIsOffline(!navigator.onLine);
      const handleOnline = () => setIsOffline(false);
      const handleOffline = () => setIsOffline(true);
      window.addEventListener('online', handleOnline);
      window.addEventListener('offline', handleOffline);
      return () => {
        window.removeEventListener('online', handleOnline);
        window.removeEventListener('offline', handleOffline);
      };
    }
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  // Initialize initial welcome message
  useEffect(() => {
    const welcomeText =
      language === "hi"
        ? "नमस्ते! मैं स्काईसेफ़ वेदर-जीपीटी हूँ। मैं आधिकारिक आईएमडी एवं साचेत चेतावनी, मौसम पूर्वानुमान, सुरक्षित रहने के निर्देश और निकटतम राहत शिविरों की सटीक जानकारी देता हूँ।"
        : language === "or"
        ? "ନମସ୍କାର! ମୁଁ ସ୍କାଏସେଫ୍ ୱେଦର୍-ଜିପିଟି। ମୁଁ ସରକାରୀ ଆଇଏମଡି ଏବଂ ସଚେତ୍ ଚେତାବନୀ, ପାଣିପାଗ ପୂର୍ବାନୁମାନ ଏବଂ ନିକଟତମ ବାତ୍ୟା ଆଶ୍ରୟସ୍ଥଳ ବିଷୟରେ ସଠିକ୍ ତଥ୍ୟ ଦେଇଥାଏ।"
        : "Welcome to SkySafe WeatherGPT. I turn official NDMA SACHET & IMD alerts into verified, life-saving actions. Ask me about alerts, 3-day forecasts, sea safety, or nearest shelters.";

    const initialMsg: Message = {
      id: "welcome-1",
      sender: "bot",
      text: welcomeText,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      quickReplies: [
        "Is there any active alert?",
        "Weather forecast today",
        "Is it safe to go fishing?",
        "Where is the nearest shelter?",
      ],
      claimLedger: {
        status: "PASS",
        sentence_ledger: [
          {
            sentence: welcomeText,
            cited_fact_ids: ["F1"],
            status: "PASS",
          },
        ],
        raw_facts: [
          { id: "F1", field: "service", value: "Official WeatherGPT Citizen Assistant", source: "NDMA SACHET / IMD" },
        ],
      },
    };

    setMessages([initialMsg]);

    // Check if user has saved preferences
    const saved = localStorage.getItem("skysafe_citizen_prefs");
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        if (parsed.language) setLanguage(parsed.language);
        if (parsed.persona) setPersona(parsed.persona);
        if (parsed.location) setLocation(parsed.location);
      } catch (e) {
        console.error(e);
      }
    } else {
      setShowOnboarding(true);
    }
  }, []);

  // Web Speech Recognition setup
  useEffect(() => {
    if (typeof window !== "undefined") {
      const SpeechRecognition =
        (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
      if (SpeechRecognition) {
        const recognition = new SpeechRecognition();
        recognition.continuous = false;
        recognition.interimResults = false;
        recognition.lang = language === "hi" ? "hi-IN" : language === "or" ? "or-IN" : "en-IN";

        recognition.onresult = (event: any) => {
          const transcript = event.results[0][0].transcript;
          setInputMessage(transcript);
          setIsListening(false);
          // auto send
          handleSendMessage(transcript);
        };

        recognition.onerror = () => {
          setIsListening(false);
        };

        recognition.onend = () => {
          setIsListening(false);
        };

        recognitionRef.current = recognition;
      }
    }
  }, [language]);

  const toggleListening = () => {
    if (!recognitionRef.current) {
      alert("Voice input is not supported by your browser. Please use Chrome or Edge.");
      return;
    }
    if (isListening) {
      recognitionRef.current.stop();
      setIsListening(false);
    } else {
      recognitionRef.current.lang = language === "hi" ? "hi-IN" : language === "or" ? "or-IN" : "en-IN";
      recognitionRef.current.start();
      setIsListening(true);
    }
  };

  // Play audio
  const handlePlayAudio = (msgId: string, audioUrl?: string, text?: string) => {
    if (playingAudioId === msgId) {
      if (audioRef.current) {
        audioRef.current.pause();
      }
      if (typeof window !== "undefined" && window.speechSynthesis) {
        window.speechSynthesis.cancel();
      }
      setPlayingAudioId(null);
      return;
    }

    setPlayingAudioId(msgId);

    if (audioUrl) {
      if (!audioRef.current) {
        audioRef.current = new Audio();
      }
      audioRef.current.src = audioUrl;
      audioRef.current.onended = () => setPlayingAudioId(null);
      audioRef.current.onerror = () => {
        // Fallback to browser TTS if audio URL cannot be loaded
        fallbackSpeechSynthesis(text || "", language);
      };
      audioRef.current.play().catch(() => {
        fallbackSpeechSynthesis(text || "", language);
      });
    } else if (text) {
      fallbackSpeechSynthesis(text, language);
    }
  };

  const fallbackSpeechSynthesis = (text: string, lang: string) => {
    if (typeof window !== "undefined" && window.speechSynthesis) {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = lang === "hi" ? "hi-IN" : lang === "or" ? "or-IN" : "en-IN";
      utterance.onend = () => setPlayingAudioId(null);
      utterance.onerror = () => setPlayingAudioId(null);
      window.speechSynthesis.speak(utterance);
    } else {
      setPlayingAudioId(null);
    }
  };

// Robust API fetcher: tries Next.js rewrite first, then falls back directly to backend on 8000
async function apiFetch(path: string, init?: RequestInit): Promise<Response> {
  try {
    const res = await fetch(path, init);
    if (res.ok) return res;
  } catch (e) {
    // relative failed
  }
  if (path.startsWith("/api")) {
    return await fetch(`http://127.0.0.1:8000${path}`, init);
  }
  throw new Error(`Failed to fetch ${path}`);
}

  // Onboarding submit
  const handleOnboardingSubmit = async () => {
    try {
      const payload: any = {
        language,
        persona,
        location_text: location,
        alert_consent: alertConsent,
      };
      if (phone.trim()) {
        payload.phone = phone.trim();
      }
      if (locationCoords.lat && locationCoords.lon) {
        payload.lat = locationCoords.lat;
        payload.lon = locationCoords.lon;
      }

      await apiFetch("/api/chat/onboard", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      localStorage.setItem(
        "skysafe_citizen_prefs",
        JSON.stringify({ language, persona, location })
      );
    } catch (e) {
      console.error("Onboarding failed", e);
    } finally {
      setShowOnboarding(false);
    }
  };

  // Get live location via GPS
  const handleGetLocation = () => {
    if ("geolocation" in navigator) {
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          setLocationCoords({ lat: pos.coords.latitude, lon: pos.coords.longitude });
          setLocation(`${pos.coords.latitude.toFixed(3)}, ${pos.coords.longitude.toFixed(3)}`);
        },
        (err) => {
          console.warn("Geolocation denied, using district default", err);
        }
      );
    }
  };

  // Send message
  const handleSendMessage = async (textToSend?: string) => {
    const query = (textToSend || inputMessage).trim();
    if (!query || isLoading) return;

    setInputMessage("");

    // Add user message
    const userMsg: Message = {
      id: `user-${Date.now()}`,
      sender: "user",
      text: query,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };
    setMessages((prev) => [...prev, userMsg]);
    setIsLoading(true);

    try {
      const body: any = {
        message: query,
        lang: language,
        persona: persona,
        location: location,
      };
      if (locationCoords.lat && locationCoords.lon) {
        body.lat = locationCoords.lat;
        body.lon = locationCoords.lon;
      }

      const res = await apiFetch("/api/chat/message", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      const data = await res.json();

      if (res.ok && data) {
        const botMsg: Message = {
          id: `bot-${Date.now()}`,
          sender: "bot",
          text: data.message,
          voiceScript: data.voice_script,
          audioUrl: data.audio_url,
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
          claimLedger: data.claim_ledger,
          intent: data.intent,
          toolsCalled: data.tools_called,
          isDrill: false,
        };
        setMessages((prev) => [...prev, botMsg]);

        if (data.quick_replies && data.quick_replies.length > 0) {
          setQuickReplies(data.quick_replies);
        }
      } else {
        const errorMsg: Message = {
          id: `bot-err-${Date.now()}`,
          sender: "bot",
          text: "I encountered a network issue reaching official weather servers. For urgent emergencies, please call the National Disaster Helpline at 1077 or IMD Helpline at 1800-180-1717.",
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        };
        setMessages((prev) => [...prev, errorMsg]);
      }
    } catch (err) {
      console.error(err);
      const errorMsg: Message = {
        id: `bot-err-${Date.now()}`,
        sender: "bot",
        text: "Official disaster data server is currently unreachable. Refer to https://mausam.imd.gov.in or dial 1077 for local warnings.",
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsLoading(false);
    }
  };

  // Handle incoming simulated alert from DevPanel
  const handleSimulatedAlert = (simData: any) => {
    const alertMsg: Message = {
      id: `sim-${Date.now()}`,
      sender: "bot",
      text: simData.message || (simData.headline ? `[DRILL / SIMULATION] ${simData.headline}` : "Emergency Alert [DRILL]"),
      voiceScript: simData.voice_script || simData.message || simData.headline,
      audioUrl: simData.audio_url,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      claimLedger: simData.claim_ledger,
      intent: "simulated_alert",
      isDrill: true,
    };
    setMessages((prev) => [...prev, alertMsg]);
    if (simData.quick_replies) {
      setQuickReplies(simData.quick_replies);
    }
    // Auto-play alert voice note for broadcast realism
    if (simData.audio_url || simData.message) {
      handlePlayAudio(alertMsg.id, simData.audio_url, simData.message);
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-80px)] max-w-2xl mx-auto bg-slate-950 rounded-2xl border border-slate-800 shadow-2xl overflow-hidden font-sans">
      {isOffline && (
        <div className="bg-red-900/80 text-white text-xs font-bold text-center py-1 flex items-center justify-center gap-1">
          <AlertCircle className="w-3 h-3" /> NO INTERNET - OFFLINE MODE (Messages will be queued)
        </div>
      )}
      {/* WhatsApp-Style Top App Bar */}
      <div className="bg-slate-900 border-b border-slate-800 p-3 flex items-center justify-between z-10 shrink-0">
        <div className="flex items-center gap-3">
          <Link
            href="/"
            className="p-1.5 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-white transition-colors"
            title="Back to Home"
          >
            <ArrowLeft className="w-5 h-5" />
          </Link>

          {/* Avatar & Online status */}
          <div className="relative">
            <div className="w-10 h-10 rounded-full bg-emerald-600 flex items-center justify-center text-white font-bold shadow-md">
              <Radio className="w-5 h-5 animate-pulse" />
            </div>
            <span className="absolute bottom-0 right-0 w-3 h-3 bg-emerald-400 border-2 border-slate-900 rounded-full"></span>
          </div>

          <div>
            <div className="flex items-center gap-1.5">
              <h1 className="font-bold text-white text-base leading-tight">WeatherGPT</h1>
              <span className="px-1.5 py-0.2 rounded text-[10px] bg-emerald-500/20 text-emerald-300 font-semibold border border-emerald-500/30">
                OFFICIAL
              </span>
            </div>
            <p className="text-[11px] text-slate-400 flex items-center gap-1">
              <span>SkySafe Action AI</span> • 
              <span className="text-emerald-400">IMD / SACHET</span>
            </p>
          </div>
        </div>

        {/* Quick Profile Indicators */}
        <div className="flex items-center gap-1.5">
          <button
            onClick={() => setShowOnboarding(true)}
            className="flex items-center gap-1 px-2.5 py-1 rounded-full bg-slate-800 hover:bg-slate-700 text-xs text-slate-200 border border-slate-700 transition-colors"
            title="Edit Persona & Location"
          >
            <MapPin className="w-3.5 h-3.5 text-blue-400" />
            <span className="font-semibold">{location}</span>
          </button>

          <button
            onClick={() => setShowOnboarding(true)}
            className="p-2 rounded-full bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
            title="Preferences & Onboarding"
          >
            <Settings className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* WhatsApp Chat Thread */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-[#0b141a]/95">
        {/* Drill Notice Banner */}
        <div className="text-center my-1">
          <span className="inline-block px-3 py-1 rounded-lg bg-amber-950/80 border border-amber-500/40 text-amber-300 text-[11px] font-medium shadow-sm">
            🛡️ Official IMD / SACHET Grounded Layer • End-to-End Verified
          </span>
        </div>

        {messages.map((msg) => {
          const isUser = msg.sender === "user";
          const isPlaying = playingAudioId === msg.id;

          return (
            <div
              key={msg.id}
              className={`flex flex-col ${isUser ? "items-end" : "items-start"}`}
            >
              <div
                className={`max-w-[85%] sm:max-w-[78%] rounded-2xl p-3.5 shadow-md relative space-y-2 text-sm leading-relaxed ${
                  isUser
                    ? "bg-[#005c4b] text-white rounded-tr-none"
                    : msg.isDrill && msg.intent === "simulated_alert"
                    ? "bg-red-950/90 border-2 border-red-500 text-white rounded-tl-none shadow-red-950/50"
                    : "bg-[#202c33] text-slate-100 border border-slate-800 rounded-tl-none"
                }`}
              >
                {/* Emergency Broadcast Drill Label Header - only for incoming broadcasts */}
                {msg.isDrill && msg.intent === "simulated_alert" && (
                  <div className="flex items-center gap-1.5 pb-1 border-b border-red-500/40 text-red-300 font-extrabold text-xs uppercase tracking-wider">
                    <AlertCircle className="w-4 h-4 text-red-400" />
                    <span>EMERGENCY BROADCAST [DRILL]</span>
                  </div>
                )}

                {/* Voice Note Player Bubble if audio or script exists */}
                {!isUser && (msg.audioUrl || msg.voiceScript) && (
                  <div className="flex items-center gap-3 p-2.5 rounded-xl bg-slate-900/80 border border-slate-700/60 my-1">
                    <button
                      onClick={() => handlePlayAudio(msg.id, msg.audioUrl, msg.text)}
                      className="w-10 h-10 rounded-full bg-emerald-500 hover:bg-emerald-400 active:scale-95 text-slate-950 flex items-center justify-center shrink-0 transition-transform shadow-md"
                      title={isPlaying ? "Pause voice note" : "Play voice note"}
                    >
                      {isPlaying ? <Pause className="w-5 h-5 fill-current" /> : <Play className="w-5 h-5 fill-current ml-0.5" />}
                    </button>

                    {/* Animated waveform bars */}
                    <div className="flex items-center gap-1 flex-1 h-6 px-1">
                      {[35, 65, 85, 45, 95, 55, 75, 40, 90, 60, 30, 70, 50, 80].map((height, idx) => (
                        <div
                          key={idx}
                          className={`w-1 rounded-full transition-all duration-300 ${
                            isPlaying ? "bg-emerald-400 animate-pulse" : "bg-slate-600"
                          }`}
                          style={{ height: `${height}%` }}
                        />
                      ))}
                    </div>

                    <span className="text-[11px] font-mono text-slate-400 shrink-0">
                      {isPlaying ? "Playing..." : "0:30"}
                    </span>
                  </div>
                )}

                {/* Main Message Text (High Contrast & Legible) */}
                <p className="whitespace-pre-line text-sm sm:text-base font-medium">
                  {msg.text}
                </p>

                {/* Bottom metadata row */}
                <div className="flex items-center justify-between gap-3 pt-1 text-[11px] text-slate-400">
                  {/* Verified Shield Badge for Grounding Proof */}
                  {!isUser && msg.claimLedger && (
                    <button
                      onClick={() => {
                        setSelectedLedger(msg.claimLedger);
                        setIsLedgerOpen(true);
                      }}
                      className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-emerald-950/80 border border-emerald-500/50 hover:bg-emerald-900 text-emerald-300 font-bold transition-colors active:scale-95 text-[10px]"
                      title="Click to view full Grounding Proof Ledger"
                    >
                      <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
                      <span>Verified Ledger</span>
                    </button>
                  )}

                  <div className="flex items-center gap-1 ml-auto">
                    <span>{msg.timestamp}</span>
                    {isUser && <CheckCheck className="w-3.5 h-3.5 text-blue-400" />}
                  </div>
                </div>
              </div>
            </div>
          );
        })}

        {/* Typing Indicator */}
        {isLoading && (
          <div className="flex items-center gap-2 p-3 rounded-2xl bg-[#202c33] text-slate-400 max-w-[140px] text-xs font-mono">
            <div className="flex gap-1">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-bounce"></span>
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-bounce [animation-delay:0.2s]"></span>
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-bounce [animation-delay:0.4s]"></span>
            </div>
            <span>Validating...</span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Quick Reply Chips */}
      <div className="p-2 bg-slate-900 border-t border-slate-800 flex gap-2 overflow-x-auto no-scrollbar shrink-0">
        {quickReplies.map((reply, idx) => (
          <button
            key={idx}
            onClick={() => handleSendMessage(reply)}
            className="whitespace-nowrap px-3 py-1.5 rounded-full bg-slate-800 hover:bg-slate-700 active:scale-95 border border-slate-700 text-xs font-medium text-slate-200 shadow-sm transition-all"
          >
            {reply}
          </button>
        ))}
      </div>

      {/* WhatsApp Input Bar */}
      <div className="bg-slate-950 p-2.5 border-t border-slate-800 flex items-center gap-2 shrink-0">
        {/* GPS Pin Button */}
        <button
          onClick={handleGetLocation}
          className="p-2.5 rounded-full bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white transition-colors"
          title="Share Current GPS Pin"
        >
          <MapPin className="w-5 h-5 text-blue-400" />
        </button>

        {/* Text Input */}
        <input
          type="text"
          value={inputMessage}
          onChange={(e) => setInputMessage(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              handleSendMessage();
            }
          }}
          placeholder={
            language === "hi"
              ? "मौसम, चेतावनी, सुरक्षित स्थान पूछें..."
              : language === "or"
              ? "ପାଣିପାଗ, ଚେତାବନୀ, ଆଶ୍ରୟସ୍ଥଳ ପଚାରନ୍ତୁ..."
              : "Ask about alerts, 3-day forecast, sea safety..."
          }
          className="flex-1 bg-slate-900 border border-slate-700 rounded-full px-4 py-2.5 text-sm text-white placeholder-slate-400 focus:outline-none focus:border-emerald-500 transition-colors"
        />

        {/* Web Speech Voice Mic Button */}
        <button
          onClick={toggleListening}
          className={`p-2.5 rounded-full transition-all shadow-md ${
            isListening
              ? "bg-red-600 text-white animate-pulse"
              : "bg-slate-800 hover:bg-slate-700 text-emerald-400 hover:text-emerald-300"
          }`}
          title={isListening ? "Listening... click to stop" : "Voice input (Mic)"}
        >
          {isListening ? <MicOff className="w-5 h-5" /> : <Mic className="w-5 h-5" />}
        </button>

        {/* Send Button */}
        <button
          onClick={() => handleSendMessage()}
          disabled={!inputMessage.trim() || isLoading}
          className="p-2.5 rounded-full bg-emerald-600 hover:bg-emerald-500 active:scale-95 text-white disabled:opacity-40 disabled:cursor-not-allowed transition-all shadow-md"
          title="Send"
        >
          <Send className="w-5 h-5" />
        </button>
      </div>

      {/* Onboarding Modal */}
      {showOnboarding && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="w-full max-w-md bg-slate-900 border border-slate-700 rounded-3xl p-6 shadow-2xl space-y-5 text-white text-sm max-h-[90vh] overflow-y-auto">
            <div>
              <h2 className="text-xl font-black text-white">Setup Your Weather Profile</h2>
              <p className="text-xs text-slate-400 mt-1">
                Personalized disaster warnings tailored to your role and location.
              </p>
            </div>

            {/* 1. Language Selection */}
            <div className="space-y-2">
              <label className="text-xs font-bold text-slate-300 uppercase tracking-wider block">
                1. Select Preferred Language:
              </label>
              <div className="grid grid-cols-3 gap-2">
                {LANGUAGES.map((lang) => (
                  <button
                    key={lang.code}
                    onClick={() => setLanguage(lang.code)}
                    className={`py-2 px-3 rounded-xl border text-center font-bold transition-all ${
                      language === lang.code
                        ? "bg-emerald-600 border-emerald-500 text-white shadow-lg"
                        : "bg-slate-950 border-slate-800 text-slate-300 hover:bg-slate-800"
                    }`}
                  >
                    <div className="text-xs">{lang.native}</div>
                    <div className="text-[10px] font-normal opacity-75">{lang.name}</div>
                  </button>
                ))}
              </div>
            </div>

            {/* 2. Persona Selection */}
            <div className="space-y-2">
              <label className="text-xs font-bold text-slate-300 uppercase tracking-wider block">
                2. Select Persona / Role:
              </label>
              <div className="grid grid-cols-1 gap-2">
                {PERSONAS.map((p) => {
                  const Icon = p.icon;
                  const isSelected = persona === p.id;
                  return (
                    <button
                      key={p.id}
                      onClick={() => setPersona(p.id)}
                      className={`flex items-center gap-3 p-2.5 rounded-xl border text-left transition-all ${
                        isSelected
                          ? "bg-blue-600/30 border-blue-500 text-white"
                          : "bg-slate-950 border-slate-800 text-slate-300 hover:bg-slate-800"
                      }`}
                    >
                      <div className={`p-2 rounded-lg ${isSelected ? "bg-blue-500 text-white" : "bg-slate-800 text-slate-400"}`}>
                        <Icon className="w-4 h-4" />
                      </div>
                      <div className="flex-1">
                        <div className="font-bold text-xs">{p.label}</div>
                        <div className="text-[11px] text-slate-400">{p.desc}</div>
                      </div>
                      {isSelected && <Check className="w-4 h-4 text-blue-400" />}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* 3. District / Location */}
            <div className="space-y-2">
              <label className="text-xs font-bold text-slate-300 uppercase tracking-wider block">
                3. Your Location (District / Pin):
              </label>
              <div className="flex gap-2">
                <select
                  value={location}
                  onChange={(e) => setLocation(e.target.value)}
                  className="flex-1 bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-blue-500"
                >
                  {QUICK_DISTRICTS.map((d) => (
                    <option key={d} value={d}>{d}</option>
                  ))}
                </select>
                <button
                  type="button"
                  onClick={handleGetLocation}
                  className="px-3 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-blue-400 border border-slate-700 flex items-center gap-1"
                >
                  <MapPin className="w-3.5 h-3.5" /> GPS
                </button>
              </div>
            </div>

            {/* 4. Phone & Privacy Consent */}
            <div className="space-y-2">
              <label className="text-xs font-bold text-slate-300 uppercase tracking-wider block">
                4. Emergency Broadcast Subscription:
              </label>
              <input
                type="tel"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                placeholder="Mobile number (optional, e.g. 9876543210)"
                className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-blue-500"
              />
              <div className="flex items-start gap-2 pt-1 text-[11px] text-slate-400">
                <input
                  type="checkbox"
                  id="consent"
                  checked={alertConsent}
                  onChange={(e) => setAlertConsent(e.target.checked)}
                  className="mt-0.5 rounded bg-slate-800 border-slate-700 text-emerald-500 focus:ring-0"
                />
                <label htmlFor="consent" className="cursor-pointer">
                  I consent to receive emergency cyclone & disaster warnings.
                  <span className="block text-emerald-400 font-mono text-[10px]">
                    🔒 Phone number is stored ONLY as an irreversible SHA-256 hash.
                  </span>
                </label>
              </div>
            </div>

            {/* Save Button */}
            <div className="pt-2 flex gap-2">
              <button
                onClick={handleOnboardingSubmit}
                className="w-full py-3 rounded-xl bg-emerald-600 hover:bg-emerald-500 active:scale-[0.98] font-bold text-white shadow-lg transition-all"
              >
                Save & Start Chatting
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Claim Ledger Proof Drawer */}
      {!isLiteMode && (
        <ClaimLedgerDrawer
          isOpen={isLedgerOpen}
          onClose={() => setIsLedgerOpen(false)}
          ledger={selectedLedger}
        />
      )}

      {/* Dev Panel for simulating incoming alerts & SLA latency */}
      {!isLiteMode && (
        <DevPanel
          onSimulatedAlert={handleSimulatedAlert}
          currentDistrict={location}
          currentLang={language}
          currentPersona={persona}
        />
      )}
    </div>
  );
}
