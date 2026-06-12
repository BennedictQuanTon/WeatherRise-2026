"use client";

import { useEffect, useState } from "react";
import { MapContainer, TileLayer, Marker, Popup, Polyline, Tooltip, useMap } from "react-leaflet";
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

interface WeatherMarker {
  label: string;
  latitude: number;
  longitude: number;
  title?: string;
  description?: string;
  temperature_c?: number;
  weather_condition?: string;
  rain_probability?: number;
}

interface Props {
  tripPlan?: TripPlan | null;
  coordinates?: { latitude: number; longitude: number } | null;
  locationName?: string | null;
  weatherMarker?: WeatherMarker | null;
  activeDay?: number;
  onActiveDayChange?: (day: number) => void;
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
// ── Fit Map Bounds Component ───────────────────────────────────
function FitBoundsComponent({ coords }: { coords: [number, number][] }) {
  const map = useMap();
  const coordsStr = JSON.stringify(coords);
  useEffect(() => {
    if (coords && coords.length > 0) {
      const bounds = L.latLngBounds(coords);
      map.fitBounds(bounds, { padding: [30, 30] });
    }
  }, [coordsStr, map]);
  return null;
}

// ── Main Map Panel ─────────────────────────────────────────────
export default function TripMapPanel({ 
  tripPlan, 
  coordinates, 
  locationName,
  weatherMarker,
  activeDay = 1,
  onActiveDayChange,
}: Props) {
  const hasTripPlan = !!(tripPlan && tripPlan.days && tripPlan.days.length);
  const currentDay = hasTripPlan ? (tripPlan.days.find((d) => d.day === activeDay) || tripPlan.days[0]) : null;
  const stops = currentDay?.stops || [];

  // Map center: average of all stops or single coordinate or default Da Nang
  let centerLat = 16.0544;
  let centerLon = 108.2022;

  if (hasTripPlan && stops.length) {
    centerLat = stops.reduce((s, p) => s + p.lat, 0) / stops.length;
    centerLon = stops.reduce((s, p) => s + p.lon, 0) / stops.length;
  } else if (weatherMarker) {
    centerLat = weatherMarker.latitude;
    centerLon = weatherMarker.longitude;
  } else if (coordinates && coordinates.latitude && coordinates.longitude) {
    centerLat = coordinates.latitude;
    centerLon = coordinates.longitude;
  }

  // Polyline coords
  const polyline: [number, number][] = stops.map((s) => [s.lat, s.lon]);

  return (
    <div className="flex flex-col h-full w-full">
      {/* ── Map ───────────────────────────────────────────────── */}
      <div className="flex-1 min-h-0 relative w-full h-full">
        <MapContainer
          key="weatherise-leaflet-map"
          center={[centerLat, centerLon]}
          zoom={13}
          style={{ height: "100%", width: "100%", background: "#0f172a" }}
          className="rounded-none"
        >
          <TileLayer
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            attribution='&copy; <a href="https://openstreetmap.org">OpenStreetMap</a>'
          />

          {/* Fit Bounds Component */}
          {hasTripPlan && polyline.length > 0 && (
            <FitBoundsComponent coords={polyline} />
          )}
          {!hasTripPlan && weatherMarker && (
            <FitBoundsComponent coords={[[weatherMarker.latitude, weatherMarker.longitude]]} />
          )}
          {!hasTripPlan && !weatherMarker && coordinates && coordinates.latitude && coordinates.longitude && (
            <FitBoundsComponent coords={[[coordinates.latitude, coordinates.longitude]]} />
          )}

          {/* Route polyline */}
          {hasTripPlan && polyline.length > 1 && (
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
          {hasTripPlan ? (
            stops.map((stop) => {
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
                      <div style={{ color: "#fbbf24", fontSize: "10px", fontWeight: 800 }}>
                        {stop.forecast_temp != null ? `🌡 ${stop.forecast_temp}°C` : ""}
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
                          <div>⏱ {stop.duration_minutes} min</div>
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
            })
          ) : weatherMarker ? (
            <Marker position={[weatherMarker.latitude, weatherMarker.longitude]}>
              <Tooltip
                permanent
                direction="top"
                offset={[0, -10]}
                className="leaflet-tooltip-custom"
              >
                <div
                  style={{
                    background: "rgba(15,23,42,0.92)",
                    border: "1px solid rgba(34,211,238,0.4)",
                    borderRadius: "8px",
                    padding: "4px 8px",
                    fontSize: "10px",
                    color: "#f1f5f9",
                    backdropFilter: "blur(8px)",
                    whiteSpace: "nowrap",
                  }}
                >
                  <div style={{ fontWeight: 700, color: "#22d3ee" }}>
                    {weatherMarker.title || weatherMarker.label || locationName || "Searched Location"}
                  </div>
                  <div style={{ color: "#94a3b8", fontSize: "9px" }}>
                    {weatherMarker.temperature_c != null && `Avg ${Math.round(weatherMarker.temperature_c)}°C`}
                    {weatherMarker.weather_condition && ` · ${weatherMarker.weather_condition}`}
                  </div>
                </div>
              </Tooltip>
              <Popup className="leaflet-popup-custom">
                <div style={{ minWidth: "180px", color: "#0f172a" }}>
                  <div style={{ fontWeight: 800, marginBottom: "6px" }}>
                    {weatherMarker.title || weatherMarker.label || locationName || "Weather Location"}
                  </div>
                  {weatherMarker.temperature_c != null && (
                    <div>Avg Temp: {Math.round(weatherMarker.temperature_c)}°C</div>
                  )}
                  {weatherMarker.weather_condition && (
                    <div>Condition: {weatherMarker.weather_condition}</div>
                  )}
                  {weatherMarker.rain_probability != null && (
                    <div>Rain Chance: {Math.round(weatherMarker.rain_probability * 100)}%</div>
                  )}
                </div>
              </Popup>
            </Marker>
          ) : (
            coordinates && coordinates.latitude && coordinates.longitude && (
              <Marker
                position={[coordinates.latitude, coordinates.longitude]}
              >
                <Tooltip
                  permanent
                  direction="top"
                  offset={[0, -10]}
                  className="leaflet-tooltip-custom"
                >
                  <div
                    style={{
                      background: "rgba(15,23,42,0.92)",
                      border: "1px solid rgba(34,211,238,0.4)",
                      borderRadius: "8px",
                      padding: "4px 8px",
                      fontSize: "10px",
                      color: "#f1f5f9",
                      backdropFilter: "blur(8px)",
                      whiteSpace: "nowrap",
                    }}
                  >
                    <div style={{ fontWeight: 700, color: "#22d3ee" }}>
                      📍 {locationName || "Searched Location"}
                    </div>
                  </div>
                </Tooltip>
              </Marker>
            )
          )}
        </MapContainer>
      </div>
    </div>
  );
}
