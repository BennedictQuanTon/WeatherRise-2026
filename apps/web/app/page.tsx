"use client";

import { useState, useRef, useEffect } from "react";
import { Send, CloudLightning, Loader2, AlertTriangle, CheckCircle2, Wind, Droplets, Thermometer, MapPin, Clock } from "lucide-react";

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
}

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  result?: ChatResult;
  loading?: boolean;
}

interface StepEvent {
  type: "step" | "result" | "error";
  step?: string;
  data?: any;
  error?: string;
}

// ─── Helpers ────────────────────────────────────────────────
function riskClass(level: string) {
  const map: Record<string, string> = {
    low: "risk-low", medium: "risk-medium", high: "risk-high",
    good: "risk-good", caution: "risk-caution", poor: "risk-poor", unknown: "text-gray-400",
  };
  return map[level?.toLowerCase()] ?? "text-gray-400";
}

function riskLabel(level: string) {
  const icons: Record<string, string> = { low: "✓", medium: "⚠", high: "✕", good: "✓", caution: "⚠", poor: "✕" };
  return `${icons[level?.toLowerCase()] ?? "?"} ${level?.toUpperCase() ?? "N/A"}`;
}

const DOMAIN_LABELS: Record<string, string> = {
  tourism: "🗺️ Tourism",
  construction: "🏗️ Construction",
  agriculture: "🌾 Agriculture",
  unknown: "🌐 General",
};

const EXAMPLES = [
  "Plan a 3-day trip to Da Nang next week and avoid heavy rain",
  "Is tomorrow safe for concrete pouring at my construction site in Hanoi?",
  "Should I irrigate my rice farm this week in the Mekong Delta?",
  "What are the outdoor conditions for hiking in Da Lat this weekend?",
];

// ─── Components ─────────────────────────────────────────────
function ThinkingDots() {
  return (
    <div className="flex items-center gap-1 px-4 py-3">
      <span className="text-xs text-cyan-400/60 mr-2">Weatherise is thinking</span>
      {[0, 1, 2].map((i) => (
        <div key={i} className="thinking-dot w-2 h-2 rounded-full bg-cyan-400" />
      ))}
    </div>
  );
}

function StepIndicator({ steps }: { steps: string[] }) {
  return (
    <div className="flex flex-col gap-1 px-4 py-2">
      {steps.map((s, i) => (
        <div key={i} className="flex items-center gap-2 text-xs text-cyan-300/70 slide-in">
          <div className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
          {s}
        </div>
      ))}
    </div>
  );
}

function RiskCard({ risk }: { risk: RiskAssessment }) {
  const items = [
    { label: "Rain", value: risk.rain_risk, Icon: Droplets },
    { label: "Wind", value: risk.wind_risk, Icon: Wind },
    { label: "Heat", value: risk.heat_risk, Icon: Thermometer },
  ];

  return (
    <div className="mt-3 grid grid-cols-3 gap-2">
      {items.map(({ label, value, Icon }) => (
        <div key={label} className={`glass flex flex-col items-center gap-1 py-2 px-3 text-center text-xs ${riskClass(value)}`}>
          <Icon size={14} />
          <span className="font-semibold uppercase tracking-wide">{label}</span>
          <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${riskClass(value)}`}>
            {value?.toUpperCase() ?? "N/A"}
          </span>
        </div>
      ))}
    </div>
  );
}

function ResultCard({ result }: { result: ChatResult }) {
  const overall = result.risk_assessment?.overall_risk ?? "unknown";
  return (
    <div className="mt-2 slide-in">
      {/* Header */}
      <div className="flex items-center gap-2 mb-3">
        {result.domain && (
          <span className="text-xs px-2 py-1 rounded-full glass text-cyan-300 font-medium">
            {DOMAIN_LABELS[result.domain] ?? result.domain}
          </span>
        )}
        {result.location && (
          <span className="flex items-center gap-1 text-xs text-gray-400">
            <MapPin size={11} /> {result.location}
          </span>
        )}
        <span className={`ml-auto text-xs px-2 py-1 rounded-full font-bold ${riskClass(overall)}`}>
          Overall: {overall?.toUpperCase()}
        </span>
      </div>

      {/* Final Answer */}
      {result.final_answer && (
        <p className="text-sm text-gray-200 leading-relaxed mb-3">{result.final_answer}</p>
      )}

      {/* Risk cards */}
      {result.risk_assessment && <RiskCard risk={result.risk_assessment} />}

      {/* Prediction */}
      {result.prediction && (
        <div className="mt-3 glass p-3 text-xs text-gray-300">
          <span className="text-cyan-400 font-semibold">Prediction: </span>{result.prediction}
        </div>
      )}

      {/* Recommendation */}
      {result.recommendation && (
        <div className="mt-2 glass p-3 text-xs text-gray-300">
          <span className="text-emerald-400 font-semibold">Recommendation: </span>{result.recommendation}
        </div>
      )}

      {/* Explanation */}
      {result.explanation && (
        <div className="mt-2 glass p-3 text-xs text-gray-400 italic">
          {result.explanation}
        </div>
      )}

      {/* Error */}
      {result.error && (
        <div className="mt-2 flex items-center gap-2 text-xs text-red-400 glass p-3">
          <AlertTriangle size={12} /> {result.error}
        </div>
      )}
    </div>
  );
}

function MessageBubble({ msg }: { msg: Message }) {
  if (msg.role === "user") {
    return (
      <div className="flex justify-end mb-4 slide-in">
        <div className="max-w-[80%] gradient-border px-4 py-3 text-sm text-white/90 leading-relaxed">
          {msg.content}
        </div>
      </div>
    );
  }

  return (
    <div className="flex justify-start mb-4 slide-in">
      <div className="max-w-[90%] glass px-4 py-3 w-full">
        <div className="flex items-center gap-2 mb-2">
          <CloudLightning size={14} className="text-cyan-400" />
          <span className="text-xs font-semibold text-cyan-400">Weatherise</span>
        </div>
        {msg.loading ? (
          <ThinkingDots />
        ) : (
          <>
            {msg.content && <p className="text-sm text-gray-200 mb-2">{msg.content}</p>}
            {msg.result && <ResultCard result={msg.result} />}
          </>
        )}
      </div>
    </div>
  );
}

// ─── Main Page ───────────────────────────────────────────────
export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [steps, setSteps] = useState<string[]>([]);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, steps]);

  const sendMessage = async (text: string) => {
    if (!text.trim() || loading) return;

    const userMsg: Message = { id: Date.now().toString(), role: "user", content: text };
    const assistantMsg: Message = {
      id: (Date.now() + 1).toString(), role: "assistant", content: "", loading: true,
    };

    setMessages((prev) => [...prev, userMsg, assistantMsg]);
    setInput("");
    setLoading(true);
    setSteps([]);

    try {
      // Try WebSocket first for streaming
      const wsUrl = `ws://${window.location.host}/ws`;
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;
      const currentSteps: string[] = [];

      ws.onopen = () => ws.send(JSON.stringify({ message: text }));

      ws.onmessage = (evt) => {
        const event: StepEvent = JSON.parse(evt.data);
        if (event.type === "step") {
          const label = event.data?.message || `${event.step}...`;
          currentSteps.push(label);
          setSteps([...currentSteps]);
        } else if (event.type === "result") {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantMsg.id
                ? { ...m, loading: false, content: "", result: event.data }
                : m
            )
          );
          setSteps([]);
          setLoading(false);
          ws.close();
        } else if (event.type === "error") {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantMsg.id
                ? { ...m, loading: false, result: { error: event.error } }
                : m
            )
          );
          setSteps([]);
          setLoading(false);
          ws.close();
        }
      };

      ws.onerror = async () => {
        // Fallback to REST
        ws.close();
        await fetchRest(text, assistantMsg.id);
      };
    } catch {
      await fetchRest(text, assistantMsg.id);
    }
  };

  const fetchRest = async (text: string, msgId: string) => {
    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text }),
      });
      const data = await res.json();
      setMessages((prev) =>
        prev.map((m) =>
          m.id === msgId ? { ...m, loading: false, content: "", result: data } : m
        )
      );
    } catch (e) {
      setMessages((prev) =>
        prev.map((m) =>
          m.id === msgId
            ? { ...m, loading: false, result: { error: "Could not connect to the API." } }
            : m
        )
      );
    } finally {
      setSteps([]);
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
    }
  };

  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="border-b border-cyan-900/30 glass sticky top-0 z-50">
        <div className="max-w-4xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-cyan-400 to-blue-600 flex items-center justify-center">
              <CloudLightning size={16} className="text-white" />
            </div>
            <div>
              <h1 className="font-bold text-white text-lg tracking-tight">Weatherise</h1>
              <p className="text-xs text-cyan-400/70">Weather-Risk Intelligence · Powered by NVIDIA NIM</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <span className="text-xs text-gray-400">Live</span>
          </div>
        </div>
      </header>

      {/* Chat Area */}
      <main className="flex-1 max-w-4xl w-full mx-auto px-6 py-6 flex flex-col">
        {messages.length === 0 && (
          <div className="flex-1 flex flex-col items-center justify-center gap-8 fade-in">
            {/* Hero */}
            <div className="text-center">
              <div className="w-20 h-20 rounded-3xl bg-gradient-to-br from-cyan-400/20 to-blue-600/20 border border-cyan-400/20 flex items-center justify-center mx-auto mb-6">
                <CloudLightning size={36} className="text-cyan-400" />
              </div>
              <h2 className="text-3xl font-bold text-white mb-3 tracking-tight">
                What's the weather risk<br/>for your plans?
              </h2>
              <p className="text-gray-400 text-sm max-w-md mx-auto leading-relaxed">
                Get AI-powered weather-risk intelligence for tourism, construction, and agriculture across Vietnam.
                Powered by NVIDIA Nemotron NIM.
              </p>
            </div>

            {/* Example chips */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 w-full max-w-2xl">
              {EXAMPLES.map((ex) => (
                <button
                  key={ex}
                  onClick={() => sendMessage(ex)}
                  className="glass text-left text-xs text-gray-300 px-4 py-3 rounded-xl hover:border-cyan-500/40 hover:text-cyan-200 transition-all duration-200 leading-relaxed"
                >
                  "{ex}"
                </button>
              ))}
            </div>

            {/* Domain chips */}
            <div className="flex gap-2">
              {Object.entries(DOMAIN_LABELS).filter(([k]) => k !== "unknown").map(([, v]) => (
                <span key={v} className="glass px-3 py-1.5 text-xs text-gray-400 rounded-full">{v}</span>
              ))}
            </div>
          </div>
        )}

        {/* Messages */}
        {messages.length > 0 && (
          <div className="flex-1 overflow-y-auto">
            {messages.map((msg) => (
              <MessageBubble key={msg.id} msg={msg} />
            ))}
            {steps.length > 0 && loading && <StepIndicator steps={steps} />}
            <div ref={bottomRef} />
          </div>
        )}
      </main>

      {/* Input Area */}
      <footer className="sticky bottom-0 border-t border-cyan-900/20 glass">
        <div className="max-w-4xl mx-auto px-6 py-4">
          <div className="gradient-border flex items-end gap-3 p-3">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask about weather risk for your tourism, construction, or agriculture plans..."
              className="flex-1 bg-transparent text-sm text-gray-200 placeholder-gray-500 resize-none outline-none min-h-[44px] max-h-[120px] leading-relaxed"
              rows={1}
              disabled={loading}
            />
            <button
              onClick={() => sendMessage(input)}
              disabled={!input.trim() || loading}
              className="w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center transition-all duration-200 hover:scale-105 disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:scale-100 shrink-0"
            >
              {loading ? (
                <Loader2 size={16} className="text-white animate-spin" />
              ) : (
                <Send size={16} className="text-white" />
              )}
            </button>
          </div>
          <p className="text-center text-[10px] text-gray-600 mt-2">
            Press Enter to send · Shift+Enter for new line · Powered by NVIDIA Nemotron Nano 8B
          </p>
        </div>
      </footer>
    </div>
  );
}
