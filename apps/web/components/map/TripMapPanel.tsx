"use client";

import { useEffect, useState, useMemo, useRef } from "react";
import { MapContainer, TileLayer, Marker, Popup, Polyline, Tooltip, Circle, useMap } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import "leaflet-defaulticon-compatibility/dist/leaflet-defaulticon-compatibility.css";
import "leaflet-defaulticon-compatibility";
import { Layers, Eye, RefreshCw, ZoomIn, ZoomOut, CloudRain, Sun, Wind, Navigation, AlertTriangle, ShieldCheck } from "lucide-react";

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
  description?: string;
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

export interface MapMarkerItem {
  id: string;
  label: string;
  latitude: number;
  longitude: number;
  title?: string;
  description?: string;
  temperature_c?: number;
  weather_condition?: string;
  rain_probability?: number;
  is_indoor?: boolean;
}

interface Props {
  tripPlan?: TripPlan | null;
  coordinates?: { latitude: number; longitude: number } | null;
  locationName?: string | null;
  weatherMarker?: MapMarkerItem | null;
  weatherMarkers?: MapMarkerItem[];
  domain?: string;
  activeDay?: number;
  onActiveDayChange?: (day: number) => void;
  theme?: string;
}

// ── Time block colors & icons ──────────────────────────────────
const TIME_BLOCK_COLOR: Record<string, string> = {
  morning: "#0284c7",
  lunch: "#d97706",
  afternoon: "#6366f1",
  dinner: "#ea580c",
  evening: "#8b5cf6",
};

const CATEGORY_ICON_MAP: Record<string, string> = {
  attraction: "🏛️",
  restaurant: "🍜",
  cafe: "☕",
  market: "🛒",
  beach: "🏖️",
};

// ── Basemap Tile Providers (100% Free, High-Res, No API Key Required, No Watermark) ──
const BASEMAP_TILES = {
  voyager: {
    name: "Standard",
    url: "https://{s}.tile.openstreetmap.fr/hot/{z}/{x}/{y}.png",
    attribution: '&copy; <a href="https://openstreetmap.org">OpenStreetMap</a> contributors'
  },
  satellite: {
    name: "Satellite",
    url: "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    attribution: '&copy; <a href="https://esri.com/">Esri</a>'
  },
  dark: {
    name: "Dark",
    url: "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}",
    attribution: '&copy; <a href="https://esri.com/">Esri</a>'
  }
};

// ── Custom Animated Numbered Marker ────────────────────────────
function createCustomPin(order: number | string, color: string, isIndoor?: boolean, iconEmoji?: string) {
  const html = `
    <div style="position:relative; width:36px; height:36px; display:flex; align-items:center; justify-content:center;">
      <div style="position:absolute; inset:0; border-radius:50%; background:${color}30; animation:ping 2s cubic-bezier(0,0,0.2,1) infinite;"></div>
      <div style="
        position:relative;
        width:32px; height:32px; border-radius:50%;
        background:${color}; border:2.5px solid #ffffff;
        display:flex; align-items:center; justify-content:center;
        font-weight:900; font-size:12px; color:#ffffff;
        box-shadow:0 4px 12px rgba(0,0,0,0.35);
      ">
        ${iconEmoji ? `<span style="font-size:14px;">${iconEmoji}</span>` : order}
        ${isIndoor ? '<span style="position:absolute;top:-4px;right:-4px;font-size:9px;background:#ffffff;border-radius:50%;padding:1px;box-shadow:0 1px 3px rgba(0,0,0,0.2);">🏠</span>' : ""}
      </div>
    </div>
  `;
  return L.divIcon({ html, className: "", iconSize: [36, 36], iconAnchor: [18, 18], popupAnchor: [0, -18] });
}

// ── Domain Specific Pulse Pin ──────────────────────────────────
function createDomainPin(label: string, domainType?: string) {
  const isCrane = label.includes("Crane") || domainType === "construction";
  const isAgri = label.includes("Rice") || label.includes("Spore") || domainType === "agriculture";
  const isRadar = label.includes("Radar") || domainType === "severe_weather";

  const color = isCrane ? "#ef4444" : isAgri ? "#10b981" : isRadar ? "#0284c7" : "#0284c7";
  const icon = isCrane ? "🏗️" : isAgri ? "🌾" : isRadar ? "📡" : "📍";

  const html = `
    <div style="position:relative; width:38px; height:38px; display:flex; align-items:center; justify-content:center;">
      <div style="position:absolute; inset:0; border-radius:50%; background:${color}40; animation:ping 2s cubic-bezier(0,0,0.2,1) infinite;"></div>
      <div style="
        position:relative;
        width:34px; height:34px; border-radius:50%;
        background:${color}; border:2.5px solid #ffffff;
        display:flex; align-items:center; justify-content:center;
        font-size:15px;
        box-shadow:0 6px 16px rgba(0,0,0,0.4);
      ">
        ${icon}
      </div>
    </div>
  `;
  return L.divIcon({ html, className: "", iconSize: [38, 38], iconAnchor: [19, 19], popupAnchor: [0, -19] });
}

// ── Fit Map Bounds Controller Component ────────────────────────
function FitBoundsController({ coords, triggerKey }: { coords: [number, number][]; triggerKey?: string | number }) {
  const map = useMap();
  useEffect(() => {
    if (coords && coords.length > 0) {
      if (coords.length === 1) {
        map.setView(coords[0], 13, { animate: true });
      } else {
        const bounds = L.latLngBounds(coords);
        map.fitBounds(bounds, { padding: [40, 40], maxZoom: 15, animate: true });
      }
    }
  }, [triggerKey, map, JSON.stringify(coords)]);
  return null;
}

// ── Main Component ─────────────────────────────────────────────
export default function TripMapPanel({ 
  tripPlan, 
  coordinates, 
  locationName,
  weatherMarker,
  weatherMarkers = [],
  domain,
  activeDay = 1,
  onActiveDayChange,
  theme = "light",
}: Props) {
  // Basemap style state
  const [mapStyle, setMapStyle] = useState<"voyager" | "dark" | "satellite">(
    theme === "dark" ? "dark" : "voyager"
  );
  const [showRadar, setShowRadar] = useState<boolean>(true);
  const [selectedDayTab, setSelectedDayTab] = useState<number | "all">(activeDay);
  const [recenterTrigger, setRecenterTrigger] = useState<number>(0);

  useEffect(() => {
    if (theme === "dark") {
      setMapStyle("dark");
    } else {
      setMapStyle("voyager");
    }
  }, [theme]);

  useEffect(() => {
    setSelectedDayTab(activeDay);
  }, [activeDay]);

  const hasTripPlan = !!(tripPlan && tripPlan.days && tripPlan.days.length);

  // Active stops calculation based on selected day tab
  const displayStops = useMemo(() => {
    if (!hasTripPlan || !tripPlan) return [];
    if (selectedDayTab === "all") {
      return tripPlan.days.flatMap(d => d.stops);
    }
    const day = tripPlan.days.find(d => d.day === selectedDayTab) || tripPlan.days[0];
    return day?.stops || [];
  }, [hasTripPlan, tripPlan, selectedDayTab]);

  // Unified marker list for non-trip views
  const nonTripMarkers: MapMarkerItem[] = useMemo(() => {
    if (weatherMarkers && weatherMarkers.length > 0) {
      return weatherMarkers;
    }
    if (weatherMarker) {
      return [weatherMarker];
    }
    if (coordinates && coordinates.latitude && coordinates.longitude) {
      return [{
        id: "coord-center",
        label: locationName || "Location Point",
        title: locationName || "Da Nang Focus Point",
        latitude: coordinates.latitude,
        longitude: coordinates.longitude,
        description: "Target geographic observation coordinate",
        temperature_c: 31,
        weather_condition: "Observational Data"
      }];
    }
    // Fallback Da Nang
    return [{
      id: "danang-center",
      label: "Da Nang Central",
      title: "Da Nang Central Station",
      latitude: 16.0544,
      longitude: 108.2022,
      description: "Da Nang Meteorological & Tourism Observation Network",
      temperature_c: 31,
      weather_condition: "Active Surveillance"
    }];
  }, [weatherMarkers, weatherMarker, coordinates, locationName]);

  // Polyline coords for trip routes
  const polylineCoords: [number, number][] = useMemo(() => {
    return displayStops.map(s => [s.lat, s.lon]);
  }, [displayStops]);

  // Bounding coords
  const allCoords: [number, number][] = useMemo(() => {
    if (hasTripPlan && polylineCoords.length > 0) {
      return polylineCoords;
    }
    return nonTripMarkers.map(m => [m.latitude, m.longitude]);
  }, [hasTripPlan, polylineCoords, nonTripMarkers]);

  // Center coordinate
  const [centerLat, centerLon] = useMemo(() => {
    if (allCoords.length > 0) {
      const avgLat = allCoords.reduce((acc, curr) => acc + curr[0], 0) / allCoords.length;
      const avgLon = allCoords.reduce((acc, curr) => acc + curr[1], 0) / allCoords.length;
      return [avgLat, avgLon];
    }
    return [16.0544, 108.2022];
  }, [allCoords]);

  const handleDaySelect = (day: number | "all") => {
    setSelectedDayTab(day);
    if (typeof day === "number" && onActiveDayChange) {
      onActiveDayChange(day);
    }
  };

  const handleRecenter = () => {
    setRecenterTrigger(prev => prev + 1);
  };

  return (
    <div className="flex flex-col h-full w-full bg-slate-900 overflow-hidden relative select-none">
      
      {/* ── Top Map Overlay Toolbar ─────────────────────────────── */}
      <div className="absolute top-3 left-3 right-3 z-[1000] flex flex-wrap items-center justify-between gap-2 pointer-events-none">
        
        {/* Left: Day Filter Tabs for Trip Planning */}
        {hasTripPlan && tripPlan && (
          <div className="flex items-center gap-1 bg-slate-950/80 dark:bg-slate-900/90 backdrop-blur-md p-1 rounded-xl border border-white/10 shadow-lg pointer-events-auto">
            {tripPlan.days.map((d) => (
              <button
                key={d.day}
                onClick={() => handleDaySelect(d.day)}
                className={`px-2.5 py-1 text-[11px] font-extrabold rounded-lg transition-all ${
                  selectedDayTab === d.day
                    ? "bg-blue-600 text-white shadow-sm"
                    : "text-slate-300 hover:text-white hover:bg-white/10"
                }`}
              >
                Day {d.day}
              </button>
            ))}
            <button
              onClick={() => handleDaySelect("all")}
              className={`px-2 py-1 text-[10px] font-bold rounded-lg transition-all ${
                selectedDayTab === "all"
                  ? "bg-indigo-600 text-white shadow-sm"
                  : "text-slate-400 hover:text-white hover:bg-white/10"
              }`}
            >
              All
            </button>
          </div>
        )}

        {/* Non-trip domain badge indicator */}
        {!hasTripPlan && (
          <div className="flex items-center gap-1.5 bg-slate-950/80 backdrop-blur-md px-3 py-1.5 rounded-xl border border-white/10 shadow-lg pointer-events-auto">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <span className="text-[11px] font-extrabold uppercase tracking-wider text-slate-200">
              {domain === "construction" ? "🏗️ Structural Hazard Zones" :
               domain === "agriculture" ? "🌾 Irrigation & Soil Grid" :
               domain === "severe_weather" ? "📡 Coastal Radar Network" : "🗺️ Live Geospatial Feed"}
            </span>
          </div>
        )}

        {/* Right: Map Type Switcher + Radar Toggle + Recenter */}
        <div className="flex items-center gap-1 bg-slate-950/80 backdrop-blur-md p-1 rounded-xl border border-white/10 shadow-lg pointer-events-auto ml-auto">
          
          {/* Style Selector */}
          <button
            onClick={() => setMapStyle(mapStyle === "voyager" ? "satellite" : mapStyle === "satellite" ? "dark" : "voyager")}
            className="flex items-center gap-1 px-2.5 py-1 text-[10px] font-bold text-slate-200 hover:text-white hover:bg-white/10 rounded-lg transition-colors"
            title="Switch Map Tile Style"
          >
            <Layers size={12} className="text-cyan-400" />
            <span>{BASEMAP_TILES[mapStyle].name}</span>
          </button>

          {/* Radar Toggle */}
          <button
            onClick={() => setShowRadar(!showRadar)}
            className={`flex items-center gap-1 px-2.5 py-1 text-[10px] font-bold rounded-lg transition-colors ${
              showRadar ? "bg-cyan-500/20 text-cyan-300 border border-cyan-500/30" : "text-slate-400 hover:bg-white/10"
            }`}
            title="Toggle Weather Radar Overlay"
          >
            <CloudRain size={12} className={showRadar ? "text-cyan-400" : "text-slate-400"} />
            <span>Radar</span>
          </button>

          {/* Recenter */}
          <button
            onClick={handleRecenter}
            className="p-1 text-slate-300 hover:text-white hover:bg-white/10 rounded-lg transition-colors"
            title="Recenter Map View"
          >
            <RefreshCw size={12} />
          </button>
        </div>

      </div>

      {/* ── Leaflet Map Container ─────────────────────────────────── */}
      <div className="flex-1 w-full h-full relative z-0">
        <MapContainer
          key={`map-container-${mapStyle}`}
          center={[centerLat, centerLon]}
          zoom={13}
          zoomControl={false}
          style={{ height: "100%", width: "100%", background: "#0b1120" }}
          className="w-full h-full outline-none"
        >
          <TileLayer
            url={BASEMAP_TILES[mapStyle].url}
            attribution={BASEMAP_TILES[mapStyle].attribution}
          />

          {/* Fit Bounds Controller */}
          <FitBoundsController coords={allCoords} triggerKey={`${selectedDayTab}-${recenterTrigger}`} />

          {/* ── Simulated Weather Radar Layer Overlay ──────────────── */}
          {showRadar && (
            <>
              {/* Convective Thunderstorm Radar Cell over West Da Nang (Lien Chieu / Hoa Khanh) */}
              <Circle
                center={[16.0748, 108.1499]}
                radius={3800}
                pathOptions={{
                  color: domain === "construction" ? "#ef4444" : "#0284c7",
                  fillColor: domain === "construction" ? "#ef4444" : "#06b6d4",
                  fillOpacity: 0.18,
                  weight: 2,
                  dashArray: "4, 6"
                }}
              >
                <Tooltip direction="center" opacity={0.9} permanent={false}>
                  <div className="text-[10px] font-bold text-slate-900">
                    {domain === "construction" ? "⚠️ 14.8 m/s Wind Shear Zone" : "🌧️ 32mm Convective Storm Cell"}
                  </div>
                </Tooltip>
              </Circle>

              {/* Natural Soil Moisture Recharge Catchment (Hoa Vang Basin) */}
              {domain === "agriculture" && (
                <Circle
                  center={[15.9866, 108.1511]}
                  radius={4500}
                  pathOptions={{
                    color: "#10b981",
                    fillColor: "#10b981",
                    fillOpacity: 0.16,
                    weight: 2,
                    dashArray: "6, 8"
                  }}
                >
                  <Tooltip direction="center" opacity={0.9} permanent={false}>
                    <div className="text-[10px] font-bold text-slate-900">
                      💧 46mm Soil Moisture Replenishment Catchment
                    </div>
                  </Tooltip>
                </Circle>
              )}

              {/* Coastal Maritime Radar Warning Zone (Son Tra / Tien Sa) */}
              {domain === "severe_weather" && (
                <Circle
                  center={[16.1200, 108.2800]}
                  radius={5200}
                  pathOptions={{
                    color: "#0284c7",
                    fillColor: "#0284c7",
                    fillOpacity: 0.15,
                    weight: 2,
                    dashArray: "5, 5"
                  }}
                >
                  <Tooltip direction="center" opacity={0.9} permanent={false}>
                    <div className="text-[10px] font-bold text-slate-900">
                      📡 Son Tra Doppler Radar 48855 Active Surveillance Radius
                    </div>
                  </Tooltip>
                </Circle>
              )}
            </>
          )}

          {/* ── Route Polyline (Trip Planning) ──────────────────────── */}
          {hasTripPlan && polylineCoords.length > 1 && (
            <Polyline
              positions={polylineCoords}
              pathOptions={{
                color: "#0284c7",
                weight: 3.5,
                opacity: 0.85,
                dashArray: "6, 8",
              }}
            />
          )}

          {/* ── Markers: Trip Stops ─────────────────────────────────── */}
          {hasTripPlan ? (
            displayStops.map((stop) => {
              const color = TIME_BLOCK_COLOR[stop.time_block] || "#0284c7";
              const catEmoji = CATEGORY_ICON_MAP[stop.category];

              return (
                <Marker
                  key={stop.place_id}
                  position={[stop.lat, stop.lon]}
                  icon={createCustomPin(stop.order, color, stop.is_indoor, catEmoji)}
                >
                  {/* Clean Non-Overlapping Hover Tooltip */}
                  <Tooltip direction="top" offset={[0, -18]} opacity={0.95}>
                    <div className="text-[11px] font-bold text-slate-900 flex items-center gap-1.5">
                      <span>{stop.name}</span>
                      {stop.forecast_temp != null && (
                        <span className="text-amber-600 font-extrabold">· {stop.forecast_temp}°C</span>
                      )}
                    </div>
                  </Tooltip>

                  {/* Rich Liquid Glass Popup on Click */}
                  <Popup className="leaflet-popup-custom">
                    <div className="p-3 min-w-[210px] space-y-2.5 text-slate-900 dark:text-white bg-slate-900/95 backdrop-blur-xl rounded-2xl border border-white/10 shadow-2xl">
                      <div className="flex items-start gap-2.5">
                        <span className="text-2xl p-2 rounded-xl bg-white/10 shrink-0">
                          {catEmoji || "📍"}
                        </span>
                        <div>
                          <h4 className="text-xs font-black text-white leading-tight">
                            {stop.name}
                          </h4>
                          <div className="text-[10px] font-semibold text-slate-400 mt-0.5 flex items-center gap-1">
                            <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: color }} />
                            <span>{stop.time_block.toUpperCase()} · {stop.planned_time}</span>
                          </div>
                        </div>
                      </div>

                      {stop.description && (
                        <p className="text-[11px] font-medium text-slate-300 leading-snug">
                          {stop.description}
                        </p>
                      )}

                      <div className="grid grid-cols-2 gap-2 pt-2 border-t border-white/10 text-[10px]">
                        <div className="bg-white/5 p-2 rounded-lg">
                          <span className="text-slate-400 block font-semibold">Environment</span>
                          <span className="font-bold text-cyan-300">{stop.is_indoor ? "🏠 Indoor Safe" : "🌤 Outdoor"}</span>
                        </div>
                        <div className="bg-white/5 p-2 rounded-lg">
                          <span className="text-slate-400 block font-semibold">Forecast Temp</span>
                          <span className="font-bold text-amber-400">🌡 {stop.forecast_temp ?? 31}°C</span>
                        </div>
                      </div>
                    </div>
                  </Popup>
                </Marker>
              );
            })
          ) : (
            /* ── Non-Trip Domain Markers ───────────────────────────── */
            nonTripMarkers.map((marker, idx) => {
              return (
                <Marker
                  key={marker.id || idx}
                  position={[marker.latitude, marker.longitude]}
                  icon={createDomainPin(marker.label, domain)}
                >
                  <Tooltip direction="top" offset={[0, -18]} opacity={0.95}>
                    <div className="text-[11px] font-bold text-slate-900 flex items-center gap-1">
                      <span>{marker.title || marker.label}</span>
                      {marker.temperature_c != null && (
                        <span className="text-blue-700 font-extrabold">· {marker.temperature_c}°C</span>
                      )}
                    </div>
                  </Tooltip>

                  <Popup className="leaflet-popup-custom">
                    <div className="p-3.5 min-w-[220px] space-y-2 text-slate-900 dark:text-white bg-slate-900/95 backdrop-blur-xl rounded-2xl border border-white/10 shadow-2xl">
                      <div className="flex items-center justify-between gap-2 border-b border-white/10 pb-2">
                        <span className="text-xs font-black text-cyan-300">
                          {marker.label}
                        </span>
                        <span className="text-[10px] font-bold px-2 py-0.5 rounded-md bg-white/10 text-slate-300">
                          {marker.weather_condition || "Active"}
                        </span>
                      </div>

                      <h4 className="text-xs font-black text-white">
                        {marker.title || marker.label}
                      </h4>

                      {marker.description && (
                        <p className="text-[11px] text-slate-300 leading-snug font-medium">
                          {marker.description}
                        </p>
                      )}

                      <div className="flex items-center justify-between pt-2 border-t border-white/10 text-[10px] text-slate-400 font-semibold">
                        <span>Lat: {marker.latitude.toFixed(4)}, Lon: {marker.longitude.toFixed(4)}</span>
                        {marker.temperature_c != null && (
                          <span className="text-amber-400 font-bold">🌡 {marker.temperature_c}°C</span>
                        )}
                      </div>
                    </div>
                  </Popup>
                </Marker>
              );
            })
          )}
        </MapContainer>
      </div>

      {/* ── Bottom Floating Radar Legend (When radar is active) ── */}
      {showRadar && (
        <div className="absolute bottom-3 right-3 z-[1000] flex items-center gap-2 bg-slate-950/85 backdrop-blur-md px-3 py-1.5 rounded-xl border border-white/10 shadow-xl pointer-events-none text-[10px]">
          <span className="font-bold text-slate-400 uppercase tracking-wider">Radar Echo:</span>
          <div className="flex items-center gap-1">
            <span className="w-2.5 h-2.5 rounded-sm bg-cyan-400" />
            <span className="text-slate-300 font-semibold">Light</span>
          </div>
          <div className="flex items-center gap-1">
            <span className="w-2.5 h-2.5 rounded-sm bg-emerald-400" />
            <span className="text-slate-300 font-semibold">Moderate</span>
          </div>
          <div className="flex items-center gap-1">
            <span className="w-2.5 h-2.5 rounded-sm bg-rose-500" />
            <span className="text-slate-300 font-semibold">Heavy/Gust</span>
          </div>
        </div>
      )}

    </div>
  );
}
