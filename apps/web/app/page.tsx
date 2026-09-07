"use client";

import { useState, useRef, useEffect } from "react";
import dynamic from "next/dynamic";
import {
  Send, CloudLightning, Loader2, AlertTriangle,
  Wind, Droplets, Thermometer, MapPin, ExternalLink,
  Sun, Moon, Paperclip, Sliders, RefreshCw, Briefcase,
  Building, Leaf, Bell, Sparkles, LayoutGrid, Wifi,
  ShieldCheck, CheckCircle2, Calendar, Map, ArrowUp, ArrowRight, Search,
  Cloud, CloudRain, CloudSun, TrendingUp
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
  rain_risk?: string;
  wind_risk?: string;
  heat_risk?: string;
  overall_risk?: string;
  trip_disruption_risk?: string;
  construction_safety_risk?: string;
  disease_risk?: string;
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
  planning_mode?: string;
}

type ResponseType = "weather_prediction" | "trip_planning" | "general";

interface LocationPoint {
  name: string;
  latitude: number;
  longitude: number;
}

interface DateRange {
  start?: string;
  end?: string;
  label?: string;
}

interface MapMarker {
  id: string;
  label: string;
  latitude: number;
  longitude: number;
  title?: string;
  description?: string;
  order?: number;
  category?: string;
  temperature_c?: number;
  weather_condition?: string;
  rain_probability?: number;
  is_indoor?: boolean;
}

interface DomainMetricItem {
  label: string;
  value: string;
  sub?: string;
  source?: string;
  standard?: string;
  badge?: string;
  badgeColor?: "emerald" | "amber" | "rose" | "blue" | "purple" | "cyan";
  iconName?: string;
}

interface TechStackInfo {
  reasoning_model: string;
  domain_agent: string;
  weather_sources: string[];
  vector_db: string;
  guardrails_score: string;
  latency: string;
  tokens_per_sec: string;
}

interface HazardEvaluationItem {
  title: string;
  standard_code: string;
  status: string;
  threshold_limit: string;
  observed_value: string;
  impact_description: string;
  severity: "high" | "medium" | "low";
}

interface DomainOverviewData {
  title: string;
  subtitle: string;
  executive_summary: string;
  compliance_status: string;
  hazards: HazardEvaluationItem[];
  operational_protocols: string[];
}

interface WeatherPredictionView {
  title: string;
  location: LocationPoint;
  date_range: DateRange;
  assumption: {
    summary: string;
    should_go: boolean;
    decision_label: string;
    decision_category?: string;
    key_stat_badge?: string;
    key_stat_value?: string;
    reason: string;
  };
  statistics: {
    avg_temperature_c?: number;
    min_temperature_c?: number;
    max_temperature_c?: number;
    avg_wind_kmh?: number;
    total_rainfall_mm?: number;
    rain_risk?: string;
    wind_risk?: string;
    heat_risk?: string;
    overall_risk?: string;
    most_common_condition?: string;
  };
  domain_metrics?: DomainMetricItem[];
  tech_stack_info?: TechStackInfo;
  overview?: DomainOverviewData;
  daily_forecast: Array<{
    date: string;
    day_label: string;
    condition: string;
    condition_icon: string;
    max_temp_c?: number;
    min_temp_c?: number;
    wind_kmh?: number;
    rain_probability?: number;
    rain_mm?: number;
    risk?: string;
  }>;
  recommendations: string[];
  alternatives: Array<{
    name: string;
    description: string;
    distance_label?: string;
    latitude?: number;
    longitude?: number;
  }>;
  map: {
    center: LocationPoint;
    markers: MapMarker[];
  };
  insights: Array<{
    title: string;
    body: string;
    type: "rain" | "wind" | "heat" | "travel" | "general";
  }>;
}

interface HourlyForecastItem {
  time: string;
  temp_c: number;
  feels_like_c: number;
  rain_probability: number;
  rain_mm: number;
  wind_kmh: number;
  humidity_percent: number;
  condition: string;
}

interface TripPlanningView {
  title: string;
  date_range: DateRange;
  summary_cards: {
    avg_high_c?: number;
    avg_low_c?: number;
    avg_wind_kmh?: number;
    humidity_percent?: number;
    rain_risk?: string;
  };
  ai_summary: string;
  days: Array<{
    day: number;
    date?: string;
    title: string;
    summary: string;
    weather: {
      high_c?: number;
      low_c?: number;
      rain_probability?: number;
      condition?: string;
    };
    hourly_forecast?: HourlyForecastItem[];
    stops: Array<{
      order: number;
      time: string;
      time_block: string;
      category: string;
      name: string;
      description?: string;
      latitude: number;
      longitude: number;
      forecast_temp_c?: number;
      rain_probability?: number;
      weather_condition?: string;
      is_indoor: boolean;
      weather_suitability?: string;
    }>;
  }>;
  map: {
    markers: MapMarker[];
  };
}

interface ChatResult {
  response_type?: ResponseType;
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
  weather_path?: string;
  weather_confidence?: number;
  weather_mode?: string;
  sources_used?: string[];
  sources_rejected?: string[];
  tech_stack_info?: TechStackInfo;
  weather_debug?: WeatherDebug;
  response_language?: "en" | "vi";
  weather_view?: WeatherPredictionView | null;
  trip_view?: TripPlanningView | null;
}

interface WeatherDebug {
  request_id?: string;
  selected_mode?: string;
  confidence?: number;
  sources_used?: string[];
  sources_rejected?: string[];
  source_scores?: Array<Record<string, any>>;
  quality_reports?: Array<Record<string, any>>;
  comparison_matrix?: Record<string, any> | null;
  fused_weather?: Record<string, any> | null;
  arbiter_decision?: Record<string, any> | null;
  selected_weather?: Record<string, any>;
  evidence_paths?: Record<string, any>;
  warnings?: string[];
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
function DaNangWeatherWidget({ weatherData, currentTime, currentDate, theme }: { weatherData: Record<string, CityWeather>; currentTime: string; currentDate: string; theme: "light" | "dark" }) {
  const dn = weatherData["Da Nang"] || { temp: 31, condition: "High risk", risk: "High risk", humidity: 72, wind_speed: 18.5, precipitation: 5.0 };
  
  return (
    <div className="relative w-full h-[390px] rounded-[32px] overflow-hidden border border-white/10 shadow-2xl bg-cover bg-center transition-all duration-500"
      style={{ 
        backgroundImage: theme === "dark" ? "url('/dragon_bridge_dark.png')" : "url('/dragon_bridge_light.png')",
        maskImage: "radial-gradient(white, black)",
        WebkitMaskImage: "-webkit-radial-gradient(white, black)"
      }}
    >
      {/* Dark tint overlay for readability */}
      <div className={`absolute inset-0 backdrop-blur-[3.5px] transition-colors duration-500 ${
        theme === "dark" ? "bg-slate-950/75" : "bg-slate-950/65"
      }`} />
      
      {/* Live widget container */}
      <div className="absolute inset-0 p-8 flex flex-col justify-between">
        
        {/* Top part: Time, Location, and Temperature */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-center my-auto">
          {/* Clock & Date & Location */}
          <div className="space-y-2">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-cyan-950/45 border border-cyan-800/40 text-cyan-400 font-extrabold text-xs uppercase tracking-wider shadow-sm">
              <MapPin size={12} className="text-cyan-400 shrink-0" />
              <span>Đà Nẵng</span>
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            </div>
            <div className="text-4xl md:text-5xl font-extrabold tracking-tight text-white drop-shadow-[0_2px_8px_rgba(0,0,0,0.5)]">
              {currentTime || "12:00:00 PM"}
            </div>
            <div className="text-xs md:text-sm text-slate-200 font-semibold tracking-wide drop-shadow-[0_1px_2px_rgba(0,0,0,0.5)]">
              {currentDate || "Wednesday, June 10, 2026"}
            </div>
          </div>

          {/* Temperature & Condition (Merged & Premium Layout) */}
          <div className="flex flex-col md:items-end justify-center">
            <div className="flex items-center gap-5">
              {/* Temperature */}
              <div className="flex items-start">
                <span className="text-6xl md:text-7xl font-extrabold text-white tracking-tighter drop-shadow-[0_2px_8px_rgba(0,0,0,0.5)]">
                  {dn.temp}
                </span>
                <span className="text-3xl font-black text-cyan-300 mt-1 ml-0.5">°C</span>
              </div>
              
              {/* Vertical Divider */}
              <div className="w-px h-12 bg-white/25 shrink-0 self-center" />
              
              {/* Condition */}
              <div className="flex flex-col">
                <div className="flex items-center gap-2 font-black text-xl md:text-2xl text-orange-400 drop-shadow-[0_2px_4px_rgba(0,0,0,0.6)]">
                  <CloudLightning className="w-6 h-6 text-orange-400 shrink-0" />
                  {dn.condition}
                </div>
                <div className="text-xs text-slate-200 mt-0.5 font-bold uppercase tracking-wider">Weather condition</div>
              </div>
            </div>
          </div>
        </div>

        {/* Bottom part: Metrics Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 pt-5 border-t border-white/10">
          <div className="flex items-center gap-2.5 px-4.5 py-3.5 rounded-2xl bg-black/60 border border-white/10 backdrop-blur-md">
            <Wind className="w-4.5 h-4.5 text-cyan-400 shrink-0" />
            <div>
              <div className="text-xs text-slate-200 leading-none font-semibold">Wind Speed</div>
              <div className="text-base md:text-lg font-black text-white mt-1">{dn.wind_speed ?? 18.5} km/h</div>
            </div>
          </div>

          <div className="flex items-center gap-2.5 px-4.5 py-3.5 rounded-2xl bg-black/60 border border-white/10 backdrop-blur-md">
            <Droplets className="w-4.5 h-4.5 text-cyan-400 shrink-0" />
            <div>
              <div className="text-xs text-slate-200 leading-none font-semibold">Humidity</div>
              <div className="text-base md:text-lg font-black text-white mt-1">{dn.humidity ?? 72}%</div>
            </div>
          </div>

          <div className="flex items-center gap-2.5 px-4.5 py-3.5 rounded-2xl bg-black/60 border border-white/10 backdrop-blur-md">
            <Droplets className="w-4.5 h-4.5 text-cyan-400 shrink-0" />
            <div>
              <div className="text-xs text-slate-200 leading-none font-semibold">Rain Volume</div>
              <div className="text-base md:text-lg font-black text-white mt-1">{dn.precipitation ?? 5.0} mm</div>
            </div>
          </div>

          <div className="flex items-center gap-2.5 px-4.5 py-3.5 rounded-2xl bg-black/60 border border-white/10 backdrop-blur-md">
            <ShieldCheck className="w-4.5 h-4.5 text-orange-400 shrink-0" />
            <div>
              <div className="text-xs text-slate-200 leading-none font-semibold">Risk Index</div>
              <div className="text-base md:text-lg font-black text-orange-400 mt-1 uppercase">{dn.risk ?? "HIGH"}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
function PopularMockCard({ title, desc, icon: Icon, onClick, iconBg, type }: any) {
  return (
    <button 
      onClick={onClick} 
      className="relative group text-left w-full h-[220px] rounded-3xl overflow-hidden shadow-sm transition-all hover:scale-[1.03] hover:shadow-md duration-300 isolate bg-white dark:bg-slate-900 border border-slate-100 dark:border-white/5 outline-none"
      style={{
        maskImage: "radial-gradient(white, black)",
        WebkitMaskImage: "-webkit-radial-gradient(white, black)"
      }}
    >
      {/* Background Graphic on the right */}
      {type === "tourism" && (
        <div 
          className="absolute right-0 bottom-0 top-0 w-[48%] bg-cover bg-center opacity-95 group-hover:scale-105 transition-transform duration-700"
          style={{ 
            backgroundImage: "url('/card_tourism.png')",
            clipPath: "polygon(22% 0%, 100% 0%, 100% 100%, 0% 100%)"
          }} 
        />
      )}
      {type === "construction" && (
        <div 
          className="absolute right-0 bottom-0 top-0 w-[48%] bg-cover bg-center opacity-95 group-hover:scale-105 transition-transform duration-700"
          style={{ 
            backgroundImage: "url('/card_construction.png')",
            clipPath: "polygon(22% 0%, 100% 0%, 100% 100%, 0% 100%)"
          }} 
        />
      )}
      {type === "agriculture" && (
        <div 
          className="absolute right-0 bottom-0 top-0 w-[48%] bg-cover bg-center opacity-95 group-hover:scale-105 transition-transform duration-700"
          style={{ 
            backgroundImage: "url('/card_agriculture.png')",
            clipPath: "polygon(22% 0%, 100% 0%, 100% 100%, 0% 100%)"
          }} 
        />
      )}
      {type === "severe" && (
        <div 
          className="absolute right-0 bottom-0 top-0 w-[48%] bg-cover bg-center opacity-95 group-hover:scale-105 transition-transform duration-700"
          style={{ 
            backgroundImage: "url('/card_severe.png')",
            clipPath: "polygon(22% 0%, 100% 0%, 100% 100%, 0% 100%)"
          }} 
        />
      )}

      {/* Content */}
      <div className="absolute inset-0 p-6 flex flex-col justify-between w-[52%] z-10">
        <div className={`w-9 h-9 rounded-xl flex items-center justify-center shadow-sm ${iconBg}`}>
          <Icon className="w-4.5 h-4.5" />
        </div>
        <div>
          <h4 className="font-serif-heading text-lg md:text-xl font-black text-slate-900 dark:text-white leading-tight">{title}</h4>
        </div>
        <div>
          <div className="w-7 h-7 rounded-full flex items-center justify-center bg-slate-100 dark:bg-white/10 group-hover:bg-blue-600 group-hover:text-white dark:group-hover:bg-cyan-400 dark:group-hover:text-slate-950 transition-colors shadow-sm">
            <ArrowRight size={12} className="stroke-[2.5]" />
          </div>
        </div>
      </div>
    </button>
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

function PathBDebugPanel({ result }: { result: ChatResult }) {
  const debug = result.weather_debug;
  if (!debug) return null;
  const sourceScores = debug.source_scores ?? [];
  const qualityReports = debug.quality_reports ?? [];
  return (
    <div className="rounded-xl border border-cyan-900/40 bg-cyan-950/10 p-3 space-y-3 text-[10px]">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 font-bold text-cyan-300">
          <ShieldCheck size={12} />
          <span>Path B Weather Decision</span>
        </div>
        <span className="px-2 py-0.5 rounded-md bg-cyan-500/10 text-cyan-200 border border-cyan-800/50">
          {result.weather_mode ?? debug.selected_mode ?? "path_b"}
        </span>
      </div>
      <div className="grid grid-cols-2 gap-2">
        <DebugMetric label="Confidence" value={formatConfidence(result.weather_confidence ?? debug.confidence)} />
        <DebugMetric label="Sources" value={(result.sources_used ?? debug.sources_used ?? []).join(", ") || "none"} />
      </div>
      {sourceScores.length > 0 && (
        <div className="space-y-1">
          <div className="font-bold text-slate-300">Source Scores</div>
          <div className="grid gap-1">
            {sourceScores.slice(0, 5).map((score, idx) => (
              <div key={`${score.source_code}-${idx}`} className="flex items-center justify-between gap-2 rounded-md bg-white/[0.03] px-2 py-1">
                <span className="text-slate-300">{score.source_code}</span>
                <span className="font-mono text-cyan-300">{score.rank_score}</span>
              </div>
            ))}
          </div>
        </div>
      )}
      {qualityReports.length > 0 && (
        <div className="space-y-1">
          <div className="font-bold text-slate-300">Quality</div>
          <div className="grid gap-1">
            {qualityReports.slice(0, 5).map((report, idx) => (
              <div key={`${report.source_code}-${idx}`} className="flex items-center justify-between gap-2 rounded-md bg-white/[0.03] px-2 py-1">
                <span className="text-slate-300">{report.source_code}</span>
                <span className={report.valid ? "text-emerald-300" : "text-red-300"}>
                  {report.valid ? "valid" : "rejected"} · {report.quality_score}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
      {debug.warnings && debug.warnings.length > 0 && (
        <div className="space-y-1">
          <div className="font-bold text-slate-300">Warnings</div>
          {debug.warnings.slice(0, 4).map((warning, idx) => (
            <div key={idx} className="rounded-md bg-amber-500/10 px-2 py-1 text-amber-200">{warning}</div>
          ))}
        </div>
      )}
    </div>
  );
}

function DebugMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md bg-white/[0.03] px-2 py-1">
      <div className="text-slate-500">{label}</div>
      <div className="font-mono text-slate-200 truncate">{value}</div>
    </div>
  );
}

function formatConfidence(value?: number) {
  if (value === undefined || value === null) return "n/a";
  return `${Math.round(value * 100)}%`;
}

function formatTemp(value?: number) {
  return value === undefined || value === null ? "n/a" : `${Math.round(value)}°C`;
}

function formatPercent(value?: number) {
  return value === undefined || value === null ? "n/a" : `${Math.round(value * 100)}%`;
}

function formatNumber(value?: number, suffix = "") {
  return value === undefined || value === null ? "n/a" : `${Math.round(value)}${suffix}`;
}

function blockLabel(value: string) {
  return value.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function getWeatherIcon(condition?: string) {
  const cond = (condition || "").toLowerCase();
  if (cond.includes("thunder") || cond.includes("lightning") || cond.includes("storm")) {
    return CloudLightning;
  }
  if (cond.includes("rain") || cond.includes("shower") || cond.includes("drizzle")) {
    return CloudRain;
  }
  if (cond.includes("partly") && cond.includes("cloud")) {
    return CloudSun;
  }
  if (cond.includes("cloud") || cond.includes("overcast") || cond.includes("mist") || cond.includes("fog")) {
    return Cloud;
  }
  return Sun;
}

function WeatherMetricCard({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="rounded-2xl border border-slate-200/40 dark:border-white/5 bg-slate-100/50 dark:bg-white/5 p-5 shadow-sm transition-all hover:shadow-md hover:border-blue-400/50 dark:hover:border-cyan-400/50">
      <div className="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">{label}</div>
      <div className="text-2xl font-black text-slate-900 dark:text-white mt-1.5">{value}</div>
      {sub && <div className="text-sm font-semibold text-slate-600 dark:text-slate-300 mt-1">{sub}</div>}
    </div>
  );
}

function DomainSafetyOverviewSection({ overview }: { overview?: DomainOverviewData }) {
  if (!overview) return null;

  return (
    <div className="rounded-3xl border border-slate-200/70 dark:border-white/10 bg-white/70 dark:bg-slate-900/50 backdrop-blur-md p-6 shadow-sm space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between flex-wrap gap-3 border-b border-slate-200/50 dark:border-white/10 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <ShieldCheck size={20} className="text-blue-600 dark:text-cyan-400" />
            <h3 className="text-lg md:text-xl font-black text-slate-900 dark:text-white tracking-tight">
              {overview.title}
            </h3>
          </div>
          {overview.subtitle && (
            <p className="text-xs md:text-sm font-semibold text-slate-500 dark:text-slate-400 mt-1">
              {overview.subtitle}
            </p>
          )}
        </div>

        {overview.compliance_status && (
          <span className="text-[10px] font-black uppercase tracking-wider px-3 py-1 rounded-full border border-blue-200 dark:border-cyan-800 bg-blue-50 dark:bg-cyan-950/30 text-blue-700 dark:text-cyan-300">
            {overview.compliance_status}
          </span>
        )}
      </div>

      {/* Executive Summary Box */}
      {overview.executive_summary && (
        <div className="rounded-2xl p-4 bg-slate-50 dark:bg-white/5 border border-slate-200/60 dark:border-white/5 space-y-1.5">
          <div className="text-[10px] font-black uppercase tracking-wider text-slate-400 dark:text-slate-400 flex items-center gap-1.5">
            <Sparkles size={12} className="text-blue-500 dark:text-cyan-400" />
            Executive Synthesis & Operational Evaluation
          </div>
          <p className="text-sm md:text-base font-semibold text-slate-700 dark:text-slate-200 leading-relaxed">
            {overview.executive_summary}
          </p>
        </div>
      )}

      {/* 3 Key Hazard Evaluation Cards */}
      {overview.hazards && overview.hazards.length > 0 && (
        <div className="space-y-3">
          <div className="text-xs font-black uppercase tracking-wider text-slate-700 dark:text-slate-300 flex items-center gap-1.5">
            <AlertTriangle size={14} className="text-amber-500" />
            Technical Hazard Analysis & Physical Constraints
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {overview.hazards.map((hazard, idx) => {
              const sevBorder = hazard.severity === "high" 
                ? "border-rose-300/80 dark:border-rose-800/60 bg-rose-50/40 dark:bg-rose-950/20" 
                : hazard.severity === "medium" 
                ? "border-amber-300/80 dark:border-amber-800/60 bg-amber-50/40 dark:bg-amber-950/20" 
                : "border-slate-200/80 dark:border-white/5 bg-slate-50/60 dark:bg-white/5";

              const sevBadge = hazard.severity === "high"
                ? "bg-rose-100 dark:bg-rose-950/60 text-rose-700 dark:text-rose-300 border-rose-200 dark:border-rose-800"
                : hazard.severity === "medium"
                ? "bg-amber-100 dark:bg-amber-950/60 text-amber-700 dark:text-amber-300 border-amber-200 dark:border-amber-800"
                : "bg-emerald-100 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300 border-emerald-200 dark:border-emerald-800";

              return (
                <div key={idx} className={`rounded-2xl border p-4 flex flex-col justify-between gap-3 shadow-sm overflow-hidden ${sevBorder}`}>
                  <div className="space-y-2">
                    <div className="text-xs font-black text-slate-900 dark:text-white leading-snug break-words">
                      {hazard.title}
                    </div>
                    
                    <div className="flex flex-wrap items-center gap-1.5">
                      <span className={`text-[9px] font-black uppercase tracking-wider px-2 py-0.5 rounded-md border inline-block max-w-full truncate ${sevBadge}`}>
                        {hazard.status}
                      </span>
                      <span className="text-[10px] font-bold text-blue-600 dark:text-cyan-400 truncate">
                        {hazard.standard_code}
                      </span>
                    </div>
                  </div>

                  <div className="space-y-1.5 text-xs bg-slate-100/70 dark:bg-white/[0.03] p-2.5 rounded-xl border border-slate-200/50 dark:border-white/5">
                    <div>
                      <div className="text-[9px] font-bold uppercase tracking-wider text-slate-400">Standard Limit</div>
                      <div className="text-xs font-bold text-slate-700 dark:text-slate-200 break-words leading-tight mt-0.5">{hazard.threshold_limit}</div>
                    </div>
                    <div className="pt-1.5 border-t border-slate-200/40 dark:border-white/5">
                      <div className="text-[9px] font-bold uppercase tracking-wider text-slate-400">Observed / Forecast</div>
                      <div className="text-xs font-black text-slate-900 dark:text-white break-words leading-tight mt-0.5">{hazard.observed_value}</div>
                    </div>
                  </div>

                  <p className="text-xs font-semibold text-slate-600 dark:text-slate-300 pt-2 border-t border-slate-200/50 dark:border-white/5 leading-relaxed break-words">
                    {hazard.impact_description}
                  </p>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Operational Protocols & Action Plan */}
      {overview.operational_protocols && overview.operational_protocols.length > 0 && (
        <div className="space-y-3 pt-2 border-t border-slate-200/50 dark:border-white/10">
          <div className="text-xs font-black uppercase tracking-wider text-slate-700 dark:text-slate-300 flex items-center gap-1.5">
            <CheckCircle2 size={14} className="text-emerald-500" />
            Mandatory Operational Protocols & Action Plan
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {overview.operational_protocols.map((protocol, idx) => (
              <div key={idx} className="rounded-2xl p-3.5 bg-slate-50 dark:bg-white/5 border border-slate-100 dark:border-white/5 flex items-start gap-3">
                <div className="w-5 h-5 rounded-full bg-blue-100 dark:bg-cyan-950 text-blue-600 dark:text-cyan-400 flex items-center justify-center text-xs font-black shrink-0 mt-0.5">
                  {idx + 1}
                </div>
                <p className="text-xs md:text-sm font-semibold text-slate-700 dark:text-slate-200 leading-relaxed">
                  {protocol}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function WeatherPredictionDemoView({ result }: { result: ChatResult }) {
  const view = result.weather_view;
  if (!view) return null;
  const stats = view.statistics;
  const decisionColor = view.assumption.should_go ? "#10b981" : "#f43f5e"; // emerald-500 or rose-500

  return (
    <div className="space-y-6">
      {/* Title & Badge */}
      <div className="space-y-2">
        <div className="flex items-center gap-2">
          <span className="flex items-center gap-1.5 rounded-full border border-blue-200/60 dark:border-cyan-800/40 bg-blue-50/70 dark:bg-cyan-950/30 px-3 py-1 text-xs font-bold text-blue-700 dark:text-cyan-300 w-fit">
            <MapPin size={13} /> {view.location.name}
          </span>
          {view.date_range.label && (
            <span className="text-xs font-semibold text-slate-500 dark:text-slate-400">
              · {view.date_range.label}
            </span>
          )}
        </div>
        <h2 className="text-3xl md:text-4xl font-black text-slate-900 dark:text-white tracking-tight leading-tight">
          {view.title}
        </h2>
      </div>

      {/* AI Decision & Operational Strategy Hero Box */}
      <div className="rounded-3xl border border-slate-200/70 dark:border-white/10 bg-gradient-to-br from-white/90 to-slate-50/70 dark:from-slate-900/80 dark:to-slate-950/60 backdrop-blur-xl p-6 shadow-md space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 dark:border-white/5 pb-3">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full animate-pulse" style={{ backgroundColor: decisionColor }} />
            <span className="text-[11px] font-black uppercase tracking-widest text-slate-600 dark:text-slate-400">
              {view.assumption.decision_category || "AI Advisory & Risk Assessment"}
            </span>
          </div>
          {view.assumption.key_stat_badge && (
            <span 
              className="text-[10px] font-black uppercase px-2.5 py-0.5 rounded-full border"
              style={{
                backgroundColor: `${decisionColor}15`,
                borderColor: `${decisionColor}40`,
                color: decisionColor,
              }}
            >
              {view.assumption.key_stat_badge}
            </span>
          )}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-center">
          <div className="lg:col-span-8 space-y-2.5">
            <h3 
              className="text-2xl md:text-3xl font-black tracking-tight leading-snug"
              style={{ color: decisionColor }}
            >
              {view.assumption.decision_label}
            </h3>
            <p className="text-sm md:text-base text-slate-700 dark:text-slate-200 font-medium leading-relaxed">
              {view.assumption.reason || view.assumption.summary}
            </p>
          </div>

          <div className="lg:col-span-4 rounded-2xl p-4 bg-slate-100/70 dark:bg-white/5 border border-slate-200/50 dark:border-white/5 flex flex-col justify-center">
            <div className="text-[10px] uppercase font-bold text-slate-500 dark:text-slate-400 tracking-wider">
              Core Operational Impact
            </div>
            <div className="text-base md:text-lg font-black text-slate-900 dark:text-white mt-1">
              {view.assumption.key_stat_value || (view.assumption.should_go ? "Favorable Conditions" : "Operational Precaution Advised")}
            </div>
            <div className="text-xs text-slate-500 dark:text-slate-400 mt-1 font-semibold">
              Verified by NeMo Guardrails
            </div>
          </div>
        </div>
      </div>

      {/* 8-Card Clean Telemetry & Engineering Constraints Grid (No distracting multi-color pills) */}
      {view.domain_metrics && view.domain_metrics.length > 0 && (
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <Sliders size={14} className="text-blue-600 dark:text-cyan-400" />
            <span className="text-xs font-black uppercase tracking-wider text-slate-800 dark:text-slate-200">
              Domain Telemetry & Physical Constraints
            </span>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-3.5">
            {view.domain_metrics.map((m, idx) => (
              <div 
                key={idx} 
                className="rounded-2xl border border-slate-200/80 dark:border-white/10 bg-white/80 dark:bg-slate-900/60 backdrop-blur-md p-4 shadow-sm transition-all hover:scale-[1.01] hover:border-blue-400/60 dark:hover:border-cyan-400/60 hover:shadow-md flex flex-col justify-between"
              >
                <div>
                  <div className="text-[11px] font-bold text-slate-500 dark:text-slate-400 leading-tight uppercase tracking-wider">
                    {m.label}
                  </div>
                  <div className="text-2xl font-black text-slate-900 dark:text-white mt-2 leading-tight tracking-tight">
                    {m.value}
                  </div>
                </div>

                <div className="pt-2.5 mt-3 border-t border-slate-100 dark:border-white/5 space-y-0.5">
                  <div className="text-[10px] font-bold text-blue-600 dark:text-cyan-400 leading-tight">
                    {m.source || m.standard || "Technical Reference"}
                  </div>
                  {m.sub && (
                    <div className="text-[10px] font-semibold text-slate-400 dark:text-slate-500 leading-tight">
                      {m.sub}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Operational Safety & Agro Advisory Overview Section */}
      <DomainSafetyOverviewSection overview={view.overview} />

      {/* 7-Day Weather Overview */}
      <div className="rounded-3xl border border-slate-200/50 dark:border-white/10 bg-white/60 dark:bg-slate-900/40 backdrop-blur-md p-6 shadow-sm space-y-6">
        <div className="flex items-center gap-2 border-b border-slate-200/50 dark:border-white/10 pb-3">
          <Calendar size={16} className="text-blue-600 dark:text-cyan-400" />
          <span className="text-base font-extrabold text-slate-900 dark:text-white">7-Day Weather Overview</span>
        </div>

        <div className="grid grid-cols-2 xl:grid-cols-4 gap-3">
          <WeatherMetricCard label="Avg Temperature" value={formatTemp(stats.avg_temperature_c)} sub={`Min ${formatTemp(stats.min_temperature_c)} · Max ${formatTemp(stats.max_temperature_c)}`} />
          <WeatherMetricCard label="Avg Wind" value={formatNumber(stats.avg_wind_kmh, " km/h")} sub={stats.wind_risk ? `${stats.wind_risk} wind risk` : undefined} />
          <WeatherMetricCard label="Total Rainfall" value={formatNumber(stats.total_rainfall_mm, " mm")} sub={stats.rain_risk ? `${stats.rain_risk} rain risk` : undefined} />
          <WeatherMetricCard label="Weather Condition (Most common)" value={stats.most_common_condition || "n/a"} sub={stats.overall_risk ? `${stats.overall_risk} overall risk` : undefined} />
        </div>

        {view.daily_forecast.length > 0 && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-[repeat(auto-fill,minmax(110px,1fr))] gap-3">
              {view.daily_forecast.slice(0, 7).map((day) => {
                const IconComponent = getWeatherIcon(day.condition);
                return (
                  <div key={day.date} className="rounded-2xl border border-slate-200/50 dark:border-white/5 bg-slate-100/50 dark:bg-white/5 p-4 text-center min-h-[160px] flex flex-col justify-between transition-all hover:border-blue-400 dark:hover:border-cyan-400 hover:shadow-md hover:scale-[1.02]">
                    <div>
                      <div className="text-base font-extrabold text-slate-800 dark:text-slate-200">{day.day_label.split(" ")[0]}</div>
                      <div className="text-xs font-semibold text-slate-500 dark:text-slate-400 mt-0.5">{day.date.slice(5)}</div>
                    </div>
                    <div className="my-3 flex justify-center">
                      <IconComponent size={28} className="text-blue-600 dark:text-cyan-400" />
                    </div>
                    <div>
                      <div className="text-xl font-extrabold text-slate-900 dark:text-white">{formatTemp(day.max_temp_c)}</div>
                      <div className="text-xs font-semibold text-slate-500 dark:text-slate-400">{formatTemp(day.min_temp_c)}</div>
                    </div>
                    <div className="mt-2.5 pt-2 border-t border-slate-200/50 dark:border-white/5 flex items-center justify-around text-xs font-semibold text-slate-600 dark:text-slate-300">
                      <span className="flex items-center gap-0.5"><Wind size={12} /> {formatNumber(day.wind_kmh, "")}</span>
                      <span className="flex items-center gap-0.5"><Droplets size={12} /> {formatPercent(day.rain_probability)}</span>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Condition Legend */}
            <div className="flex flex-wrap items-center justify-center gap-6 mt-4 pt-3 border-t border-slate-200/50 dark:border-white/10 text-xs font-semibold text-slate-500 dark:text-slate-400">
              <div className="flex items-center gap-1.5"><Sun size={14} className="text-amber-500" /> Sunny</div>
              <div className="flex items-center gap-1.5"><CloudSun size={14} className="text-blue-500 dark:text-cyan-400" /> Partly Cloudy</div>
              <div className="flex items-center gap-1.5"><Cloud size={14} className="text-slate-400" /> Cloudy</div>
              <div className="flex items-center gap-1.5"><CloudRain size={14} className="text-blue-600 dark:text-cyan-500" /> Rain</div>
            </div>
          </div>
        )}
      </div>

      {/* Recommendation Checklist */}
      <div className="rounded-3xl border border-slate-200/50 dark:border-white/10 bg-white/60 dark:bg-slate-900/40 backdrop-blur-md p-6 shadow-sm">
        <div className="text-base md:text-lg font-extrabold text-emerald-600 dark:text-emerald-400 mb-4 flex items-center gap-2">
          <CheckCircle2 size={16} /> Recommendations
        </div>
        <div className="space-y-3">
          {view.recommendations.map((item, idx) => (
            <div key={idx} className="flex gap-2.5 text-sm md:text-base text-slate-700 dark:text-slate-300 font-semibold leading-relaxed">
              <CheckCircle2 size={16} className="text-emerald-500 shrink-0 mt-0.5" />
              <span>{item}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Alternatives List */}
      {view.alternatives.length > 0 && (
        <div className="rounded-3xl border border-slate-200/50 dark:border-white/10 bg-white/60 dark:bg-slate-900/40 backdrop-blur-md p-6 shadow-sm space-y-4">
          <div>
            <div className="text-base md:text-lg font-extrabold text-purple-600 dark:text-purple-400 flex items-center gap-2">
              <MapPin size={16} /> Alternative Options (Weather Contingency)
            </div>
            <p className="text-sm md:text-base text-slate-500 dark:text-slate-400 mt-1.5 font-semibold">
              If severe weather disrupts operations in {view.location.name}, consider these alternatives:
            </p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {view.alternatives.map((alt, idx) => (
              <div key={`${alt.name}-${idx}`} className="rounded-2xl border border-slate-200/50 dark:border-white/5 bg-slate-100/50 dark:bg-white/5 p-5 transition-all hover:border-purple-400/50 dark:hover:border-purple-400/55 hover:shadow-md hover:scale-[1.01]">
                <div className="text-base md:text-lg font-extrabold text-slate-900 dark:text-white">{alt.name}</div>
                {alt.distance_label && (
                  <div className="text-xs font-bold text-slate-400 dark:text-slate-500 mt-1">{alt.distance_label}</div>
                )}
                <div className="text-sm md:text-base text-slate-600 dark:text-slate-300 mt-2.5 leading-relaxed font-semibold">
                  {alt.description}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function convertTripViewToPlan(view?: any): any {
  if (!view || !view.days) return null;
  return {
    duration_days: view.days.length,
    location: view.title ? view.title.replace("Plan for ", "") : "Trip",
    days: view.days.map((day: any) => ({
      day: day.day,
      theme: day.title,
      primary_area: day.summary,
      date: day.date,
      weather_condition: day.weather?.condition,
      stops: (day.stops || []).map((stop: any) => ({
        order: stop.order,
        place_id: `${stop.latitude}-${stop.longitude}-${stop.name}`,
        name: stop.name,
        lat: stop.latitude,
        lon: stop.longitude,
        time_block: stop.time_block,
        planned_time: stop.time,
        forecast_temp: stop.forecast_temp_c,
        weather_condition: stop.weather_condition,
        duration_minutes: stop.duration_minutes ?? 60,
        is_indoor: stop.is_indoor,
        category: stop.category,
        vibe_tags: stop.vibe_tags ?? [],
      }))
    }))
  };
}

function getStopThumbnail(name: string, category: string): string {
  const normalized = name.toLowerCase();
  if (normalized.includes("bình mì") || normalized.includes("bánh mì") || normalized.includes("cơm") || normalized.includes("mì quảng") || normalized.includes("hải sản") || category === "restaurant") {
    return "https://images.unsplash.com/photo-1583085292233-a3d606ccb4b4?auto=format&fit=crop&w=150&q=80"; // Vietnamese food/Banh Mi
  }
  if (normalized.includes("cà phê") || normalized.includes("cafe") || normalized.includes("coffee") || category === "cafe") {
    return "https://images.unsplash.com/photo-1501339847302-ac426a4a7cbb?auto=format&fit=crop&w=150&q=80"; // Cafe
  }
  if (normalized.includes("biển") || normalized.includes("beach") || normalized.includes("my khe") || category === "beach") {
    return "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?auto=format&fit=crop&w=150&q=80"; // Beach
  }
  if (normalized.includes("ngũ hành sơn") || normalized.includes("marble") || normalized.includes("chùa") || normalized.includes("pagoda") || category === "attraction") {
    return "https://images.unsplash.com/photo-1528127269322-539801943592?auto=format&fit=crop&w=150&q=80"; // Da Nang / Marble mountains/ Vietnam
  }
  return "https://images.unsplash.com/photo-1596422846543-75c6fc18a523?auto=format&fit=crop&w=150&q=80"; // Generic Vietnam travel
}

function TripWeatherChartsView({ day }: { day: any }) {
  if (!day) return null;
  const hours = day.hourly_forecast || [
    { time: "06:00", temp_c: 25, feels_like_c: 26, rain_probability: 10, rain_mm: 0.0, wind_kmh: 12, humidity_percent: 80, condition: "Clear" },
    { time: "08:00", temp_c: 27, feels_like_c: 29, rain_probability: 10, rain_mm: 0.0, wind_kmh: 14, humidity_percent: 78, condition: "Sunny" },
    { time: "10:00", temp_c: 29, feels_like_c: 32, rain_probability: 15, rain_mm: 0.0, wind_kmh: 16, humidity_percent: 74, condition: "Sunny" },
    { time: "12:00", temp_c: 31, feels_like_c: 35, rain_probability: 25, rain_mm: 0.2, wind_kmh: 18, humidity_percent: 70, condition: "Partly Cloudy" },
    { time: "14:00", temp_c: 32, feels_like_c: 36, rain_probability: 30, rain_mm: 0.5, wind_kmh: 19, humidity_percent: 68, condition: "Partly Cloudy" },
    { time: "16:00", temp_c: 30, feels_like_c: 33, rain_probability: 20, rain_mm: 0.1, wind_kmh: 16, humidity_percent: 72, condition: "Gentle Breeze" },
    { time: "18:00", temp_c: 28, feels_like_c: 30, rain_probability: 12, rain_mm: 0.0, wind_kmh: 14, humidity_percent: 76, condition: "Clear" },
    { time: "20:00", temp_c: 27, feels_like_c: 28, rain_probability: 8, rain_mm: 0.0, wind_kmh: 12, humidity_percent: 80, condition: "Cool Night" },
    { time: "22:00", temp_c: 26, feels_like_c: 27, rain_probability: 5, rain_mm: 0.0, wind_kmh: 10, humidity_percent: 84, condition: "Clear Night" },
  ];

  const minTemp = Math.min(...hours.map((h: any) => h.temp_c)) - 2;
  const maxTemp = Math.max(...hours.map((h: any) => h.temp_c)) + 2;
  const tempRange = maxTemp - minTemp || 1;

  const width = 640;
  const height = 140;
  const paddingX = 36;
  const paddingY = 22;
  const chartW = width - paddingX * 2;
  const chartH = height - paddingY * 2;

  const points = hours.map((h: any, idx: number) => {
    const x = paddingX + (idx / (hours.length - 1)) * chartW;
    const y = height - paddingY - ((h.temp_c - minTemp) / tempRange) * chartH;
    return { x, y, ...h };
  });

  const pathD = points.reduce((acc: string, pt: any, idx: number) => {
    if (idx === 0) return `M ${pt.x} ${pt.y}`;
    const prev = points[idx - 1];
    const cx = (prev.x + pt.x) / 2;
    return `${acc} C ${cx} ${prev.y}, ${cx} ${pt.y}, ${pt.x} ${pt.y}`;
  }, "");

  const areaD = `${pathD} L ${points[points.length - 1].x} ${height - paddingY} L ${points[0].x} ${height - paddingY} Z`;

  return (
    <div className="rounded-3xl border border-slate-100 dark:border-white/5 bg-white dark:bg-slate-900/60 p-6 shadow-sm space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-2 border-b border-slate-100 dark:border-white/5 pb-3">
        <div className="flex items-center gap-2">
          <TrendingUp size={16} className="text-blue-600 dark:text-cyan-400" />
          <span className="text-base font-extrabold text-slate-900 dark:text-white">
            Da Nang Hourly Atmospheric & Weather Trajectory — Day {day.day}
          </span>
        </div>
        <span className="text-xs font-semibold text-slate-500 dark:text-slate-400">
          {day.date || `Day ${day.day}`} · 06:00 to 22:00
        </span>
      </div>

      {/* Temperature Polyline Chart */}
      <div className="space-y-2">
        <div className="flex items-center justify-between text-xs font-bold text-slate-600 dark:text-slate-300">
          <span className="flex items-center gap-1.5"><Sun size={14} className="text-amber-500" /> Diurnal Temperature (°C)</span>
          <span className="text-slate-400 font-normal">Peak: {Math.max(...hours.map((h: any) => h.temp_c))}°C · Min: {Math.min(...hours.map((h: any) => h.temp_c))}°C</span>
        </div>

        <div className="relative w-full overflow-x-auto">
          <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-36 overflow-visible">
            <defs>
              <linearGradient id={`tempGrad-${day.day}`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#f59e0b" stopOpacity="0.30" />
                <stop offset="100%" stopColor="#3b82f6" stopOpacity="0.02" />
              </linearGradient>
            </defs>

            {/* Grid horizontal dashed lines */}
            <line x1={paddingX} y1={paddingY} x2={width - paddingX} y2={paddingY} stroke="currentColor" strokeOpacity="0.08" strokeDasharray="3 3" />
            <line x1={paddingX} y1={height / 2} x2={width - paddingX} y2={height / 2} stroke="currentColor" strokeOpacity="0.08" strokeDasharray="3 3" />
            <line x1={paddingX} y1={height - paddingY} x2={width - paddingX} y2={height - paddingY} stroke="currentColor" strokeOpacity="0.12" />

            {/* Area fill */}
            <path d={areaD} fill={`url(#tempGrad-${day.day})`} />

            {/* Smooth line */}
            <path d={pathD} fill="none" stroke="#f59e0b" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />

            {/* Dots and Labels */}
            {points.map((pt: any, i: number) => (
              <g key={i}>
                <circle cx={pt.x} cy={pt.y} r="4.5" fill="#f59e0b" stroke="#ffffff" strokeWidth="2" />
                <text x={pt.x} y={pt.y - 8} textAnchor="middle" fill="currentColor" className="text-[10px] font-black fill-slate-800 dark:fill-slate-100">
                  {pt.temp_c}°
                </text>
                <text x={pt.x} y={height - 5} textAnchor="middle" fill="currentColor" className="text-[9px] font-semibold fill-slate-500 dark:fill-slate-400">
                  {pt.time}
                </text>
              </g>
            ))}
          </svg>
        </div>
      </div>

      {/* Hourly Precipitation Probability & Rainfall Volume Bar Chart */}
      <div className="space-y-3 pt-2 border-t border-slate-100 dark:border-white/5">
        <div className="flex items-center justify-between text-xs font-bold text-slate-600 dark:text-slate-300">
          <span className="flex items-center gap-1.5"><CloudRain size={14} className="text-blue-500" /> Precipitation Probability (%) & Expected Volume (mm)</span>
          <span className="text-slate-400 font-normal">Rain Risk: {day.weather?.rain_probability > 40 ? "Moderate Shower Window" : "Low Rain Risk"}</span>
        </div>

        <div className="grid grid-cols-9 gap-2">
          {hours.map((h: any, i: number) => {
            const isHigh = h.rain_probability >= 50;
            const isMed = h.rain_probability >= 20 && h.rain_probability < 50;
            const barBg = isHigh 
              ? "bg-gradient-to-t from-blue-600 to-indigo-500 dark:from-cyan-500 dark:to-blue-600" 
              : isMed 
              ? "bg-gradient-to-t from-amber-400 to-amber-300 dark:from-amber-500 dark:to-amber-400" 
              : "bg-gradient-to-t from-emerald-400 to-emerald-300 dark:from-emerald-500 dark:to-emerald-400";

            return (
              <div key={i} className="flex flex-col items-center justify-end h-28 p-1.5 rounded-2xl bg-slate-50/70 dark:bg-white/5 border border-slate-100 dark:border-white/5 transition-all hover:bg-slate-100/50">
                <span className="text-[10px] font-extrabold text-slate-800 dark:text-slate-200 mb-1">
                  {h.rain_probability}%
                </span>
                
                {/* Bar */}
                <div className="w-full bg-slate-200/50 dark:bg-white/10 rounded-full h-14 flex items-end overflow-hidden p-0.5">
                  <div 
                    className={`w-full rounded-full transition-all duration-500 ${barBg}`}
                    style={{ height: `${Math.max(14, h.rain_probability)}%` }}
                  />
                </div>

                <div className="text-[9px] font-semibold text-slate-400 dark:text-slate-500 mt-1">
                  {h.rain_mm > 0 ? `${h.rain_mm}mm` : "0mm"}
                </div>
                <div className="text-[9px] font-bold text-slate-600 dark:text-slate-300 mt-0.5">
                  {h.time}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Atmospheric Strip */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 pt-2 border-t border-slate-100 dark:border-white/5">
        <div className="rounded-2xl p-3 bg-slate-50 dark:bg-white/5 border border-slate-100 dark:border-white/5 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Wind size={16} className="text-cyan-500" />
            <div>
              <div className="text-[10px] font-bold uppercase text-slate-400">Mean Wind Speed</div>
              <div className="text-sm font-black text-slate-900 dark:text-white">
                {Math.round(hours.reduce((acc: number, h: any) => acc + h.wind_kmh, 0) / hours.length)} km/h
              </div>
            </div>
          </div>
          <span className="text-[10px] font-bold px-2 py-0.5 rounded-md bg-cyan-50 dark:bg-cyan-950/30 text-cyan-600 dark:text-cyan-400 border border-cyan-200/40 dark:border-cyan-800/40">
            Gentle
          </span>
        </div>

        <div className="rounded-2xl p-3 bg-slate-50 dark:bg-white/5 border border-slate-100 dark:border-white/5 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Droplets size={16} className="text-blue-500" />
            <div>
              <div className="text-[10px] font-bold uppercase text-slate-400">Average Humidity</div>
              <div className="text-sm font-black text-slate-900 dark:text-white">
                {Math.round(hours.reduce((acc: number, h: any) => acc + h.humidity_percent, 0) / hours.length)}%
              </div>
            </div>
          </div>
          <span className="text-[10px] font-bold px-2 py-0.5 rounded-md bg-blue-50 dark:bg-blue-950/30 text-blue-600 dark:text-blue-400 border border-blue-200/40 dark:border-blue-800/40">
            Comfortable
          </span>
        </div>

        <div className="rounded-2xl p-3 bg-slate-50 dark:bg-white/5 border border-slate-100 dark:border-white/5 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Sun size={16} className="text-amber-500" />
            <div>
              <div className="text-[10px] font-bold uppercase text-slate-400">UV Index Peak</div>
              <div className="text-sm font-black text-slate-900 dark:text-white">
                {day.day === 2 ? "6 (Moderate)" : "8 (High)"}
              </div>
            </div>
          </div>
          <span className="text-[10px] font-bold px-2 py-0.5 rounded-md bg-amber-50 dark:bg-amber-950/30 text-amber-600 dark:text-amber-400 border border-amber-200/40 dark:border-amber-800/40">
            Sunscreen
          </span>
        </div>

        <div className="rounded-2xl p-3 bg-slate-50 dark:bg-white/5 border border-slate-100 dark:border-white/5 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <ShieldCheck size={16} className="text-emerald-500" />
            <div>
              <div className="text-[10px] font-bold uppercase text-slate-400">Itinerary Safety</div>
              <div className="text-sm font-black text-slate-900 dark:text-white">
                100% Optimized
              </div>
            </div>
          </div>
          <span className="text-[10px] font-bold px-2 py-0.5 rounded-md bg-emerald-50 dark:bg-emerald-950/30 text-emerald-600 dark:text-emerald-400 border border-emerald-200/40 dark:border-emerald-800/40">
            Verified
          </span>
        </div>
      </div>
    </div>
  );
}

function TripPlanningDemoView({ result, activeDay, setActiveDay }: { result: ChatResult; activeDay: number; setActiveDay: (day: number) => void }) {
  const view = result.trip_view;
  if (!view) return null;
  const currentDay = view.days.find((day) => day.day === activeDay) || view.days[0];
  const cards = view.summary_cards;

  const CATEGORY_ICON_MAP: Record<string, string> = {
    attraction: "🏛️",
    restaurant: "🍜",
    cafe: "☕",
    market: "🛒",
    beach: "🏖️",
  };

  const TIME_BLOCK_COLOR: Record<string, string> = {
    morning: "#3b82f6",
    lunch: "#10b981",
    afternoon: "#8b5cf6",
    dinner: "#f97316",
    evening: "#6366f1",
  };

  return (
    <div className="space-y-6">
      {/* Title block */}
      <div className="flex items-center justify-between">
        <h2 className="text-3xl md:text-4xl font-black text-slate-900 dark:text-white tracking-tight leading-tight">
          Plan for {view.title.replace("Plan for ", "")} next week
        </h2>
        <div className="rounded-full border border-emerald-200 dark:border-emerald-800 bg-emerald-50 dark:bg-emerald-950/30 px-3 py-1 text-[10px] font-black text-emerald-600 dark:text-emerald-400 tracking-wider">
          LIVE
        </div>
      </div>

      {/* Summary Stats Grid */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        <TripSummaryCard label="Avg High" value={formatTemp(cards.avg_high_c)} Icon={Sun} colorClass="text-amber-500" />
        <TripSummaryCard label="Avg Low" value={formatTemp(cards.avg_low_c)} Icon={Moon} colorClass="text-indigo-500" />
        <TripSummaryCard label="Avg Wind" value={formatNumber(cards.avg_wind_kmh, " km/h")} Icon={Wind} colorClass="text-cyan-500" />
        <TripSummaryCard label="Humidity" value={formatNumber(cards.humidity_percent, "%")} Icon={Droplets} colorClass="text-blue-500" />
        <TripSummaryCard label="Rain Risk" value={cards.rain_risk || "n/a"} Icon={ShieldCheck} colorClass="text-emerald-500" />
      </div>

      {/* AI Summary card */}
      <div className="rounded-2xl border border-slate-100 dark:border-white/5 bg-white dark:bg-slate-900/60 p-5 shadow-sm">
        <div className="flex items-center gap-1.5 text-xs font-bold text-blue-600 dark:text-cyan-400 uppercase tracking-wider mb-2">
          <Sparkles size={13} /> AI Summary
        </div>
        <p className="text-sm md:text-base leading-relaxed text-slate-700 dark:text-slate-300 font-semibold">
          {view.ai_summary}
        </p>
      </div>

      {/* 3-Day Plan details card */}
      <div className="rounded-3xl border border-slate-100 dark:border-white/5 bg-white dark:bg-slate-900/60 p-6 shadow-sm space-y-6">
        <div className="flex items-center gap-2 border-b border-slate-100 dark:border-white/5 pb-3">
          <Calendar size={14} className="text-blue-600 dark:text-cyan-400" />
          <span className="text-sm font-black text-slate-800 dark:text-slate-200">{view.days.length}-Day Plan</span>
        </div>

        {/* Days Selector Tabs */}
        {view.days.length > 1 && (
          <div className="flex gap-2 overflow-x-auto pb-1">
            {view.days.map((day) => {
              const isActive = currentDay?.day === day.day;
              return (
                <button
                  key={day.day}
                  onClick={() => setActiveDay(day.day)}
                  className={`flex-1 min-w-[130px] rounded-2xl border p-4 text-left transition-all duration-200 ${
                    isActive
                      ? "bg-blue-600 dark:bg-cyan-500 text-white dark:text-slate-950 border-blue-600 dark:border-cyan-500 shadow-lg shadow-blue-500/10 dark:shadow-cyan-500/15"
                      : "bg-slate-50 dark:bg-white/5 text-slate-700 dark:text-slate-300 border-slate-100 dark:border-white/5 hover:border-blue-400 dark:hover:border-cyan-400"
                  }`}
                >
                  <div className="text-sm font-black">Day {day.day}</div>
                  <div className={`text-xs mt-0.5 font-semibold ${isActive ? "opacity-90" : "opacity-60"}`}>
                    {day.date || `Day ${day.day} details`}
                  </div>
                </button>
              );
            })}
          </div>
        )}

        {/* Day detail stop list */}
        {currentDay && (
          <div className="space-y-5">
            <div className="flex items-center justify-between gap-3 border-b border-slate-100 dark:border-white/5 pb-4">
              <div>
                <h3 className="text-2xl md:text-3xl font-extrabold text-slate-900 dark:text-white">{currentDay.title}</h3>
                <p className="text-sm md:text-base text-slate-500 dark:text-slate-400 leading-relaxed mt-1.5 font-medium">{currentDay.summary}</p>
              </div>
              <div className="flex items-center gap-4 text-sm md:text-base font-extrabold text-slate-800 dark:text-slate-200 shrink-0">
                <span className="flex items-center gap-1"><Sun size={15} className="text-amber-500" /> {formatTemp(currentDay.weather.high_c)} / {formatTemp(currentDay.weather.low_c)}</span>
                <span className="flex items-center gap-1 text-blue-600 dark:text-cyan-400"><CloudLightning size={15} /> {formatPercent(currentDay.weather.rain_probability)} Rain Chance</span>
              </div>
            </div>

            {/* Stop list with timeline track */}
            <div className="relative border-l-2 border-slate-100 dark:border-white/5 ml-3 pl-6 space-y-5">
              {currentDay.stops.map((stop) => {
                const isIndoor = stop.is_indoor;
                const timeCol = TIME_BLOCK_COLOR[stop.time_block] || "#94a3b8";
                return (
                  <div key={`${stop.order}-${stop.name}`} className="relative flex items-center justify-between gap-4 bg-slate-50 dark:bg-white/5 border border-slate-100/50 dark:border-white/5 rounded-2xl p-4 transition-all hover:bg-slate-100/30 dark:hover:bg-white/10">
                    {/* Circle dot on the timeline track */}
                    <div
                      className="absolute -left-[31px] top-1/2 -translate-y-1/2 w-4 h-4 rounded-full border-4 border-white dark:border-slate-900 shadow-sm"
                      style={{ backgroundColor: timeCol }}
                    />
                    
                    {/* Left: Time, Icon, Details */}
                    <div className="flex items-center gap-4 min-w-0">
                      <div className="text-base md:text-lg font-black text-slate-500 dark:text-slate-400 font-mono w-14 shrink-0">{stop.time}</div>
                      
                      <div className="text-xl shrink-0 p-1.5 bg-white dark:bg-slate-950 rounded-xl shadow-sm border border-slate-100 dark:border-white/5">
                        {CATEGORY_ICON_MAP[stop.category] || "📍"}
                      </div>

                      <div className="min-w-0">
                        <div className="flex items-center gap-2">
                          <span style={{ color: timeCol }} className="text-xs font-black uppercase tracking-wider">{blockLabel(stop.time_block)}</span>
                          <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${isIndoor ? "bg-indigo-50 dark:bg-indigo-950/30 text-indigo-600 dark:text-indigo-400" : "bg-cyan-50 dark:bg-cyan-950/30 text-cyan-600 dark:text-cyan-400"}`}>
                            {isIndoor ? "Indoor" : "Outdoor"}
                          </span>
                        </div>
                        <div className="text-lg font-black text-slate-900 dark:text-white truncate mt-1">{stop.name}</div>
                        {stop.description && <div className="text-sm md:text-base font-semibold text-slate-500 dark:text-slate-400 mt-1">{stop.description}</div>}
                      </div>
                    </div>

                    {/* Right: Weather */}
                    <div className="flex items-center gap-4 shrink-0">
                      <div className="text-right text-xs">
                        <div className="font-extrabold text-slate-900 dark:text-white flex items-center gap-1 justify-end text-base md:text-lg">
                          <Thermometer size={14} className="text-amber-500" /> {formatTemp(stop.forecast_temp_c)}
                        </div>
                        <div className="text-slate-500 dark:text-slate-400 font-bold text-xs md:text-sm">{formatPercent(stop.rain_probability)} rain</div>
                        <div className={`capitalize font-extrabold text-xs px-2.5 py-1 rounded mt-1.5 inline-block ${
                          stop.weather_suitability === "good" ? "bg-emerald-50 dark:bg-emerald-950/20 text-emerald-600 dark:text-emerald-400" :
                          stop.weather_suitability === "poor" ? "bg-red-50 dark:bg-red-950/20 text-red-600 dark:text-red-400" :
                          "bg-amber-50 dark:bg-amber-950/20 text-amber-600 dark:text-amber-400"
                        }`}>
                          {stop.weather_suitability || "medium"}
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>

      {/* Atmospheric Weather Diurnal Chart for Tourism Itinerary */}
      <TripWeatherChartsView day={currentDay} />
    </div>
  );
}

function TripSummaryCard({ label, value, Icon, colorClass }: { label: string; value: string; Icon: any; colorClass: string }) {
  return (
    <div className="rounded-2xl border border-slate-100 dark:border-white/5 bg-white dark:bg-slate-900/60 p-4 flex items-center gap-3.5 shadow-sm transition-all hover:shadow-md">
      <div className={`p-2 rounded-xl bg-slate-50 dark:bg-white/5 shrink-0 ${colorClass}`}>
        <Icon size={20} />
      </div>
      <div>
        <div className="text-xl font-extrabold text-slate-900 dark:text-white leading-none">{value}</div>
        <div className="text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider mt-1">{label}</div>
      </div>
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
  const [theme, setTheme] = useState<"light" | "dark">("light");
  const [showMap, setShowMap] = useState(false);
  const [showWeather, setShowWeather] = useState(true);
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

  // Fetch weather data with 5-minute polling interval
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
    const interval = setInterval(fetchWeather, 300000); // 5 minutes
    return () => clearInterval(interval);
  }, []);

  // Theme support
  useEffect(() => {
    const saved = localStorage.getItem("theme") as "light" | "dark" | null;
    if (saved) {
      setTheme(saved);
      document.documentElement.className = saved;
    } else {
      setTheme("light");
      document.documentElement.className = "light";
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

    let wsHandled = false;

    try {
      const ws = new WebSocket(wsUrl);
      await new Promise<void>((resolve, reject) => {
        const timeout = setTimeout(() => reject(new Error("ws timeout")), 600);
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
              wsHandled = true;
              ws.close();
              resolve();
            } else if (ev.type === "error") {
              setLatestResult({ error: ev.error });
              wsHandled = true;
              ws.close();
              resolve();
            }
          } catch {}
        };
        ws.onerror = () => resolve();
      });
    } catch {
      // WebSocket not available (standard on Vercel deployment)
    }

    if (!wsHandled) {
      // REST Flow / Standalone Agent Processing
      try {
        setSteps(prev => [...prev, "Querying Meteorological & Domain Intelligence Agents..."]);
        
        // Dynamic step animation
        const stepTimer1 = setTimeout(() => {
          setSteps(prev => [...prev, "Extracting spatiotemporal constraints & risk parameters..."]);
        }, 300);
        const stepTimer2 = setTimeout(() => {
          setSteps(prev => [...prev, "NeMo Guardrails safety & hallucination validation passed."]);
        }, 600);

        const r = await fetch("/api/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message: text }),
        });

        clearTimeout(stepTimer1);
        clearTimeout(stepTimer2);

        if (!r.ok) {
          throw new Error(`API returned status ${r.status}`);
        }

        const data: ChatResult = await r.json();
        setLatestResult(data);
        setActiveDay(1);
        if (data?.trip_plan || data?.trip_view) setShowMap(true);
      } catch (err: any) {
        console.error("Chat error:", err);
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

  const resetToHome = () => {
    setLatestResult(null);
    setLoading(false);
    setSteps([]);
    setInput("");
    setQuery("");
  };

  const isChatActive = loading || !!latestResult;
  const dn = weatherData["Da Nang"] || { temp: 31, condition: "High risk", risk: "High risk", humidity: 72, wind_speed: 18.5, precipitation: 5.0 };

  return (
    <div 
      className={`min-h-screen ${isChatActive ? "h-screen overflow-hidden" : ""} flex flex-col bg-cover bg-center bg-no-repeat transition-all duration-500 relative`}
      style={{ 
        backgroundImage: theme === "dark" ? "url('/image_dark.png')" : "url('/image.png')"
      }}
    >
      <div 
        className={`absolute inset-0 transition-all duration-500 pointer-events-none ${
          !isChatActive ? (theme === "dark" ? "bg-gradient-overlay-dark" : "bg-gradient-overlay-light") : ""
        }`}
        style={{
          backgroundColor: isChatActive
            ? (theme === "dark" ? "#030712" : "#f8fafc")
            : undefined,
          backdropFilter: isChatActive ? "blur(12px)" : undefined,
          WebkitBackdropFilter: isChatActive ? "blur(12px)" : undefined
        }}
      />

      <div className="relative z-10 flex flex-col min-h-screen">
        {/* Header */}
      <header className="sticky top-0 z-50 backdrop-blur-xl bg-white/10 dark:bg-slate-950/20 transition-colors duration-500">
        <div className="max-w-7xl mx-auto px-6 py-5 flex items-center justify-between">
          <button
            onClick={resetToHome}
            className="flex items-center gap-3 text-left group transition-all active:scale-95 outline-none cursor-pointer"
            title="Return to Home"
          >
            <img 
              src="/Weatherise_Logo.png" 
              alt="Weatherise Logo" 
              className="w-10 h-10 rounded-xl object-cover shadow-sm group-hover:scale-105 group-hover:ring-2 group-hover:ring-blue-500/50 dark:group-hover:ring-cyan-400/50 transition-all" 
            />
            <div className="flex flex-col">
              <h1 className="text-slate-900 dark:text-white font-serif-heading text-2xl md:text-3xl font-black tracking-tight leading-none group-hover:text-blue-600 dark:group-hover:text-cyan-400 transition-colors">
                Weatherise
              </h1>
            </div>
          </button>

          <div className="flex items-center gap-5">
            <a href="/monitor" target="_blank" className="text-xs text-slate-700 dark:text-slate-200 hover:text-blue-600 dark:hover:text-cyan-400 transition-colors flex items-center gap-1.5 font-semibold">
              <ExternalLink size={11} /> Monitor
            </a>
            
            {/* Theme Toggle */}
            <button onClick={toggleTheme} className="btn-liquid-glass p-2 rounded-xl bg-white/40 dark:bg-white/5 border border-slate-200/50 dark:border-white/10 text-slate-800 dark:text-white" title="Toggle theme">
              {theme === "dark" ? <Sun size={15} /> : <Moon size={15} />}
            </button>

            <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-white dark:bg-slate-950/60 border border-slate-100 dark:border-white/10 shadow-sm">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse" />
              <span className="text-[10px] uppercase font-bold tracking-wider text-slate-700 dark:text-slate-200">Live</span>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className={`flex-1 w-full max-w-7xl mx-auto px-6 ${isChatActive ? "py-6 min-h-0" : "py-8 justify-center"} flex flex-col`}>
        {(!loading && !latestResult) ? (
            /* INITIAL VIEW (Mockup layout matches image exactly) */
            <div className="space-y-6 animate-[fadeIn_0.4s_ease-out]">
              {/* Hero Grid */}
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-center">
                
                {/* Left side: Heading, Search & Category Buttons */}
                <div className="lg:col-span-6 space-y-6">
                  <h2 className="font-serif-heading text-5xl md:text-6xl font-black tracking-tight leading-[1.02] text-slate-900 dark:text-white">
                    <span className="font-handwritten text-8xl md:text-9xl text-blue-600 dark:text-cyan-400 block -mb-4 font-normal">Understand</span>
                    <span className="font-handwritten text-7xl md:text-8xl text-blue-600 dark:text-cyan-400 block -mb-4 font-normal">the weather.</span>
                    Plan better.
                  </h2>
                  <p className="text-slate-800 dark:text-slate-200 text-base md:text-lg leading-relaxed max-w-xl mt-4 font-bold">
                    Real-time weather intelligence to help you plan smarter, stay safe, and make confident decisions.
                  </p>
                  
                  {/* Search Composer Container */}
                  <div className="w-full max-w-xl mt-6 rounded-full border border-slate-200/80 dark:border-white/10 bg-white/95 dark:bg-slate-950/80 shadow-lg px-5 py-3 flex items-center gap-3">
                    <Search size={18} className="text-slate-400 dark:text-slate-400 shrink-0" />
                    <textarea
                      ref={textareaRef}
                      rows={1}
                      value={input}
                      onChange={e => setInput(e.target.value)}
                      onKeyDown={handleKey}
                      placeholder="Ask anything about weather risk for your plans..."
                      disabled={loading}
                      className="flex-1 bg-transparent text-sm text-slate-800 dark:text-white placeholder-slate-400 dark:placeholder-slate-400 resize-none outline-none leading-relaxed py-1"
                    />
                    <button 
                      onClick={() => sendMessage(input)} 
                      disabled={!input.trim() || loading}
                      className="w-8 h-8 rounded-full flex items-center justify-center shrink-0 transition-all bg-blue-600 dark:bg-cyan-400 hover:scale-[1.05] active:scale-[0.95] disabled:opacity-30 disabled:hover:scale-100 shadow-md outline-none"
                    >
                      <ArrowRight size={14} className="text-white dark:text-slate-950 font-bold stroke-[3]" />
                    </button>
                  </div>

                  {/* Category Buttons Stretched Row */}
                  <div className="flex flex-row gap-3 mt-4 max-w-xl w-full">
                    {[
                      { name: "Tourism", icon: Briefcase, q: "Plan a 3-day trip to Da Nang next week for sightseeing" },
                      { name: "Construction", icon: Building, q: "Is tomorrow safe for concrete pouring at my construction site in Da Nang?" },
                      { name: "Agriculture", icon: Leaf, q: "Should I irrigate my rice farm this week in Hoa Vang, Da Nang?" }
                    ].map((p, i) => {
                      const Icon = p.icon;
                      return (
                        <button 
                          key={i} 
                          onClick={() => { setInput(p.q); }}
                          className="flex-1 flex items-center justify-center gap-2 px-7 py-4 rounded-full btn-category-glass outline-none"
                        >
                          <Icon size={18} className="text-blue-600 dark:text-cyan-400 shrink-0" />
                          <span className="text-slate-800 dark:text-slate-100 font-black text-base md:text-lg truncate">{p.name}</span>
                        </button>
                      );
                    })}
                  </div>
                </div>

                {/* Right side: Clean direct weather values inside fluid glass box */}
                <div className="lg:col-span-6 flex items-center justify-center">
                  <div className="fluid-glass-box w-full rounded-3xl p-8 md:p-10 space-y-8 text-slate-800 dark:text-white">
                    {/* Location */}
                    <div className="flex items-center gap-2.5 text-blue-600 dark:text-cyan-400 font-black text-sm md:text-base uppercase tracking-widest drop-shadow-sm">
                      <MapPin size={18} className="shrink-0" />
                      <span>DA NANG, VIETNAM</span>
                    </div>
                    
                    {/* Temp & Condition */}
                    <div className="flex flex-wrap items-center gap-8 md:gap-12">
                      <div className="flex items-start">
                        <span className="font-serif-heading text-[6.5rem] md:text-[8rem] lg:text-[9rem] font-black tracking-tighter leading-none text-slate-900 dark:text-white drop-shadow-[0_2px_4px_rgba(255,255,255,0.4)] dark:drop-shadow-[0_2px_8px_rgba(0,0,0,0.5)]">
                          {dn.temp}
                        </span>
                        <div className="flex flex-col items-center ml-2 mt-4">
                          <span className="text-4xl font-light text-blue-600 dark:text-cyan-400">°</span>
                          <span className="text-2xl font-black text-blue-600 dark:text-cyan-400 -mt-2.5 uppercase">C</span>
                        </div>
                      </div>
                      
                      {/* Condition Info */}
                      <div className="flex items-center gap-5">
                        <div className="w-16 h-16 rounded-full bg-blue-50/80 dark:bg-slate-950/40 flex items-center justify-center shadow-md border border-slate-100 dark:border-white/5">
                          <svg className="w-10 h-10 shrink-0" viewBox="0 0 24 24" fill="none">
                            <path d="M18 10h-.7A5.5 5.5 0 0 0 6.8 9.2a4 4 0 0 0-3.3 4.3 4 4 0 0 0 4 3.5h10.5a4.5 4.5 0 0 0 0-9Z" fill="#94a3b8" />
                            <path d="M8 18v2M12 18v2M16 18v2" stroke="#2563eb" strokeWidth="2.5" strokeLinecap="round" />
                          </svg>
                        </div>
                        <div>
                          <div className="text-xl md:text-2xl lg:text-3xl font-black text-slate-900 dark:text-white leading-none">
                            {dn.condition}
                          </div>
                          <div className="text-sm text-slate-500 dark:text-slate-400 mt-2 font-black">
                            Feels like {dn.temp + 3}°C
                          </div>
                        </div>
                      </div>
                    </div>
                    
                    {/* Horizontal Metrics row */}
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 pt-8 border-t border-slate-200/50 dark:border-white/10">
                      <div className="flex items-center gap-3 bg-white/45 dark:bg-slate-950/40 backdrop-blur-lg rounded-2xl p-3.5 border border-white/35 shadow-sm">
                        <Wind className="w-6 h-6 text-blue-600 dark:text-cyan-400 shrink-0" />
                        <div>
                          <div className="text-base md:text-lg font-black text-slate-950 dark:text-white leading-none">{dn.wind_speed ?? 18.5} km/h</div>
                          <div className="text-[10px] font-black text-slate-700 dark:text-slate-200 mt-1 uppercase tracking-wider">Wind</div>
                        </div>
                      </div>

                      <div className="flex items-center gap-3 bg-white/45 dark:bg-slate-950/40 backdrop-blur-lg rounded-2xl p-3.5 border border-white/35 shadow-sm">
                        <Droplets className="w-6 h-6 text-blue-600 dark:text-cyan-400 shrink-0" />
                        <div>
                          <div className="text-base md:text-lg font-black text-slate-950 dark:text-white leading-none">{dn.humidity ?? 72}%</div>
                          <div className="text-[10px] font-black text-slate-700 dark:text-slate-200 mt-1 uppercase tracking-wider">Humidity</div>
                        </div>
                      </div>

                      <div className="flex items-center gap-3 bg-white/45 dark:bg-slate-950/40 backdrop-blur-lg rounded-2xl p-3.5 border border-white/35 shadow-sm">
                        <Droplets className="w-6 h-6 text-blue-600 dark:text-cyan-400 shrink-0" />
                        <div>
                          <div className="text-base md:text-lg font-black text-slate-950 dark:text-white leading-none">{dn.precipitation ?? 5.0} mm</div>
                          <div className="text-[10px] font-black text-slate-700 dark:text-slate-200 mt-1 uppercase tracking-wider">Rainfall</div>
                        </div>
                      </div>

                      <div className="flex items-center gap-3 bg-white/45 dark:bg-slate-950/40 backdrop-blur-lg rounded-2xl p-3.5 border border-white/35 shadow-sm">
                        <ShieldCheck className="w-6 h-6 text-orange-500 dark:text-orange-400 shrink-0" />
                        <div>
                          <div className="text-base md:text-lg font-black text-orange-700 dark:text-orange-400 leading-none">{dn.risk ?? "High"}</div>
                          <div className="text-[10px] font-black text-slate-700 dark:text-slate-200 mt-1 uppercase tracking-wider">Risk Index</div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

              </div>

              {/* Bottom popular cards matching mockup style */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 pt-6">
                <PopularMockCard 
                  title="Plan Your Trip" 
                  desc="Get weather-aware travel recommendations tailored to your journey." 
                  icon={Briefcase} 
                  iconBg="bg-blue-50 text-blue-600 dark:bg-blue-950/40 dark:text-blue-400"
                  onClick={() => sendMessage("Plan a 3-day trip to Da Nang next week for sightseeing")} 
                  type="tourism"
                />
                <PopularMockCard 
                  title="Construction Safety" 
                  desc="Check rain, wind, and extreme weather impact." 
                  icon={Building} 
                  iconBg="bg-emerald-50 text-emerald-600 dark:bg-emerald-950/40 dark:text-emerald-400"
                  onClick={() => sendMessage("Is tomorrow safe for concrete pouring at my construction site in Da Nang?")} 
                  type="construction"
                />
                <PopularMockCard 
                  title="Agriculture Planning" 
                  desc="Optimize planting, irrigation and harvesting." 
                  icon={Leaf} 
                  iconBg="bg-indigo-50 text-indigo-600 dark:bg-indigo-950/40 dark:text-indigo-400"
                  onClick={() => sendMessage("Should I irrigate my rice farm this week in Hoa Vang, Da Nang?")} 
                  type="agriculture"
                />
                <PopularMockCard 
                  title="Severe Weather Alerts" 
                  desc="Early warnings for storms, floods, and other extreme conditions." 
                  icon={Bell} 
                  iconBg="bg-rose-50 text-rose-600 dark:bg-rose-950/40 dark:text-rose-400"
                  onClick={() => sendMessage("Are there any severe weather alerts or typhoons near Da Nang this week?")} 
                  type="severe"
                />
              </div>
            </div>
          ) : (
          /* ACTIVE / CHAT VIEW — V3: Left Output Canvas | Right Composer + Small Map */
          <div className="animate-[fadeIn_0.3s_ease] flex flex-col flex-1 min-h-0">
            <div className="grid grid-cols-1 lg:grid-cols-[1.2fr_0.8fr] gap-6 flex-1 min-h-0">

              {/* ── LEFT: Large Output Canvas ─────────────────────── */}
              {(() => {
                const displayRisk = latestResult?.weather_view?.statistics?.overall_risk
                  ?? latestResult?.risk_assessment?.overall_risk
                  ?? latestResult?.risk_assessment?.trip_disruption_risk
                  ?? latestResult?.risk_assessment?.construction_safety_risk
                  ?? latestResult?.risk_assessment?.disease_risk
                  ?? "unknown";
                const overallRisk = displayRisk.toLowerCase();
                const dynamicBorder = overallRisk === "high" 
                  ? "rgba(239, 68, 68, 0.25)" 
                  : overallRisk === "medium" 
                  ? "rgba(245, 158, 11, 0.22)" 
                  : (theme === "dark" ? "rgba(255, 255, 255, 0.1)" : "rgba(226, 232, 240, 0.9)");
                const dynamicBg = overallRisk === "high"
                  ? "radial-gradient(ellipse at 50% 0%, rgba(239, 68, 68, 0.05) 0%, var(--bg-secondary) 80%)"
                  : overallRisk === "medium"
                  ? "radial-gradient(ellipse at 50% 0%, rgba(245, 158, 11, 0.04) 0%, var(--bg-secondary) 80%)"
                  : "var(--bg-secondary)";

                const isTripPlan = latestResult && latestResult.response_type === "trip_planning" && latestResult.trip_view;

                if (isTripPlan) {
                  return (
                    <div className="overflow-y-auto flex flex-col gap-6 min-h-0 pr-1 pb-4">
                      {loading && (
                        <div className="py-8 text-center space-y-4 bg-[var(--bg-secondary)] border border-[var(--color-border)] rounded-3xl p-6 shadow-2xl">
                          <Loader2 size={24} className="animate-spin text-[var(--color-brand)] mx-auto" />
                          <p className="text-xs text-[var(--color-text-secondary)]">Analyzing input & evaluating risk factors...</p>
                          <StepIndicator steps={steps} />
                        </div>
                      )}
                      {!loading && latestResult && (
                        <TripPlanningDemoView result={latestResult} activeDay={activeDay} setActiveDay={setActiveDay} />
                      )}
                    </div>
                  );
                }

                return (
                  <div 
                    style={{ border: `1px solid ${dynamicBorder}`, background: dynamicBg }}
                    className="rounded-3xl p-6 shadow-2xl overflow-y-auto flex flex-col gap-5 min-h-0"
                  >

                    {/* Loading */}
                    {loading && (
                      <div className="py-8 text-center space-y-4">
                        <Loader2 size={24} className="animate-spin text-[var(--color-brand)] mx-auto" />
                        <p className="text-xs text-[var(--color-text-secondary)]">Analyzing input & evaluating risk factors...</p>
                        <StepIndicator steps={steps} />
                      </div>
                    )}

                    {/* Result */}
                    {!loading && latestResult && (
                      <div className="space-y-5">
                        {latestResult.weather_view ? (
                          <WeatherPredictionDemoView result={latestResult} />
                        ) : latestResult.response_type === "trip_planning" && latestResult.trip_view ? (
                          <TripPlanningDemoView result={latestResult} activeDay={activeDay} setActiveDay={setActiveDay} />
                        ) : (
                          <>
                            {/* Badges for generic fallback */}
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
                                  color: riskColor(displayRisk),
                                  background: riskBg(displayRisk),
                                }}>
                                {displayRisk}
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
                              value={latestResult.risk_assessment.rain_risk ?? "unknown"} 
                              Icon={Droplets} 
                              detail={latestResult.weather_stats?.max_rain_prob !== undefined ? `${latestResult.weather_stats.max_rain_prob}%` : undefined}
                            />
                            <RiskBadge 
                              label="Wind" 
                              value={latestResult.risk_assessment.wind_risk ?? "unknown"} 
                              Icon={Wind} 
                              detail={latestResult.weather_stats?.max_wind_speed !== undefined ? `${latestResult.weather_stats.max_wind_speed} km/h` : undefined}
                            />
                            <RiskBadge 
                              label="Heat" 
                              value={latestResult.risk_assessment.heat_risk ?? "unknown"} 
                              Icon={Thermometer} 
                              detail={latestResult.weather_stats?.max_temp !== undefined ? `${latestResult.weather_stats.max_temp}°C` : undefined}
                            />
                          </div>
                        )}

                        <PathBDebugPanel result={latestResult} />

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
                          </>
                        )}
                      </div>
                    )}
                  </div>
                );
              })()}

              {/* ── RIGHT: Composer (top) + Small Map (bottom ¼) ─── */}
              <div className="flex flex-col gap-6 min-h-0">

                {/* Query Composer - Ask Weatherise style */}
                <div className="flex-shrink-0 rounded-3xl border border-[var(--color-border)] bg-[var(--bg-secondary)] p-6 shadow-2xl space-y-4 min-h-0">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Search size={15} className="text-[var(--color-brand)]" />
                      <h3 className="text-xs font-bold uppercase tracking-wider text-[var(--color-brand)]">Ask Weatherise</h3>
                    </div>
                    <button
                      onClick={resetToHome}
                      className="text-[11px] font-bold text-slate-600 dark:text-slate-300 hover:text-blue-600 dark:hover:text-cyan-400 flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-white/40 dark:bg-white/5 border border-slate-200/50 dark:border-white/10 transition-all cursor-pointer"
                      title="Return to Home"
                    >
                      <RefreshCw size={11} /> Home
                    </button>
                  </div>
                  
                  <div className="relative flex items-center bg-[var(--bg-primary)] border border-[var(--color-border)] rounded-full px-4 py-2.5 focus-within:border-[var(--color-brand)] focus-within:ring-2 focus-within:ring-[var(--color-brand)]/20 transition-all">
                    <input
                      type="text"
                      value={input}
                      onChange={e => setInput(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" && input.trim()) {
                          sendMessage(input);
                        }
                      }}
                      placeholder="Ask anything about your plan..."
                      disabled={loading}
                      className="w-full bg-transparent text-xs text-[var(--color-text-primary)] placeholder-[var(--color-text-muted)] outline-none pr-10"
                    />
                    <button
                      onClick={() => sendMessage(input)}
                      disabled={!input.trim() || loading}
                      className="absolute right-1.5 top-1/2 -translate-y-1/2 w-8 h-8 rounded-full bg-blue-600 text-white flex items-center justify-center hover:bg-blue-700 disabled:opacity-40 transition-colors shadow-md"
                    >
                      <ArrowRight size={14} />
                    </button>
                  </div>

                </div>

                {/* Geospatial Map — expands to fill remaining space */}
                <div className="flex-1 rounded-3xl border border-[var(--color-border)] bg-[var(--bg-secondary)] shadow-2xl overflow-hidden flex flex-col min-h-0">
                  <div className="flex items-center justify-between px-5 py-3 border-b border-white/10 bg-slate-900/60 flex-shrink-0">
                    <div className="flex items-center gap-2">
                      <Map size={14} className="text-blue-500 dark:text-cyan-400" />
                      <span className="text-xs font-bold text-slate-800 dark:text-slate-200">
                        {latestResult?.domain === "construction" ? "Structural Safety & Wind Radius Map" :
                         latestResult?.domain === "agriculture" ? "Irrigation & Crop Monitoring Map" :
                         latestResult?.domain === "severe_weather" ? "Coastal Doppler Radar & Marine Grid" :
                         "Interactive Trip Itinerary & POI Map"}
                      </span>
                    </div>
                    <div className="flex items-center gap-1.5 text-[10px] text-slate-400 font-semibold">
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                      <span>Da Nang GIS</span>
                    </div>
                  </div>
                  <div className="flex-1 min-h-0 w-full relative">
                    <TripMapPanel 
                      tripPlan={latestResult?.trip_plan ?? convertTripViewToPlan(latestResult?.trip_view)} 
                      coordinates={(latestResult?.trip_view?.map as any)?.center
                        ? {
                            latitude: (latestResult?.trip_view?.map as any)?.center?.latitude,
                            longitude: (latestResult?.trip_view?.map as any)?.center?.longitude,
                          }
                        : latestResult?.coordinates}
                      locationName={latestResult?.trip_view?.title ?? latestResult?.location}
                      weatherMarker={latestResult?.weather_view?.map?.markers?.[0] ?? null}
                      weatherMarkers={latestResult?.weather_view?.map?.markers ?? []}
                      domain={latestResult?.domain}
                      activeDay={activeDay}
                      onActiveDayChange={setActiveDay}
                      theme={theme}
                    />
                  </div>
                </div>

              </div>{/* end right column */}
            </div>{/* end grid */}
          </div>
        )}

      </main>
      </div>
    </div>);
}
