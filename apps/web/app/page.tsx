"use client";

import { useState, useRef, useEffect } from "react";
import {
  Send, CloudLightning, Loader2, AlertTriangle,
  Wind, Droplets, Thermometer, MapPin, ExternalLink,
} from "lucide-react";

// ─── Types ─────────────────────────────────────────────────
interface RiskAssessment {
  rain_risk: string;
  wind_risk: string;
  heat_risk: string;
  overall_risk: string;
  trip_disruption_risk?: string;
}

interface ChatResult {
  domain?: string;
  location?: string;
  prediction?: string;
  recommendation?: string;
  risk_assessment?: RiskAssessment;
  explanation?: string;
  final_answer?: string;
  error?: string;
  status?: string;
}

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  result?: ChatResult;
  steps?: string[];
  loading?: boolean;
}

// ─── Helpers ────────────────────────────────────────────────
function riskBg(level: string) {
  const m: Record<string, string> = {
    low: "rgba(105,240,174,0.12)", medium: "rgba(255,179,0,0.12)",
    high: "rgba(255,82,82,0.12)", good: "rgba(105,240,174,0.1)",
    caution: "rgba(255,152,0,0.12)", poor: "rgba(255,82,82,0.12)",
  };
  return m[level?.toLowerCase()] ?? "rgba(255,255,255,0.05)";
}
function riskColor(level: string) {
  const m: Record<string, string> = {
    low: "#69f0ae", medium: "#ffb300", high: "#ff5252",
    good: "#69f0ae", caution: "#ff9800", poor: "#ff5252", unknown: "#8ba3b0",
  };
  return m[level?.toLowerCase()] ?? "#8ba3b0";
}

const DOMAIN_ICONS: Record<string, string> = {
  tourism: "🗺️", construction: "🏗️", agriculture: "🌾", unknown: "🌐",
};

const EXAMPLES = [
  "Plan a 3-day trip to Da Nang next week and avoid heavy rain",
  "Is tomorrow safe for concrete pouring at my construction site in Hanoi?",
  "Should I irrigate my rice farm this week in the Mekong Delta?",
  "Can I go to Han Market in the next 3 days?",
];

// ─── Components ─────────────────────────────────────────────
function StepIndicator({ steps }: { steps: string[] }) {
  return (
    <div className="space-y-1.5 px-2 py-1">
      {steps.map((s, i) => (
        <div key={i} className="flex items-center gap-2 text-xs text-cyan-300/60 animate-[fadeIn_0.3s_ease]">
          <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse shrink-0" />
          {s}
        </div>
      ))}
    </div>
  );
}

function RiskBadge({ label, value, Icon }: { label: string; value: string; Icon: any }) {
  const color = riskColor(value);
  const bg = riskBg(value);
  return (
    <div className="flex-1 flex flex-col items-center gap-1.5 rounded-xl py-3 px-2 text-center border border-white/5"
      style={{ background: bg }}>
      <Icon size={14} style={{ color }} />
      <span className="text-[10px] text-gray-400 uppercase tracking-wider">{label}</span>
      <span className="text-[11px] font-bold" style={{ color }}>{value?.toUpperCase() ?? "N/A"}</span>
    </div>
  );
}

function ResultCard({ r }: { r: ChatResult }) {
  const overall = r.risk_assessment?.overall_risk ?? "unknown";
  return (
    <div className="mt-2 space-y-3">
      {/* Domain + location + overall */}
      <div className="flex items-center gap-2 flex-wrap">
        {r.domain && (
          <span className="text-xs px-2.5 py-1 rounded-full bg-white/5 border border-white/10 text-cyan-300">
            {DOMAIN_ICONS[r.domain]} {r.domain}
          </span>
        )}
        {r.location && (
          <span className="flex items-center gap-1 text-xs text-gray-500">
            <MapPin size={10} /> {r.location}
          </span>
        )}
        <span className="ml-auto text-[11px] font-bold px-2 py-0.5 rounded-full"
          style={{ color: riskColor(overall), background: riskBg(overall) }}>
          {overall.toUpperCase()}
        </span>
      </div>

      {/* Final answer */}
      {r.final_answer && (
        <p className="text-sm text-gray-200 leading-relaxed">{r.final_answer}</p>
      )}

      {/* Risk cards */}
      {r.risk_assessment && (
        <div className="flex gap-2">
          <RiskBadge label="Rain" value={r.risk_assessment.rain_risk} Icon={Droplets} />
          <RiskBadge label="Wind" value={r.risk_assessment.wind_risk} Icon={Wind} />
          <RiskBadge label="Heat" value={r.risk_assessment.heat_risk} Icon={Thermometer} />
        </div>
      )}

      {/* Prediction + Recommendation */}
      {r.prediction && (
        <div className="rounded-lg border border-cyan-900/20 bg-cyan-900/10 px-3 py-2 text-xs text-gray-300">
          <span className="text-cyan-400 font-semibold">Forecast: </span>{r.prediction}
        </div>
      )}
      {r.recommendation && (
        <div className="rounded-lg border border-emerald-900/20 bg-emerald-900/10 px-3 py-2 text-xs text-gray-300">
          <span className="text-emerald-400 font-semibold">Recommendation: </span>{r.recommendation}
        </div>
      )}
      {r.explanation && (
        <p className="text-[11px] text-gray-500 italic">{r.explanation}</p>
      )}
      {r.error && (
        <div className="flex items-center gap-2 text-xs text-red-400 bg-red-900/10 rounded-lg px-3 py-2">
          <AlertTriangle size={12} /> {r.error}
        </div>
      )}
    </div>
  );
}

function Bubble({ msg }: { msg: Message }) {
  if (msg.role === "user") {
    return (
      <div className="flex justify-end mb-4">
        <div className="max-w-[75%] rounded-2xl rounded-tr-sm px-4 py-3 text-sm text-white/90 leading-relaxed"
          style={{ background: "linear-gradient(135deg,rgba(0,80,150,0.6),rgba(0,180,255,0.2))", border: "1px solid rgba(0,180,255,0.25)" }}>
          {msg.content}
        </div>
      </div>
    );
  }
  return (
    <div className="flex justify-start mb-4">
      <div className="max-w-[90%] w-full rounded-2xl rounded-tl-sm px-4 py-3"
        style={{ background: "rgba(13,21,48,0.8)", border: "1px solid rgba(0,229,255,0.08)" }}>
        <div className="flex items-center gap-2 mb-2">
          <CloudLightning size={13} className="text-cyan-400" />
          <span className="text-[11px] font-semibold text-cyan-400 tracking-wide">Weatherise</span>
          {!msg.loading && msg.result && (
            <a href="/monitor" target="_blank" className="ml-auto flex items-center gap-1 text-[10px] text-gray-600 hover:text-cyan-500 transition-colors">
              <ExternalLink size={9} /> Monitor
            </a>
          )}
        </div>
        {msg.loading ? (
          <div>
            <div className="flex items-center gap-2 mb-2 text-xs text-cyan-400/60">
              <span className="flex gap-1">
                {[0,1,2].map(i => (
                  <span key={i} className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" style={{ animationDelay: `${i*0.2}s` }} />
                ))}
              </span>
              Weatherise is thinking...
            </div>
            {msg.steps && msg.steps.length > 0 && <StepIndicator steps={msg.steps} />}
          </div>
        ) : (
          <>
            {msg.content && <p className="text-sm text-gray-200">{msg.content}</p>}
            {msg.result && <ResultCard r={msg.result} />}
          </>
        )}
      </div>
    </div>
  );
}

// ─── Main ─────────────────────────────────────────────────
export default function HomePage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const updateLastMsg = (id: string, patch: Partial<Message>) => {
    setMessages(prev => prev.map(m => m.id === id ? { ...m, ...patch } : m));
  };

  const sendMessage = async (text: string) => {
    if (!text.trim() || loading) return;
    const userMsg: Message = { id: `u_${Date.now()}`, role: "user", content: text };
    const asstId = `a_${Date.now()}`;
    const asstMsg: Message = { id: asstId, role: "assistant", content: "", loading: true, steps: [] };
    setMessages(prev => [...prev, userMsg, asstMsg]);
    setInput("");
    setLoading(true);

    // WebSocket — proxied by Next.js rewrite at /ws
    const wsProto = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${wsProto}//${window.location.host}/ws`;
    let wsOk = false;

    try {
      const ws = new WebSocket(wsUrl);
      await new Promise<void>((resolve, reject) => {
        const timeout = setTimeout(() => reject(new Error("ws timeout")), 4000);
        ws.onopen = () => { clearTimeout(timeout); resolve(); };
        ws.onerror = () => { clearTimeout(timeout); reject(new Error("ws error")); };
      });

      wsOk = true;
      ws.send(JSON.stringify({ message: text }));

      await new Promise<void>((resolve) => {
        ws.onmessage = (e) => {
          try {
            const ev = JSON.parse(e.data);
            if (ev.type === "step") {
              setMessages(prev => prev.map(m =>
                m.id === asstId ? { ...m, steps: [...(m.steps ?? []), ev.data?.message ?? ev.step] } : m
              ));
            } else if (ev.type === "result") {
              updateLastMsg(asstId, { loading: false, result: ev.data, steps: [] });
              ws.close();
              resolve();
            } else if (ev.type === "error") {
              updateLastMsg(asstId, { loading: false, result: { error: ev.error } });
              ws.close();
              resolve();
            }
          } catch {}
        };
        ws.onerror = () => resolve();
      });
    } catch {
      // Fallback to REST via Next.js proxy
      try {
        updateLastMsg(asstId, { steps: ["Connecting to API..."] });
        const r = await fetch("/api/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message: text }),
        });
        const data: ChatResult = await r.json();
        updateLastMsg(asstId, { loading: false, result: data, steps: [] });
      } catch (err: any) {
        updateLastMsg(asstId, { loading: false, result: { error: "Cannot reach API server." } });
      }
    }
    setLoading(false);
  };

  const handleKey = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(input); }
  };

  return (
    <div className="min-h-screen flex flex-col bg-[#070c1a]">
      {/* Header */}
      <header className="sticky top-0 z-50 border-b border-cyan-900/20 backdrop-blur-xl bg-[#070c1a]/80">
        <div className="max-w-3xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl flex items-center justify-center"
              style={{ background: "linear-gradient(135deg,#00b4db,#0040ff)" }}>
              <CloudLightning size={17} className="text-white" />
            </div>
            <div>
              <h1 className="text-white font-bold text-base tracking-tight">Weatherise</h1>
              <p className="text-[10px] text-cyan-400/60">Weather-Risk Intelligence · Powered by NVIDIA NIM</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <a href="/monitor" className="text-[11px] text-gray-500 hover:text-cyan-400 transition-colors flex items-center gap-1">
              <ExternalLink size={10} /> Monitor
            </a>
            <div className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              <span className="text-[11px] text-gray-500">Live</span>
            </div>
          </div>
        </div>
      </header>

      {/* Chat */}
      <main className="flex-1 max-w-3xl w-full mx-auto px-6 py-6 flex flex-col">
        {messages.length === 0 && (
          <div className="flex-1 flex flex-col items-center justify-center gap-8">
            <div className="text-center">
              <div className="w-20 h-20 rounded-3xl mx-auto mb-6 flex items-center justify-center"
                style={{ background: "linear-gradient(135deg,rgba(0,180,255,0.15),rgba(0,64,255,0.15))", border: "1px solid rgba(0,180,255,0.15)" }}>
                <CloudLightning size={36} className="text-cyan-400" />
              </div>
              <h2 className="text-2xl font-bold text-white mb-2">What's the weather risk<br />for your plans?</h2>
              <p className="text-gray-500 text-sm max-w-sm mx-auto">Tourism · Construction · Agriculture — AI-powered analysis for Vietnam</p>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 w-full max-w-xl">
              {EXAMPLES.map(ex => (
                <button key={ex} onClick={() => sendMessage(ex)}
                  className="text-left text-xs text-gray-400 px-4 py-3 rounded-xl hover:text-gray-200 transition-all duration-200 leading-relaxed"
                  style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)" }}>
                  "{ex}"
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.length > 0 && (
          <div className="flex-1">
            {messages.map(m => <Bubble key={m.id} msg={m} />)}
            <div ref={bottomRef} />
          </div>
        )}
      </main>

      {/* Input */}
      <footer className="sticky bottom-0 border-t border-cyan-900/20 bg-[#070c1a]/90 backdrop-blur-xl">
        <div className="max-w-3xl mx-auto px-6 py-4">
          <div className="flex items-end gap-3 rounded-2xl px-4 py-3"
            style={{ background: "rgba(13,21,48,0.8)", border: "1.5px solid", borderColor: loading ? "rgba(0,229,255,0.4)" : "rgba(0,229,255,0.15)" }}>
            <textarea
              ref={textareaRef}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKey}
              placeholder="Ask about weather risk for your tourism, construction, or agriculture plans..."
              rows={1}
              disabled={loading}
              className="flex-1 bg-transparent text-sm text-gray-200 placeholder-gray-600 resize-none outline-none leading-relaxed max-h-32"
            />
            <button onClick={() => sendMessage(input)} disabled={!input.trim() || loading}
              className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0 transition-all hover:scale-105 disabled:opacity-30 disabled:hover:scale-100"
              style={{ background: "linear-gradient(135deg,#00b4db,#0040ff)" }}>
              {loading ? <Loader2 size={16} className="text-white animate-spin" /> : <Send size={16} className="text-white" />}
            </button>
          </div>
          <p className="text-center text-[10px] text-gray-700 mt-2">
            Enter to send · Shift+Enter for new line · NVIDIA Nemotron Nano 8B
          </p>
        </div>
      </footer>
    </div>
  );
}
