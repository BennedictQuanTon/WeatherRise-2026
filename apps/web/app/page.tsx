"use client";

import { useState, useRef, useEffect } from "react";
import dynamic from "next/dynamic";
import {
  Send, CloudLightning, Loader2, AlertTriangle,
  Wind, Droplets, Thermometer, MapPin, ExternalLink,
  Sun, Moon, Paperclip, Sliders, RefreshCw, Briefcase,
  Building, Leaf, Bell, Sparkles, LayoutGrid, Wifi,
  ShieldCheck, CheckCircle2, Calendar, Map
} from "lucide-react";

// Dynamic import — Leaflet requires window object (no SSR)
const TripMapPanel = dynamic(
  () => import("@/components/map/TripMapPanel"),
  {
    ssr: false,
    loading: () => (
      <div className="flex-1 flex items-center justify-center">
        <div className="w-8 h-8 rounded-full border-2 border-cyan-500 border-t-transparent animate-spin" />
      </div>
    ),
  }
);

// ─── Types ─────────────────────────────────────────────────
interface RiskAssessment {
  rain_risk: string;
  wind_risk: string;
  heat_risk: string;
  overall_risk: string;
  trip_disruption_risk?: string;
}

interface TripStop {
  order: number;
  place_id: string;
  name: string;
  lat: number;
  lon: number;
  time_block: string;
  planned_time: string;
  forecast_temp?: number;
  weather_condition?: string;
  duration_minutes: number;
  is_indoor: boolean;
  category: string;
  vibe_tags: string[];
}

interface TripDay {
  day: number;
  theme?: string;
  primary_area?: string;
  stops: TripStop[];
  backup_options?: any[];
  date?: string;
  weather_condition?: string;
  temp_range?: string;
  rain_prob?: number;
}

interface TripPlan {
  duration_days: number;
  location: string;
  days: TripDay[];
  weather_aware: boolean;
  planning_mode: string;
}

interface ChatResult {
  domain?: string;
  location?: string;
  prediction?: string;
  recommendation?: string;
  risk_assessment?: RiskAssessment;
  explanation?: string;
  final_answer?: string;
  trip_plan?: TripPlan;
  error?: string;
  status?: string;
  coordinates?: { latitude: number; longitude: number } | null;
  evidence?: string[];
  weather_stats?: Record<string, any>;
  time_range?: { start: string; end: string; raw_text?: string };
}

interface CityWeather {
  temp: number;
  condition: string;
  risk: string;
  humidity?: number;
  wind_speed?: number;
  precipitation?: number;
}

// ─── Helpers ────────────────────────────────────────────────
function riskBg(level: string) {
  const m: Record<string, string> = {
    low: "rgba(105,240,174,0.12)",
    medium: "rgba(255,179,0,0.12)",
    high: "rgba(255,82,82,0.12)",
    good: "rgba(105,240,174,0.1)",
    caution: "rgba(255,152,0,0.12)",
    poor: "rgba(255,82,82,0.12)",
  };
  return m[level?.toLowerCase()] ?? "rgba(255,255,255,0.05)";
}

function riskColor(level: string) {
  const m: Record<string, string> = {
    low: "#69f0ae",
    medium: "#ffb300",
    high: "#ff5252",
    good: "#69f0ae",
    caution: "#ff9800",
    poor: "#ff5252",
    unknown: "#8ba3b0",
  };
  return m[level?.toLowerCase()] ?? "#8ba3b0";
}

const DOMAIN_ICONS: Record<string, string> = {
  tourism: "🗺️",
  construction: "🏗️",
  agriculture: "🌾",
  unknown: "🌐",
};

// ─── Components ─────────────────────────────────────────────
function DaNangWeatherWidget({ weatherData, currentTime, currentDate }: { weatherData: Record<string, CityWeather>; currentTime: string; currentDate: string }) {
  const dn = weatherData["Da Nang"] || { temp: 31, condition: "High risk", risk: "High risk", humidity: 72, wind_speed: 18.5, precipitation: 5.0 };
  
  return (
    <div className="relative w-full h-[380px] rounded-3xl overflow-hidden border border-[var(--color-border-subtle)] shadow-2xl bg-cover bg-center"
      style={{ backgroundImage: "url('/map_bg.png')" }}>
      {/* Dark tint overlay */}
      <div className="absolute inset-0 bg-slate-950/50 backdrop-blur-[0.5px]" />
      
      {/* Live widget container */}
      <div className="absolute inset-0 p-6 flex flex-col justify-between">
        {/* Header: Widget title and Live status */}
        <div className="flex justify-between items-center">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-cyan-400 animate-ping" />
            <span className="w-2 h-2 rounded-full bg-cyan-400 absolute" />
            <span className="text-[10px] font-bold uppercase tracking-widest text-cyan-400 pl-3">Da Nang Live Station</span>
          </div>
          <span className="text-[9px] text-gray-400 font-medium">Station ID: #DN-OWM9</span>
        </div>

        {/* Middle part: Time & Big Temp */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-center my-auto">
          {/* Clock & Date */}
          <div className="space-y-1">
            <div className="text-3xl md:text-4xl font-extrabold font-mono tracking-wider text-cyan-300 drop-shadow-[0_0_8px_rgba(34,211,238,0.4)]">
              {currentTime || "12:00:00 PM"}
            </div>
            <div className="text-[10px] text-gray-300 font-medium tracking-wide">
              {currentDate || "Wednesday, June 10, 2026"}
            </div>
          </div>

          {/* Temperature & Condition */}
          <div className="flex items-center gap-4 md:justify-end">
            <div className="flex items-start">
              <span className="text-5xl md:text-6xl font-extrabold text-white tracking-tighter drop-shadow-md">
                {dn.temp}
              </span>
              <span className="text-2xl font-bold text-cyan-400">°C</span>
            </div>
            <div>
              <div className="flex items-center gap-1.5 font-bold text-xs text-white">
                <CloudLightning className="w-4 h-4 text-orange-400 shrink-0" />
                {dn.condition}
              </div>
              <div className="text-[9px] text-gray-300 mt-0.5">Weather condition</div>
            </div>
          </div>
        </div>

        {/* Bottom part: Metrics Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 pt-4 border-t border-white/10">
          <div className="flex items-center gap-2 px-3 py-2 rounded-xl bg-black/40 border border-white/5 backdrop-blur-md">
            <Wind className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
            <div>
              <div className="text-[9px] text-gray-400 leading-none">Wind Speed</div>
              <div className="text-xs font-bold text-white mt-1">{dn.wind_speed ?? 18.5} km/h</div>
            </div>
          </div>

          <div className="flex items-center gap-2 px-3 py-2 rounded-xl bg-black/40 border border-white/5 backdrop-blur-md">
            <Droplets className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
            <div>
              <div className="text-[9px] text-gray-400 leading-none">Humidity</div>
              <div className="text-xs font-bold text-white mt-1">{dn.humidity ?? 72}%</div>
            </div>
          </div>

          <div className="flex items-center gap-2 px-3 py-2 rounded-xl bg-black/40 border border-white/5 backdrop-blur-md">
            <Droplets className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
            <div>
              <div className="text-[9px] text-gray-400 leading-none">Rain Volume</div>
              <div className="text-xs font-bold text-white mt-1">{dn.precipitation ?? 5.0} mm</div>
            </div>
          </div>

          <div className="flex items-center gap-2 px-3 py-2 rounded-xl bg-black/40 border border-white/5 backdrop-blur-md">
            <ShieldCheck className="w-3.5 h-3.5 text-orange-400 shrink-0" />
            <div>
              <div className="text-[9px] text-gray-400 leading-none">Risk Index</div>
              <div className="text-xs font-bold text-orange-400 mt-1 uppercase">{dn.risk ?? "HIGH"}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function PopularCard({ title, desc, icon: Icon, bgUrl, onClick }: any) {
  return (
    <button onClick={onClick} className="relative group w-full text-left aspect-[4/3] rounded-2xl overflow-hidden border border-white/5 shadow-lg transition-transform hover:scale-[1.02] duration-300">
      {/* Background Image */}
      <div className="absolute inset-0 bg-cover bg-center transition-transform group-hover:scale-105 duration-500"
        style={{ backgroundImage: `url('${bgUrl}')` }} />
      {/* Gradient Overlay */}
      <div className="absolute inset-0 bg-gradient-to-t from-slate-950 via-slate-950/60 to-transparent" />
      
      {/* Content */}
      <div className="absolute inset-0 p-4 flex flex-col justify-between">
        <div className="w-8 h-8 rounded-lg flex items-center justify-center bg-white/10 backdrop-blur-md border border-white/10">
          <Icon className="w-4 h-4 text-cyan-400" />
        </div>
        <div>
          <h4 className="text-xs font-bold text-white mb-0.5">{title}</h4>
          <p className="text-[10px] text-gray-300 leading-tight line-clamp-2">{desc}</p>
        </div>
      </div>
      
      {/* Arrow Button */}
      <div className="absolute bottom-4 right-4 w-6 h-6 rounded-full flex items-center justify-center bg-white/10 backdrop-blur-md border border-white/10 group-hover:bg-cyan-500 group-hover:border-cyan-400 transition-colors">
        <Send size={8} className="text-white rotate-45" />
      </div>
    </button>
  );
}

function StepIndicator({ steps }: { steps: string[] }) {
  return (
    <div className="space-y-1.5 px-2 py-1 mt-4">
      {steps.map((s, i) => (
        <div key={i} className="flex items-center gap-2 text-xs text-cyan-400/80 animate-[fadeIn_0.3s_ease]">
          <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse shrink-0" />
          {s}
        </div>
      ))}
    </div>
  );
}

function RiskBadge({ label, value, Icon, detail }: { label: string; value: string; Icon: any; detail?: string }) {
  const color = riskColor(value);
  const bg = riskBg(value);
  return (
    <div className="flex-1 flex flex-col items-center gap-1.5 rounded-xl py-3 px-2 text-center border border-white/5"
      style={{ background: bg }}>
      <Icon size={16} style={{ color }} />
      <span className="text-[10px] text-[var(--color-text-muted)] uppercase tracking-wider">{label}</span>
      <span className="text-[12px] font-bold animate-pulse-subtle" style={{ color }}>{value?.toUpperCase() ?? "N/A"}</span>
      {detail && <span className="text-[9px] text-[var(--color-text-secondary)] mt-0.5">{detail}</span>}
    </div>
  );
}

// ─── Main ─────────────────────────────────────────────────
export default function HomePage() {
  const [input, setInput] = useState("");
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [steps, setSteps] = useState<string[]>([]);
  const [latestResult, setLatestResult] = useState<ChatResult | null>(null);
  const [activeDay, setActiveDay] = useState(1);
  const [theme, setTheme] = useState<"light" | "dark">("dark");
  const [showMap, setShowMap] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [weatherData, setWeatherData] = useState<Record<string, CityWeather>>({
    "Hanoi": { temp: 28, condition: "Heavy rain", risk: "Moderate" },
    "Da Nang": { temp: 31, condition: "High risk", risk: "High risk", humidity: 72, wind_speed: 18.5, precipitation: 5.0 },
    "Ho Chi Minh": { temp: 33, condition: "Moderate", risk: "Moderate" }
  });

  const [currentTime, setCurrentTime] = useState("");
  const [currentDate, setCurrentDate] = useState("");

  // Liveclock timer
  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      const timeStr = now.toLocaleTimeString("en-US", {
        timeZone: "Asia/Ho_Chi_Minh",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
        hour12: true
      });
      const dateStr = now.toLocaleDateString("en-US", {
        timeZone: "Asia/Ho_Chi_Minh",
        weekday: "long",
        year: "numeric",
        month: "long",
        day: "numeric"
      });
      setCurrentTime(timeStr);
      setCurrentDate(dateStr);
    };
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  // Fetch weather data
  useEffect(() => {
    const fetchWeather = async () => {
      try {
        const r = await fetch("/api/weather/current");
        if (r.ok) {
          const d = await r.json();
          setWeatherData(d);
        }
      } catch (e) {
        console.error("Failed to fetch live weather:", e);
      }
    };
    fetchWeather();
  }, []);

  // Theme support
  useEffect(() => {
    const saved = localStorage.getItem("theme") as "light" | "dark" | null;
    if (saved) {
      setTheme(saved);
      document.documentElement.className = saved;
    } else {
      document.documentElement.className = "dark";
    }
  }, []);

  const toggleTheme = () => {
    const next = theme === "dark" ? "light" : "dark";
    setTheme(next);
    localStorage.setItem("theme", next);
    document.documentElement.className = next;
  };

  const sendMessage = async (text: string) => {
    if (!text.trim() || loading) return;
    setLoading(true);
    setSteps(["Initializing parser agent..."]);
    setLatestResult(null);
    setActiveDay(1);
    setQuery(text);
    setInput("");

    const wsProto = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${wsProto}//${window.location.host}/ws`;

    try {
      const ws = new WebSocket(wsUrl);
      await new Promise<void>((resolve, reject) => {
        const timeout = setTimeout(() => reject(new Error("ws timeout")), 4000);
        ws.onopen = () => { clearTimeout(timeout); resolve(); };
        ws.onerror = () => { clearTimeout(timeout); reject(new Error("ws error")); };
      });

      ws.send(JSON.stringify({ message: text }));

      await new Promise<void>((resolve) => {
        ws.onmessage = (e) => {
          try {
            const ev = JSON.parse(e.data);
            if (ev.type === "step") {
              setSteps(prev => [...prev, ev.data?.message ?? ev.step]);
            } else if (ev.type === "result") {
              setLatestResult(ev.data);
              setActiveDay(1);
              if (ev.data?.trip_plan) setShowMap(true);
              ws.close();
              resolve();
            } else if (ev.type === "error") {
              setLatestResult({ error: ev.error });
              ws.close();
              resolve();
            }
          } catch {}
        };
        ws.onerror = () => resolve();
      });
    } catch {
      // REST Fallback
      try {
        setSteps(prev => [...prev, "Connecting to REST API..."]);
        const r = await fetch("/api/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message: text }),
        });
        const data: ChatResult = await r.json();
        setLatestResult(data);
        setActiveDay(1);
        if (data?.trip_plan) setShowMap(true);
      } catch (err: any) {
        setLatestResult({ error: "Cannot reach API server." });
      }
    }
    setLoading(false);
  };

  const handleKey = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-[var(--bg-primary)] text-[var(--color-text-primary)] transition-colors duration-300">
      {/* Header */}
      <header className="sticky top-0 z-50 border-b border-[var(--color-border)] backdrop-blur-xl bg-[var(--bg-primary)]/80 transition-colors duration-300">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl flex items-center justify-center animate-[pulse_3s_infinite]"
              style={{ background: "var(--color-brand-gradient)" }}>
              <CloudLightning size={17} className="text-white" />
            </div>
            <div>
              <h1 className="text-[var(--color-text-primary)] font-bold text-base tracking-tight leading-none">Weatherise</h1>
              <p className="text-[10px] text-[var(--color-text-muted)] mt-1">Weather Risk Intelligence · Powered by NVIDIA NIM</p>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <a href="/monitor" target="_blank" className="text-[11px] text-[var(--color-text-secondary)] hover:text-[var(--color-brand)] transition-colors flex items-center gap-1">
              <ExternalLink size={10} /> Monitor
            </a>
            
            {/* Theme Toggle */}
            <button onClick={toggleTheme} className="p-1.5 rounded-lg bg-[var(--bg-tertiary)] hover:bg-[var(--bg-tertiary-hover)] border border-[var(--color-border-subtle)] text-[var(--color-text-primary)] transition-all" title="Toggle theme">
              {theme === "dark" ? <Sun size={13} /> : <Moon size={13} />}
            </button>

            <div className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              <span className="text-[11px] text-[var(--color-text-secondary)]">Live</span>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 w-full max-w-7xl mx-auto px-6 py-8 flex flex-col justify-center">
        {(!loading && !latestResult) ? (
          /* INITIAL VIEW (Image 2) */
          <div className="space-y-8 animate-[fadeIn_0.4s_ease-out]">
            {/* Hero Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-center">
              <div className="lg:col-span-6 space-y-6">
                <h2 className="text-4xl md:text-5xl font-extrabold tracking-tight leading-[1.15] text-[var(--color-text-primary)]">
                  What's the weather <br />
                  risk for your plans?
                </h2>
                <p className="text-[var(--color-text-secondary)] text-sm md:text-base leading-relaxed max-w-lg">
                  AI-powered insights to help you plan smarter, safer, and ahead of the weather.
                </p>
                <div className="flex items-center gap-2.5 flex-wrap">
                  {[
                    { name: "Tourism", icon: Briefcase, q: "Plan a 3-day trip to Da Nang next week and avoid heavy rain" },
                    { name: "Construction", icon: Building, q: "Is tomorrow safe for concrete pouring at my construction site in Hanoi?" },
                    { name: "Agriculture", icon: Leaf, q: "Should I irrigate my rice farm this week in the Mekong Delta?" }
                  ].map((p, i) => {
                    const Icon = p.icon;
                    return (
                      <button key={i} onClick={() => { setInput(p.q); }}
                        className="flex items-center gap-2 text-xs font-semibold px-4 py-2.5 rounded-xl border border-[var(--color-border-subtle)] bg-[var(--bg-secondary)] hover:bg-[var(--bg-tertiary-hover)] hover:border-[var(--color-brand)] transition-all">
                        <Icon size={12} className="text-[var(--color-brand)]" />
                        {p.name}
                      </button>
                    );
                  })}
                </div>
              </div>
              <div className="lg:col-span-6">
                <DaNangWeatherWidget weatherData={weatherData} currentTime={currentTime} currentDate={currentDate} />
              </div>
            </div>

            {/* Input Composer Box */}
            <div className="w-full max-w-4xl mx-auto">
              <div className="w-full rounded-2xl border border-[var(--color-border)] bg-[var(--bg-secondary)]/90 backdrop-blur-md shadow-xl overflow-hidden">
                <div className="flex items-center gap-3 px-4 py-3.5">
                  <textarea
                    ref={textareaRef}
                    rows={1}
                    value={input}
                    onChange={e => setInput(e.target.value)}
                    onKeyDown={handleKey}
                    placeholder="Ask anything about weather risk for your plans..."
                    disabled={loading}
                    className="flex-1 bg-transparent text-sm text-[var(--color-text-primary)] placeholder-[var(--color-text-muted)] resize-none outline-none leading-relaxed"
                  />
                  <div className="flex items-center gap-3.5 shrink-0">
                    <button className="text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors">
                      <Paperclip size={16} />
                    </button>
                    <button className="text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors">
                      <Sliders size={16} />
                    </button>
                    <button onClick={() => sendMessage(input)} disabled={!input.trim() || loading}
                      className="w-9 h-9 rounded-full flex items-center justify-center shrink-0 transition-all bg-[var(--color-brand)] text-white hover:scale-105 disabled:opacity-40 disabled:hover:scale-100 shadow-md">
                      <Send size={13} className="rotate-45" />
                    </button>
                  </div>
                </div>
                
                {/* Suggestions */}
                <div className="flex items-center justify-between border-t border-[var(--color-border-subtle)] px-4 py-2.5 text-[10px] text-[var(--color-text-muted)] bg-[var(--bg-secondary)]/40">
                  <div className="flex items-center gap-4 flex-wrap">
                    {[
                      "Plan a 3-day trip to Da Nang next week",
                      "Is it safe to hike in Sa Pa this weekend?",
                      "Will heavy rain affect my construction?"
                    ].map((s, idx) => (
                      <button key={idx} onClick={() => { setInput(s); sendMessage(s); }} className="hover:text-[var(--color-brand)] transition-colors">
                        {s}
                      </button>
                    ))}
                  </div>
                  <button onClick={() => setInput("")} className="hover:text-[var(--color-brand)] transition-colors">
                    <RefreshCw size={11} />
                  </button>
                </div>
              </div>
            </div>

            {/* Popular Grid */}
            <div className="space-y-4 pt-4">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-bold tracking-wider uppercase text-[var(--color-text-primary)] flex items-center gap-2">
                  <CloudLightning size={12} className="text-[var(--color-brand)]" />
                  Explore popular questions
                </h3>
                <a href="#" className="text-xs text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors">View all &gt;</a>
              </div>
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                <PopularCard title="Plan a trip safely" desc="Get weather risk for your destination and activities" icon={Briefcase} bgUrl="/card_tourism.png" onClick={() => sendMessage("Plan a 3-day trip to Da Nang next week and avoid heavy rain")} />
                <PopularCard title="Construction safety" desc="Check rain, wind, and extreme weather impact" icon={Building} bgUrl="/card_construction.png" onClick={() => sendMessage("Is tomorrow safe for concrete pouring at my construction site in Hanoi?")} />
                <PopularCard title="Agriculture planning" desc="Optimize planting, irrigation and harvesting" icon={Leaf} bgUrl="/card_agriculture.png" onClick={() => sendMessage("Should I irrigate my rice farm this week in the Mekong Delta?")} />
                <PopularCard title="Severe weather alerts" desc="Stay ahead of storms, floods and extreme events" icon={Bell} bgUrl="/card_severe.png" onClick={() => sendMessage("Are there any severe weather alerts or typhoons near Da Nang this week?")} />
              </div>
            </div>

            {/* Footer boxes */}
            <div className="pt-4 border-t border-[var(--color-border-subtle)]">
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 p-4 rounded-2xl border border-[var(--color-border-subtle)] bg-[var(--bg-secondary)]/30 backdrop-blur-sm">
                {[
                  { title: "AI-Powered", desc: "Advanced AI models for accurate forecasts", icon: Sparkles },
                  { title: "High Resolution", desc: "Up to 3km resolution local forecasts", icon: LayoutGrid },
                  { title: "Real-time Data", desc: "Live updates from global weather sources", icon: Wifi },
                  { title: "Trusted Insights", desc: "Designed for Vietnam by weather experts", icon: ShieldCheck }
                ].map((f, idx) => {
                  const Icon = f.icon;
                  return (
                    <div key={idx} className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-lg flex items-center justify-center bg-[var(--bg-tertiary)] text-[var(--color-brand)]">
                        <Icon size={14} />
                      </div>
                      <div>
                        <div className="text-[10px] font-bold text-[var(--color-text-primary)]">{f.title}</div>
                        <div className="text-[9px] text-[var(--color-text-muted)] leading-tight">{f.desc}</div>
                      </div>
                    </div>
                  );
                })}
              </div>
              <p className="text-center text-[10px] text-[var(--color-text-muted)] mt-6">
                Weatherise AI · Built for Vietnam · Powered by NVIDIA NIM
              </p>
            </div>
          </div>
        ) : (
          /* ACTIVE / CHAT VIEW — V3: Left Output Canvas | Right Composer + Small Map */
          <div className="animate-[fadeIn_0.3s_ease] flex flex-col h-[calc(100vh-130px)]">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 flex-1 min-h-0">

              {/* ── LEFT: Large Output Canvas ─────────────────────── */}
              {(() => {
                const overallRisk = latestResult?.risk_assessment?.overall_risk?.toLowerCase() ?? "";
                const dynamicBorder = overallRisk === "high" 
                  ? "rgba(239, 68, 68, 0.25)" 
                  : overallRisk === "medium" 
                  ? "rgba(245, 158, 11, 0.22)" 
                  : "var(--color-border)";
                const dynamicBg = overallRisk === "high"
                  ? "radial-gradient(ellipse at 50% 0%, rgba(239, 68, 68, 0.08) 0%, var(--bg-secondary) 80%)"
                  : overallRisk === "medium"
                  ? "radial-gradient(ellipse at 50% 0%, rgba(245, 158, 11, 0.06) 0%, var(--bg-secondary) 80%)"
                  : "radial-gradient(ellipse at 50% 0%, rgba(34, 211, 238, 0.04) 0%, var(--bg-secondary) 80%)";

                return (
                  <div 
                    style={{ border: `1px solid ${dynamicBorder}`, background: dynamicBg }}
                    className="rounded-2xl p-5 shadow-xl overflow-y-auto flex flex-col gap-4 min-h-0"
                  >

                    {/* Header */}
                    <div className="flex items-center justify-between border-b border-[var(--color-border-subtle)] pb-4 flex-shrink-0">
                      <div className="flex items-center gap-2.5">
                        <div className="w-7 h-7 rounded-lg flex items-center justify-center" style={{ background: "var(--color-brand-gradient)" }}>
                          <CloudLightning size={13} className="text-white" />
                        </div>
                        <div>
                          <h3 className="text-xs font-bold leading-none">Weatherise</h3>
                          <p className="text-[9px] text-[var(--color-text-muted)] mt-0.5">Weather Risk Intelligence</p>
                        </div>
                      </div>
                      <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-emerald-950/30 border border-emerald-900/40 text-[9px] text-emerald-400">
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                        Live
                      </div>
                    </div>

                {/* Loading */}
                {loading && (
                  <div className="py-8 text-center space-y-4">
                    <Loader2 size={24} className="animate-spin text-[var(--color-brand)] mx-auto" />
                    <p className="text-xs text-[var(--color-text-secondary)]">Analyzing input & evaluating risk factors...</p>
                    <StepIndicator steps={steps} />
                  </div>
                )}

                {/* Result */}
                {latestResult && (
                  <div className="space-y-5">
                    {/* Badges */}
                    <div className="flex items-center justify-between flex-wrap gap-2 text-[10px] text-[var(--color-text-muted)]">
                      <div className="flex items-center gap-2">
                        {latestResult.domain && (
                          <span className="flex items-center gap-1.5 px-2 py-1 rounded-md bg-[var(--bg-tertiary)] border border-[var(--color-border-subtle)] text-[var(--color-brand)]">
                            {DOMAIN_ICONS[latestResult.domain] ?? "🌐"} {latestResult.domain}
                          </span>
                        )}
                        {latestResult.location && (
                          <span className="flex items-center gap-1.5 px-2 py-1 rounded-md bg-[var(--bg-tertiary)] border border-[var(--color-border-subtle)]">
                            <MapPin size={10} /> {latestResult.location}
                          </span>
                        )}
                      </div>
                      <span className="font-bold px-2 py-0.5 rounded-md text-[9px] uppercase tracking-wider"
                        style={{
                          color: riskColor(latestResult.risk_assessment?.overall_risk ?? "unknown"),
                          background: riskBg(latestResult.risk_assessment?.overall_risk ?? "unknown"),
                        }}>
                        {latestResult.risk_assessment?.overall_risk ?? "UNKNOWN"}
                      </span>
                    </div>

                    {/* Heading */}
                    {latestResult.location && (
                      <h3 className="text-xl font-bold leading-snug text-[var(--color-text-primary)]">
                        {latestResult.location} will likely experience{" "}
                        {latestResult.risk_assessment?.rain_risk?.toLowerCase() === "high"
                          ? "heavy rain"
                          : "some weather conditions"}{" "}
                        {latestResult.time_range?.raw_text ? latestResult.time_range.raw_text.toLowerCase() : "during this period"}.
                      </h3>
                    )}

                    {/* Final answer */}
                    {latestResult.final_answer && (
                      <p className="text-sm text-[var(--color-text-card-secondary)] leading-relaxed">
                        {latestResult.final_answer}
                      </p>
                    )}

                    {/* Risk Cards */}
                    {latestResult.risk_assessment && (
                      <div className="flex gap-3">
                        <RiskBadge 
                          label="Rain" 
                          value={latestResult.risk_assessment.rain_risk} 
                          Icon={Droplets} 
                          detail={latestResult.weather_stats?.max_rain_prob !== undefined ? `${latestResult.weather_stats.max_rain_prob}%` : undefined}
                        />
                        <RiskBadge 
                          label="Wind" 
                          value={latestResult.risk_assessment.wind_risk} 
                          Icon={Wind} 
                          detail={latestResult.weather_stats?.max_wind_speed !== undefined ? `${latestResult.weather_stats.max_wind_speed} km/h` : undefined}
                        />
                        <RiskBadge 
                          label="Heat" 
                          value={latestResult.risk_assessment.heat_risk} 
                          Icon={Thermometer} 
                          detail={latestResult.weather_stats?.max_temp !== undefined ? `${latestResult.weather_stats.max_temp}°C` : undefined}
                        />
                      </div>
                    )}

                    {/* Forecast */}
                    {latestResult.prediction && (
                      <div className="flex gap-3 p-3.5 rounded-xl border" style={{ background: "var(--box-cyan-bg)", borderColor: "var(--box-cyan-border)" }}>
                        <div className="w-8 h-8 rounded-full flex items-center justify-center shrink-0 bg-cyan-950/20 text-[var(--box-cyan-label)] border border-[var(--box-cyan-border)]">
                          <Calendar size={14} />
                        </div>
                        <div className="text-xs flex-1">
                          <div className="font-bold flex items-center justify-between" style={{ color: "var(--box-cyan-label)" }}>
                            <span>Forecast</span>
                            {latestResult.time_range?.start && latestResult.time_range?.end && (
                              <span className="text-[9px] font-medium px-2 py-0.5 rounded bg-cyan-950/40 text-cyan-300">
                                Forecast: {latestResult.time_range.start} to {latestResult.time_range.end}
                              </span>
                            )}
                          </div>
                          <p className="mt-1 leading-relaxed" style={{ color: "var(--box-cyan-text)" }}>{latestResult.prediction}</p>
                        </div>
                      </div>
                    )}

                    {/* Recommendation */}
                    {latestResult.recommendation && (
                      <div className="flex gap-3 p-3.5 rounded-xl border" style={{ background: "var(--box-emerald-bg)", borderColor: "var(--box-emerald-border)" }}>
                        <div className="w-8 h-8 rounded-full flex items-center justify-center shrink-0 bg-emerald-950/20 text-[var(--box-emerald-label)] border border-[var(--box-emerald-border)]">
                          <CheckCircle2 size={14} />
                        </div>
                        <div className="text-xs">
                          <div className="font-bold" style={{ color: "var(--box-emerald-label)" }}>Recommendation</div>
                          <p className="mt-1 leading-relaxed" style={{ color: "var(--box-emerald-text)" }}>{latestResult.recommendation}</p>
                        </div>
                      </div>
                    )}

                    {/* Trip Plan Cards */}
                    {latestResult.trip_plan && (
                      <div className="space-y-3 pt-2 border-t border-[var(--color-border-subtle)]">
                        <div className="flex items-center justify-between gap-2 text-xs font-bold text-[var(--color-text-primary)]">
                          <div className="flex items-center gap-2">
                            <Calendar size={12} className="text-[var(--color-brand)]" />
                            {latestResult.trip_plan.duration_days}-Day Trip Plan · {latestResult.trip_plan.location}
                          </div>
                          {latestResult.trip_plan.weather_aware && (
                            <span className="text-[9px] px-2 py-0.5 rounded-full bg-cyan-950/30 text-cyan-400 border border-cyan-900/40">
                              ⛅ Weather-Optimised
                            </span>
                          )}
                        </div>

                        {/* Day Tabs */}
                        {latestResult.trip_plan.days.length > 1 && (
                          <div className="flex gap-1.5 border-b border-[var(--color-border-subtle)] pb-2 mb-1">
                            {latestResult.trip_plan.days.map((d) => (
                              <button
                                key={d.day}
                                onClick={() => setActiveDay(d.day)}
                                className={`px-3 py-1.5 rounded-xl text-[10px] font-bold transition-all duration-200 ${
                                  activeDay === d.day
                                    ? "bg-cyan-500 text-slate-900 shadow-lg shadow-cyan-500/25"
                                    : "bg-white/5 text-slate-400 hover:bg-white/10 hover:text-white"
                                }`}
                              >
                                Day {d.day}
                              </button>
                            ))}
                          </div>
                        )}

                        {latestResult.trip_plan.days
                          .filter((d) => d.day === activeDay)
                          .map((day) => (
                            <div key={day.day} className="rounded-xl border border-[var(--color-border-subtle)] bg-[var(--bg-primary)] p-3 space-y-2 animate-[fadeIn_0.25s_ease]">
                              <div className="flex items-center justify-between">
                                <div className="flex items-center gap-2">
                                  <span className="w-5 h-5 rounded-full bg-cyan-500/20 text-cyan-400 text-[10px] font-black flex items-center justify-center flex-shrink-0">{day.day}</span>
                                  <span className="text-[10px] font-bold text-[var(--color-text-primary)]">{day.theme || `Day ${day.day}`}</span>
                                  {day.primary_area && <span className="text-[9px] text-[var(--color-text-muted)]">· {day.primary_area}</span>}
                                </div>
                                {(day.date || day.weather_condition) && (
                                  <span className="text-[9px] font-medium px-2 py-0.5 rounded bg-white/5 text-slate-300">
                                    {day.date && `${day.date}`} {day.weather_condition && `· ${day.weather_condition}`}
                                  </span>
                                )}
                              </div>
                              <div className="space-y-1.5">
                                {day.stops.map((stop) => {
                                  const blockColor: Record<string, string> = {
                                    morning: "#22d3ee", lunch: "#f59e0b",
                                    afternoon: "#818cf8", dinner: "#f97316", evening: "#a78bfa",
                                  };
                                  const col = blockColor[stop.time_block] || "#94a3b8";
                                  const catIcon: Record<string, string> = { restaurant: "🍜", beach: "🏖️", cafe: "☕", market: "🛒" };
                                  return (
                                    <div key={stop.place_id} className="flex items-center gap-2 text-[10px] px-2 py-1.5 rounded-lg hover:bg-white/5 transition-colors">
                                      <span style={{ color: col }} className="font-bold w-10 shrink-0 font-mono">{stop.planned_time}</span>
                                      <span className="text-[9px] shrink-0">{catIcon[stop.category] || "📍"}</span>
                                      <span className="text-[var(--color-text-secondary)] truncate flex-1">{stop.name}</span>
                                      {stop.weather_condition && (
                                        <span className="text-[9px] text-slate-400 max-w-[80px] truncate shrink-0">{stop.weather_condition}</span>
                                      )}
                                      <span className="text-[9px] shrink-0 px-1.5 py-0.5 rounded-full" style={{
                                        background: stop.is_indoor ? "rgba(129,140,248,0.15)" : "rgba(34,211,238,0.12)",
                                        color: stop.is_indoor ? "#818cf8" : "#22d3ee",
                                      }}>
                                        {stop.is_indoor ? "🏠" : "🌤"}
                                      </span>
                                      {stop.forecast_temp != null && (
                                        <span className="text-amber-400 text-[9px] shrink-0">🌡{stop.forecast_temp}°C</span>
                                      )}
                                    </div>
                                  );
                                })}
                              </div>
                            </div>
                          ))}
                      </div>
                    )}

                    {/* Explanation */}
                    {latestResult.explanation && (
                      <p className="text-[10px] text-[var(--color-text-card-muted)] italic leading-relaxed pt-2 border-t border-[var(--color-border-subtle)]">
                        {latestResult.explanation}
                      </p>
                    )}

                    {/* Error */}
                    {latestResult.error && (
                      <div className="flex items-center gap-2 text-xs text-red-400 bg-red-950/20 border border-red-900/30 rounded-xl p-3.5">
                        <AlertTriangle size={14} /> {latestResult.error}
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })()}

              {/* ── RIGHT: Composer (top) + Small Map (bottom ¼) ─── */}
              <div className="flex flex-col gap-4 min-h-0">

                {/* Query Composer */}
                <div className="flex-shrink-0 rounded-2xl border border-[var(--color-border)] bg-[var(--bg-secondary)] p-5 shadow-xl space-y-4 min-h-0">
                  <div>
                    <h3 className="text-xs font-bold uppercase tracking-wider text-[var(--color-brand)]">What would you like to know?</h3>
                    <p className="text-[10px] text-[var(--color-text-muted)] mt-1">Get intelligent weather risk insights for your plans.</p>
                  </div>
                  <div className="relative rounded-xl border border-[var(--color-border)] bg-[var(--bg-primary)] p-3 focus-within:border-[var(--color-brand)] transition-colors">
                    <textarea
                      rows={4}
                      value={input}
                      onChange={e => setInput(e.target.value)}
                      onKeyDown={handleKey}
                      placeholder="e.g. Plan a 3-day trip to Da Nang next week..."
                      disabled={loading}
                      maxLength={300}
                      className="w-full bg-transparent text-xs text-[var(--color-text-primary)] placeholder-[var(--color-text-muted)] resize-none outline-none leading-relaxed"
                    />
                    <div className="text-[10px] text-[var(--color-text-muted)] text-right mt-1">{input.length} / 300</div>
                  </div>
                  <div className="flex justify-end">
                    <button onClick={() => sendMessage(input)} disabled={!input.trim() || loading}
                      className="flex items-center gap-2 px-4 py-2 rounded-xl font-semibold text-xs text-white bg-[var(--color-brand)] hover:scale-[1.02] disabled:opacity-40 transition-all shadow-md">
                      <Sparkles size={12} /> Generate
                    </button>
                  </div>
                  <div className="pt-1 text-center text-[10px] text-[var(--color-text-muted)] border-t border-[var(--color-border-subtle)] pt-3">Weatherise AI • Powered by NVIDIA NIM</div>
                </div>

                {/* Small Map — expands to fill remaining space */}
                <div className="flex-1 rounded-2xl border border-[var(--color-border)] bg-[var(--bg-secondary)] shadow-xl overflow-hidden flex flex-col min-h-0">
                  <div className="flex items-center gap-2 px-4 py-2 border-b border-white/10 bg-slate-900/40 flex-shrink-0">
                    <Map size={11} className="text-cyan-400" />
                    <span className="text-[10px] font-bold text-slate-200">
                      {latestResult?.trip_plan ? `Trip Map · ${latestResult.trip_plan.location}` : latestResult?.location ? `Location · ${latestResult.location}` : "Map"}
                    </span>
                    {latestResult?.trip_plan && (
                      <span className="ml-auto text-[9px] text-slate-500">
                        {latestResult.trip_plan.duration_days} days
                      </span>
                    )}
                  </div>
                  <div className="flex-1 min-h-0 w-full relative">
                    <TripMapPanel 
                      tripPlan={latestResult?.trip_plan} 
                      coordinates={latestResult?.coordinates}
                      locationName={latestResult?.location}
                      activeDay={activeDay}
                    />
                  </div>
                </div>

              </div>{/* end right column */}
            </div>{/* end grid */}
          </div>
        )}

      </main>
    </div>
  );
}
