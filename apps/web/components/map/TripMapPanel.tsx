"use client";

import { useEffect, useState } from "react";
import { MapContainer, TileLayer, Marker, Popup, Polyline, Tooltip } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import "leaflet-defaulticon-compatibility/dist/leaflet-defaulticon-compatibility.css";
import "leaflet-defaulticon-compatibility";

// ── Types ──────────────────────────────────────────────────────
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
}

interface TripPlan {
  duration_days: number;
  location: string;
  days: TripDay[];
  weather_aware: boolean;
  planning_mode: string;
}

interface Props {
  tripPlan: TripPlan;
}

// ── Time block colors ──────────────────────────────────────────
const TIME_BLOCK_COLOR: Record<string, string> = {
  morning: "#22d3ee",
  lunch: "#f59e0b",
  afternoon: "#818cf8",
  dinner: "#f97316",
  evening: "#a78bfa",
};

const CATEGORY_ICON_MAP: Record<string, string> = {
  attraction: "🏛️",
  restaurant: "🍜",
  cafe: "☕",
  market: "🛒",
  beach: "🏖️",
};

// ── Custom numbered marker ─────────────────────────────────────
function createNumberedIcon(order: number, color: string, isIndoor: boolean) {
  const html = `
    <div style="
      width:36px; height:36px; border-radius:50%;
      background:${color}; border:3px solid rgba(255,255,255,0.9);
      display:flex; align-items:center; justify-content:center;
      font-weight:800; font-size:13px; color:#0f172a;
      box-shadow:0 4px 14px rgba(0,0,0,0.5);
      position:relative;
    ">
      ${order}
      ${isIndoor ? '<span style="position:absolute;top:-4px;right:-4px;font-size:9px">🏠</span>' : ""}
    </div>
  `;
  return L.divIcon({ html, className: "", iconSize: [36, 36], iconAnchor: [18, 18] });
}

// ── Main Map Panel ─────────────────────────────────────────────
export default function TripMapPanel({ tripPlan }: Props) {
  const [activeDay, setActiveDay] = useState(1);

  const currentDay = tripPlan.days.find((d) => d.day === activeDay) || tripPlan.days[0];
  const stops = currentDay?.stops || [];

  // Map center: average of all stops
  const centerLat = stops.length
    ? stops.reduce((s, p) => s + p.lat, 0) / stops.length
    : 16.054;
  const centerLon = stops.length
    ? stops.reduce((s, p) => s + p.lon, 0) / stops.length
    : 108.202;

  // Polyline coords
  const polyline: [number, number][] = stops.map((s) => [s.lat, s.lon]);

  return (
    <div className="flex flex-col h-full">
      {/* ── Day Selector ──────────────────────────────────────── */}
      <div className="flex items-center gap-2 px-4 py-3 border-b border-white/10 flex-shrink-0">
        <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400 mr-2">
          Lịch trình
        </span>
        <div className="flex gap-1.5">
          {tripPlan.days.map((d) => (
            <button
              key={d.day}
              onClick={() => setActiveDay(d.day)}
              className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-all duration-200 ${
                activeDay === d.day
                  ? "bg-cyan-500 text-slate-900 shadow-lg shadow-cyan-500/30"
                  : "bg-white/5 text-slate-400 hover:bg-white/10 hover:text-white"
              }`}
            >
              Ngày {d.day}
            </button>
          ))}
        </div>
        {currentDay?.theme && (
          <span className="ml-auto text-[10px] text-cyan-400 italic">
            {currentDay.theme}
          </span>
        )}
      </div>

      {/* ── Map ───────────────────────────────────────────────── */}
      <div className="flex-1 min-h-0 relative">
        <MapContainer
          key={`map-day-${activeDay}`}
          center={[centerLat, centerLon]}
          zoom={13}
          style={{ height: "100%", width: "100%", background: "#0f172a" }}
          className="rounded-none"
        >
          <TileLayer
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            attribution='&copy; <a href="https://openstreetmap.org">OpenStreetMap</a>'
          />

          {/* Route polyline */}
          {polyline.length > 1 && (
            <Polyline
              positions={polyline}
              pathOptions={{
                color: "#22d3ee",
                weight: 2.5,
                opacity: 0.7,
                dashArray: "6, 8",
              }}
            />
          )}

          {/* Markers */}
          {stops.map((stop) => {
            const color = TIME_BLOCK_COLOR[stop.time_block] || "#94a3b8";
            return (
              <Marker
                key={stop.place_id}
                position={[stop.lat, stop.lon]}
                icon={createNumberedIcon(stop.order, color, stop.is_indoor)}
              >
                {/* Tooltip always visible */}
                <Tooltip
                  permanent
                  direction="top"
                  offset={[0, -22]}
                  className="leaflet-tooltip-custom"
                >
                  <div
                    style={{
                      background: "rgba(15,23,42,0.92)",
                      border: `1px solid ${color}40`,
                      borderRadius: "8px",
                      padding: "4px 8px",
                      fontSize: "10px",
                      color: "#f1f5f9",
                      backdropFilter: "blur(8px)",
                      whiteSpace: "nowrap",
                    }}
                  >
                    <div style={{ fontWeight: 700, color: color }}>{stop.name}</div>
                    <div style={{ color: "#94a3b8", fontSize: "9px" }}>
                      {stop.planned_time}
                      {stop.forecast_temp != null && (
                        <span style={{ color: "#fbbf24", marginLeft: 4 }}>
                          🌡 {stop.forecast_temp}°C
                        </span>
                      )}
                    </div>
                  </div>
                </Tooltip>

                {/* Popup on click */}
                <Popup className="leaflet-popup-custom">
                  <div
                    style={{
                      background: "#0f172a",
                      color: "#f1f5f9",
                      padding: "12px",
                      borderRadius: "12px",
                      minWidth: "200px",
                      border: `1px solid ${color}40`,
                    }}
                  >
                    <div style={{ display: "flex", alignItems: "center", gap: "6px", marginBottom: "8px" }}>
                      <span style={{ fontSize: "18px" }}>
                        {CATEGORY_ICON_MAP[stop.category] || "📍"}
                      </span>
                      <div>
                        <div style={{ fontWeight: 800, fontSize: "13px", color }}>{stop.name}</div>
                        <div style={{ fontSize: "10px", color: "#64748b" }}>
                          {stop.is_indoor ? "🏠 Indoor" : "🌤 Outdoor"}
                        </div>
                      </div>
                    </div>

                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "6px" }}>
                      <div style={{ fontSize: "10px", color: "#94a3b8" }}>
                        <div>🕐 {stop.planned_time}</div>
                        <div>⏱ {stop.duration_minutes} phút</div>
                      </div>
                      {stop.forecast_temp != null && (
                        <div style={{ fontSize: "10px", color: "#94a3b8" }}>
                          <div style={{ color: "#fbbf24" }}>🌡 {stop.forecast_temp}°C</div>
                          <div>{stop.weather_condition}</div>
                        </div>
                      )}
                    </div>

                    {stop.vibe_tags.length > 0 && (
                      <div style={{ display: "flex", flexWrap: "wrap", gap: "4px", marginTop: "8px" }}>
                        {stop.vibe_tags.slice(0, 3).map((tag) => (
                          <span
                            key={tag}
                            style={{
                              background: `${color}20`,
                              color,
                              border: `1px solid ${color}40`,
                              borderRadius: "20px",
                              padding: "2px 8px",
                              fontSize: "9px",
                              fontWeight: 700,
                            }}
                          >
                            {tag}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </Popup>
              </Marker>
            );
          })}
        </MapContainer>
      </div>

      {/* ── Stop List ─────────────────────────────────────────── */}
      <div
        style={{ maxHeight: "160px" }}
        className="flex-shrink-0 overflow-y-auto border-t border-white/10 p-3 space-y-1.5"
      >
        {stops.length === 0 ? (
          <div className="text-xs text-slate-500 text-center py-4">
            Chưa có lịch trình cho ngày này.
          </div>
        ) : (
          stops.map((stop) => {
            const color = TIME_BLOCK_COLOR[stop.time_block] || "#94a3b8";
            return (
              <div
                key={stop.place_id}
                className="flex items-center gap-3 px-3 py-2 rounded-xl hover:bg-white/5 transition-colors"
              >
                {/* Order badge */}
                <div
                  className="w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-black flex-shrink-0"
                  style={{ background: color, color: "#0f172a" }}
                >
                  {stop.order}
                </div>
                {/* Name + time */}
                <div className="flex-1 min-w-0">
                  <div className="text-xs font-bold text-slate-200 truncate">{stop.name}</div>
                  <div className="text-[10px] text-slate-500">
                    {stop.planned_time} · {stop.duration_minutes}p
                    {stop.forecast_temp != null && (
                      <span className="text-amber-400 ml-2">🌡 {stop.forecast_temp}°C</span>
                    )}
                  </div>
                </div>
                {/* Indoor/outdoor badge */}
                <div
                  className="text-[9px] px-2 py-0.5 rounded-full font-bold flex-shrink-0"
                  style={{
                    background: stop.is_indoor ? "rgba(99,102,241,0.15)" : "rgba(34,211,238,0.15)",
                    color: stop.is_indoor ? "#818cf8" : "#22d3ee",
                  }}
                >
                  {stop.is_indoor ? "Indoor" : "Outdoor"}
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
