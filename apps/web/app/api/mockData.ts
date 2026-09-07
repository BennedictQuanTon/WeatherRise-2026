export interface LocationPoint {
  name: string;
  latitude: number;
  longitude: number;
}

export interface MapMarker {
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

export interface TripViewStop {
  order: number;
  time: string;
  time_block: "morning" | "lunch" | "afternoon" | "dinner" | "evening";
  category: "attraction" | "restaurant" | "cafe" | "market" | "beach";
  name: string;
  description?: string;
  latitude: number;
  longitude: number;
  forecast_temp_c?: number;
  rain_probability?: number;
  weather_condition?: string;
  is_indoor: boolean;
  weather_suitability?: "good" | "medium" | "poor";
}

export interface HourlyForecastItem {
  time: string;
  temp_c: number;
  feels_like_c: number;
  rain_probability: number;
  rain_mm: number;
  wind_kmh: number;
  humidity_percent: number;
  condition: string;
}

export interface TripViewDay {
  day: number;
  date?: string;
  title: string;
  summary: string;
  weather: {
    high_c: number;
    low_c: number;
    rain_probability: number;
    condition: string;
  };
  hourly_forecast?: HourlyForecastItem[];
  stops: TripViewStop[];
}

export interface TripPlanningView {
  title: string;
  date_range: { start?: string; end?: string; label?: string };
  summary_cards: {
    avg_high_c: number;
    avg_low_c: number;
    avg_wind_kmh: number;
    humidity_percent: number;
    rain_risk: string;
  };
  ai_summary: string;
  days: TripViewDay[];
  map: {
    markers: MapMarker[];
  };
}

export interface DomainMetricItem {
  label: string;
  value: string;
  sub?: string;
  source?: string;
  standard?: string;
  badge?: string;
  badgeColor?: "emerald" | "amber" | "rose" | "blue" | "purple" | "cyan";
  iconName?: string;
}

export interface TechStackInfo {
  reasoning_model: string;
  domain_agent: string;
  weather_sources: string[];
  vector_db: string;
  guardrails_score: string;
  latency: string;
  tokens_per_sec: string;
}

export interface HazardEvaluationItem {
  title: string;
  standard_code: string;
  status: string;
  threshold_limit: string;
  observed_value: string;
  impact_description: string;
  severity: "high" | "medium" | "low";
}

export interface DomainOverviewData {
  title: string;
  subtitle: string;
  executive_summary: string;
  compliance_status: string;
  hazards: HazardEvaluationItem[];
  operational_protocols: string[];
}

export interface WeatherPredictionView {
  title: string;
  location: LocationPoint;
  date_range: { start?: string; end?: string; label?: string };
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
    avg_temperature_c: number;
    min_temperature_c: number;
    max_temperature_c: number;
    avg_wind_kmh: number;
    total_rainfall_mm: number;
    rain_risk: string;
    wind_risk: string;
    heat_risk: string;
    overall_risk: string;
    most_common_condition: string;
  };
  domain_metrics?: DomainMetricItem[];
  tech_stack_info?: TechStackInfo;
  overview?: DomainOverviewData;
  daily_forecast: Array<{
    date: string;
    day_label: string;
    condition: string;
    condition_icon: string;
    max_temp_c: number;
    min_temp_c: number;
    wind_kmh: number;
    rain_probability: number;
    rain_mm: number;
    risk: string;
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

export interface ChatResult {
  session_id: string;
  status: string;
  response_type: "trip_planning" | "weather_prediction" | "general";
  domain: string;
  location: string;
  prediction?: string;
  recommendation?: string;
  risk_assessment?: {
    rain_risk?: string;
    wind_risk?: string;
    heat_risk?: string;
    overall_risk?: string;
    trip_disruption_risk?: string;
    construction_safety_risk?: string;
    disease_risk?: string;
  };
  explanation?: string;
  final_answer?: string;
  trip_plan?: any;
  error?: string;
  coordinates?: { latitude: number; longitude: number };
  evidence?: string[];
  weather_stats?: {
    avg_temperature_c?: number;
    min_temperature_c?: number;
    max_temp?: number;
    max_rain_prob?: number;
    max_wind_speed?: number;
    total_rainfall_mm?: number;
  };
  time_range?: { start?: string; end?: string; raw_text?: string };
  weather_path?: string;
  weather_confidence?: number;
  weather_mode?: string;
  sources_used?: string[];
  tech_stack_info?: TechStackInfo;
  weather_view?: WeatherPredictionView;
  trip_view?: TripPlanningView;
}

// ─────────────────────────────────────────────────────────────────────────────
// 1. TOURISM MOCK DATA (Da Nang 3-Day Weather-Aware Trip)
// ─────────────────────────────────────────────────────────────────────────────
export function getTourismMockResponse(query: string): ChatResult {
  const tech_stack_info: TechStackInfo = {
    reasoning_model: "DeepSeek-R1-Distill-Llama-70B (NVIDIA NIM CoT)",
    domain_agent: "Tourism Itinerary Optimizer & POI Weather Solver",
    weather_sources: ["ERA5 Da Nang Coastal 0.25°", "Open-Meteo HighRes", "Da Nang GIS Vector DB"],
    vector_db: "Qdrant Hybrid Search (NeMo 1024-d + BM25)",
    guardrails_score: "99.4% Safety & Grounding Passed",
    latency: "1.12s",
    tokens_per_sec: "48.5 tok/s"
  };

  const trip_view: TripPlanningView = {
    title: "Plan for Da Nang next week",
    date_range: {
      start: "2026-09-10",
      end: "2026-09-12",
      label: "Sep 10 – Sep 12, 2026"
    },
    summary_cards: {
      avg_high_c: 32,
      avg_low_c: 25,
      avg_wind_kmh: 14.5,
      humidity_percent: 74,
      rain_risk: "Low-Med"
    },
    ai_summary:
      "Weatherise Agent synthesized a 72h high-resolution forecast for Da Nang. Day 1 features clear skies ideal for Son Tra Peninsula & My Khe Beach. Day 2 has an afternoon shower (58% probability from 14:00-16:00), automatically routing indoor cultural venues (Cham Museum & Han Market). Day 3 returns to pleasant mountain conditions at Ba Na Hills.",
    days: [
      {
        day: 1,
        date: "Thursday, Sep 10",
        title: "Son Tra Peninsula & My Khe Beach (Clear Skies & Sea Breeze)",
        summary: "Explore cool morning breeze at Son Tra (26°C), enjoy beach swimming in the afternoon, and watch the Dragon Bridge fire show.",
        weather: {
          high_c: 32,
          low_c: 25,
          rain_probability: 12,
          condition: "Sunny & Gentle Breeze"
        },
        hourly_forecast: [
          { time: "06:00", temp_c: 25, feels_like_c: 26, rain_probability: 5, rain_mm: 0.0, wind_kmh: 12, humidity_percent: 82, condition: "Clear Sky" },
          { time: "08:00", temp_c: 27, feels_like_c: 29, rain_probability: 5, rain_mm: 0.0, wind_kmh: 14, humidity_percent: 78, condition: "Sunny" },
          { time: "10:00", temp_c: 30, feels_like_c: 33, rain_probability: 10, rain_mm: 0.0, wind_kmh: 16, humidity_percent: 72, condition: "Sunny" },
          { time: "12:00", temp_c: 32, feels_like_c: 36, rain_probability: 15, rain_mm: 0.1, wind_kmh: 18, humidity_percent: 68, condition: "Partly Cloudy" },
          { time: "14:00", temp_c: 32, feels_like_c: 35, rain_probability: 12, rain_mm: 0.0, wind_kmh: 19, humidity_percent: 66, condition: "Partly Cloudy" },
          { time: "16:00", temp_c: 30, feels_like_c: 33, rain_probability: 10, rain_mm: 0.0, wind_kmh: 16, humidity_percent: 70, condition: "Gentle Breeze" },
          { time: "18:00", temp_c: 28, feels_like_c: 30, rain_probability: 8, rain_mm: 0.0, wind_kmh: 14, humidity_percent: 75, condition: "Clear" },
          { time: "20:00", temp_c: 27, feels_like_c: 29, rain_probability: 5, rain_mm: 0.0, wind_kmh: 12, humidity_percent: 80, condition: "Cool Night" },
          { time: "22:00", temp_c: 26, feels_like_c: 27, rain_probability: 5, rain_mm: 0.0, wind_kmh: 10, humidity_percent: 84, condition: "Clear Night" }
        ],
        stops: [
          {
            order: 1,
            time: "07:30",
            time_block: "morning",
            category: "cafe",
            name: "Son Tra Marina Cafe",
            description: "Watch the sunrise over Da Nang Bay with a refreshing 12 km/h sea breeze.",
            latitude: 16.0965,
            longitude: 108.2723,
            forecast_temp_c: 26,
            rain_probability: 5,
            weather_condition: "Clear Sky",
            is_indoor: false,
            weather_suitability: "good"
          },
          {
            order: 2,
            time: "09:00",
            time_block: "morning",
            category: "attraction",
            name: "Son Tra Peninsula & Linh Ung Pagoda",
            description: "Visit the 67m Lady Buddha statue with panoramic ocean vistas.",
            latitude: 16.1018,
            longitude: 108.2764,
            forecast_temp_c: 29,
            rain_probability: 10,
            weather_condition: "Sunny",
            is_indoor: false,
            weather_suitability: "good"
          },
          {
            order: 3,
            time: "12:00",
            time_block: "lunch",
            category: "restaurant",
            name: "Be Man Fresh Seafood My Khe",
            description: "Enjoy fresh local seafood along Vo Nguyen Giap coastal avenue.",
            latitude: 16.0645,
            longitude: 108.2468,
            forecast_temp_c: 32,
            rain_probability: 15,
            weather_condition: "Partly Cloudy",
            is_indoor: true,
            weather_suitability: "good"
          },
          {
            order: 4,
            time: "15:30",
            time_block: "afternoon",
            category: "beach",
            name: "My Khe Beach (T20 Zone)",
            description: "Beach swimming and water sports as afternoon temperature cools to 29°C.",
            latitude: 16.0601,
            longitude: 108.2465,
            forecast_temp_c: 29,
            rain_probability: 12,
            weather_condition: "Gentle Breeze",
            is_indoor: false,
            weather_suitability: "good"
          },
          {
            order: 5,
            time: "19:00",
            time_block: "evening",
            category: "attraction",
            name: "Dragon Bridge & Son Tra Night Market",
            description: "Evening stroll along Han River to admire Dragon Bridge and taste local street food.",
            latitude: 16.0611,
            longitude: 108.2272,
            forecast_temp_c: 27,
            rain_probability: 8,
            weather_condition: "Cool Night",
            is_indoor: false,
            weather_suitability: "good"
          }
        ]
      },
      {
        day: 2,
        date: "Friday, Sep 11",
        title: "Museums & Indoor Cultural Experience (Rain-Optimized)",
        summary: "Afternoon showers forecasted (14:00 - 16:00). Weatherise automatically scheduled indoor museums and dining during peak rain hours.",
        weather: {
          high_c: 31,
          low_c: 24,
          rain_probability: 58,
          condition: "Afternoon Showers"
        },
        hourly_forecast: [
          { time: "06:00", temp_c: 25, feels_like_c: 26, rain_probability: 15, rain_mm: 0.0, wind_kmh: 10, humidity_percent: 86, condition: "Cloudy" },
          { time: "08:00", temp_c: 27, feels_like_c: 29, rain_probability: 20, rain_mm: 0.2, wind_kmh: 12, humidity_percent: 82, condition: "Cloudy" },
          { time: "10:00", temp_c: 29, feels_like_c: 32, rain_probability: 30, rain_mm: 0.5, wind_kmh: 15, humidity_percent: 78, condition: "Overcast" },
          { time: "12:00", temp_c: 31, feels_like_c: 35, rain_probability: 40, rain_mm: 1.2, wind_kmh: 18, humidity_percent: 74, condition: "Rain Clouds" },
          { time: "14:00", temp_c: 28, feels_like_c: 31, rain_probability: 65, rain_mm: 4.8, wind_kmh: 22, humidity_percent: 88, condition: "Showers" },
          { time: "16:00", temp_c: 27, feels_like_c: 29, rain_probability: 58, rain_mm: 3.2, wind_kmh: 20, humidity_percent: 90, condition: "Showers" },
          { time: "18:00", temp_c: 26, feels_like_c: 28, rain_probability: 25, rain_mm: 0.4, wind_kmh: 15, humidity_percent: 84, condition: "Clearing Up" },
          { time: "20:00", temp_c: 25, feels_like_c: 27, rain_probability: 15, rain_mm: 0.0, wind_kmh: 12, humidity_percent: 82, condition: "Cloudy Night" },
          { time: "22:00", temp_c: 24, feels_like_c: 26, rain_probability: 10, rain_mm: 0.0, wind_kmh: 10, humidity_percent: 85, condition: "Cool Night" }
        ],
        stops: [
          {
            order: 1,
            time: "08:00",
            time_block: "morning",
            category: "restaurant",
            name: "Ba Mua Mi Quang - Tran Binh Trong",
            description: "Authentic Central Vietnam specialty turmeric noodles with shrimp and pork.",
            latitude: 16.0682,
            longitude: 108.2201,
            forecast_temp_c: 27,
            rain_probability: 20,
            weather_condition: "Cloudy",
            is_indoor: true,
            weather_suitability: "good"
          },
          {
            order: 2,
            time: "09:30",
            time_block: "morning",
            category: "market",
            name: "Han Market Da Nang",
            description: "Indoor market shopping for local specialty treats, dry seafood, and crafts.",
            latitude: 16.0689,
            longitude: 108.2246,
            forecast_temp_c: 29,
            rain_probability: 30,
            weather_condition: "Overcast",
            is_indoor: true,
            weather_suitability: "good"
          },
          {
            order: 3,
            time: "12:00",
            time_block: "lunch",
            category: "restaurant",
            name: "Tran Pork Rice Paper Rolls",
            description: "Famous local delicacy lunch in modern air-conditioned dining comfort.",
            latitude: 16.0654,
            longitude: 108.2198,
            forecast_temp_c: 30,
            rain_probability: 40,
            weather_condition: "Rain Clouds",
            is_indoor: true,
            weather_suitability: "good"
          },
          {
            order: 4,
            time: "14:00",
            time_block: "afternoon",
            category: "attraction",
            name: "Museum of Cham Sculpture",
            description: "Sheltered indoor visit during rain showers to explore the world's premier Cham artifact collection.",
            latitude: 16.0604,
            longitude: 108.2227,
            forecast_temp_c: 28,
            rain_probability: 65,
            weather_condition: "Showers",
            is_indoor: true,
            weather_suitability: "good"
          },
          {
            order: 5,
            time: "16:30",
            time_block: "afternoon",
            category: "cafe",
            name: "Cong Caphe Bach Dang",
            description: "Sip signature coconut iced coffee by the Han River as rain skies clear.",
            latitude: 16.0674,
            longitude: 108.2241,
            forecast_temp_c: 27,
            rain_probability: 25,
            weather_condition: "Clearing Up",
            is_indoor: true,
            weather_suitability: "good"
          }
        ]
      },
      {
        day: 3,
        date: "Saturday, Sep 12",
        title: "Ba Na Hills Golden Bridge & Hoi An Ancient Town",
        summary: "Cool 22°C mountain breeze at Ba Na summit, followed by lantern-lit night walk in heritage Hoi An.",
        weather: {
          high_c: 28,
          low_c: 22,
          rain_probability: 18,
          condition: "Partly Cloudy & Mountain Mist"
        },
        hourly_forecast: [
          { time: "06:00", temp_c: 22, feels_like_c: 22, rain_probability: 10, rain_mm: 0.0, wind_kmh: 10, humidity_percent: 88, condition: "Mist" },
          { time: "08:00", temp_c: 23, feels_like_c: 23, rain_probability: 15, rain_mm: 0.0, wind_kmh: 12, humidity_percent: 84, condition: "Sun & Clouds" },
          { time: "10:00", temp_c: 25, feels_like_c: 26, rain_probability: 18, rain_mm: 0.1, wind_kmh: 14, humidity_percent: 80, condition: "Sun & Clouds" },
          { time: "12:00", temp_c: 26, feels_like_c: 27, rain_probability: 20, rain_mm: 0.2, wind_kmh: 15, humidity_percent: 76, condition: "Pleasant" },
          { time: "14:00", temp_c: 28, feels_like_c: 29, rain_probability: 15, rain_mm: 0.0, wind_kmh: 14, humidity_percent: 72, condition: "Partly Cloudy" },
          { time: "16:00", temp_c: 27, feels_like_c: 28, rain_probability: 12, rain_mm: 0.0, wind_kmh: 12, humidity_percent: 75, condition: "Clear" },
          { time: "18:00", temp_c: 26, feels_like_c: 27, rain_probability: 8, rain_mm: 0.0, wind_kmh: 10, humidity_percent: 79, condition: "Clear" },
          { time: "20:00", temp_c: 25, feels_like_c: 26, rain_probability: 5, rain_mm: 0.0, wind_kmh: 8, humidity_percent: 82, condition: "Pleasant Evening" },
          { time: "22:00", temp_c: 24, feels_like_c: 25, rain_probability: 5, rain_mm: 0.0, wind_kmh: 8, humidity_percent: 85, condition: "Pleasant Night" }
        ],
        stops: [
          {
            order: 1,
            time: "08:00",
            time_block: "morning",
            category: "attraction",
            name: "Ba Na Hills Cable Car & Golden Bridge",
            description: "World-record cable car journey and photography at the giant stone hands.",
            latitude: 15.9988,
            longitude: 107.9964,
            forecast_temp_c: 22,
            rain_probability: 15,
            weather_condition: "Sun & Clouds",
            is_indoor: false,
            weather_suitability: "good"
          },
          {
            order: 2,
            time: "11:30",
            time_block: "lunch",
            category: "restaurant",
            name: "French Village & Arapang Buffet",
            description: "European-style lunch buffet amidst brisk 23°C mountain air.",
            latitude: 15.9972,
            longitude: 107.9950,
            forecast_temp_c: 23,
            rain_probability: 20,
            weather_condition: "Pleasant",
            is_indoor: true,
            weather_suitability: "good"
          },
          {
            order: 3,
            time: "15:30",
            time_block: "afternoon",
            category: "attraction",
            name: "Non Nuoc Stone Village - Marble Mountains",
            description: "Visit traditional marble sculpture caves en route south to Hoi An.",
            latitude: 16.0028,
            longitude: 108.2612,
            forecast_temp_c: 28,
            rain_probability: 10,
            weather_condition: "Clear",
            is_indoor: false,
            weather_suitability: "good"
          },
          {
            order: 4,
            time: "18:00",
            time_block: "dinner",
            category: "restaurant",
            name: "Ba Buoi Chicken Rice - Hoi An",
            description: "Heritage chicken rice dinner in the heart of Hoi An ancient town.",
            latitude: 15.8795,
            longitude: 108.3301,
            forecast_temp_c: 26,
            rain_probability: 10,
            weather_condition: "Clear",
            is_indoor: true,
            weather_suitability: "good"
          },
          {
            order: 5,
            time: "19:30",
            time_block: "evening",
            category: "attraction",
            name: "Hoi An Ancient Town & Lantern Market",
            description: "Release river lanterns on Hoai River and explore thousands of glowing silk lanterns.",
            latitude: 15.8778,
            longitude: 108.3283,
            forecast_temp_c: 25,
            rain_probability: 5,
            weather_condition: "Pleasant Evening",
            is_indoor: false,
            weather_suitability: "good"
          }
        ]
      }
    ],
    map: {
      markers: [
        { id: "m1", label: "1", latitude: 16.0965, longitude: 108.2723, title: "Son Tra Marina Cafe", category: "cafe", is_indoor: false, weather_condition: "Clear" },
        { id: "m2", label: "2", latitude: 16.1018, longitude: 108.2764, title: "Linh Ung Pagoda Son Tra", category: "attraction", is_indoor: false, weather_condition: "Sunny" },
        { id: "m3", label: "3", latitude: 16.0645, longitude: 108.2468, title: "Be Man Seafood My Khe", category: "restaurant", is_indoor: true, weather_condition: "Partly Cloudy" },
        { id: "m4", label: "4", latitude: 16.0601, longitude: 108.2465, title: "My Khe Beach", category: "beach", is_indoor: false, weather_condition: "Gentle Breeze" },
        { id: "m5", label: "5", latitude: 16.0611, longitude: 108.2272, title: "Dragon Bridge Da Nang", category: "attraction", is_indoor: false, weather_condition: "Cool" },
        { id: "m6", label: "6", latitude: 16.0604, longitude: 108.2227, title: "Museum of Cham Sculpture", category: "attraction", is_indoor: true, weather_condition: "Indoor Safe" },
        { id: "m7", label: "7", latitude: 15.9988, longitude: 107.9964, title: "Golden Bridge Ba Na Hills", category: "attraction", is_indoor: false, weather_condition: "Mist & Clouds" },
        { id: "m8", label: "8", latitude: 15.8778, longitude: 108.3283, title: "Hoi An Ancient Town", category: "attraction", is_indoor: false, weather_condition: "Clear Night" }
      ]
    }
  };

  return {
    session_id: "demo-session-tourism-danang",
    status: "success",
    response_type: "trip_planning",
    domain: "tourism",
    location: "Da Nang, Vietnam",
    prediction: "Da Nang weather over the next 3 days is highly favorable for travel. Light afternoon showers on Day 2 (40-58%), with sunny, pleasant conditions on Day 1 and Day 3.",
    recommendation: "Outdoor highlights (Son Tra, My Khe, Golden Bridge) are prioritized during clear morning windows, with indoor museums and markets scheduled for Friday afternoon.",
    risk_assessment: {
      rain_risk: "Medium",
      wind_risk: "Low",
      heat_risk: "Medium",
      overall_risk: "Low",
      trip_disruption_risk: "Low"
    },
    weather_stats: {
      avg_temperature_c: 28.5,
      min_temperature_c: 24.0,
      max_temp: 32.0,
      max_rain_prob: 58,
      max_wind_speed: 18.5,
      total_rainfall_mm: 8.2
    },
    time_range: {
      start: "2026-09-10",
      end: "2026-09-12",
      raw_text: "Next 3 Days (Sep 10 – Sep 12)"
    },
    weather_path: "Path-A (High-resolution Realtime ERA5/Open-Meteo)",
    weather_confidence: 0.94,
    weather_mode: "standard_multi_agent",
    sources_used: ["Open-Meteo HighRes API", "ERA5 Da Nang Coastal Grid", "Da Nang Tourism GIS Vector DB"],
    tech_stack_info,
    trip_view,
    trip_plan: {
      duration_days: 3,
      location: "Da Nang, Vietnam",
      weather_aware: true,
      planning_mode: "weather_optimized",
      days: trip_view.days.map(d => ({
        day: d.day,
        theme: d.title,
        primary_area: d.summary,
        date: d.date,
        weather_condition: d.weather.condition,
        stops: d.stops.map(s => ({
          order: s.order,
          place_id: `stop-${s.order}-${s.name.replace(/\s+/g, "_")}`,
          name: s.name,
          lat: s.latitude,
          lon: s.longitude,
          time_block: s.time_block,
          planned_time: s.time,
          forecast_temp: s.forecast_temp_c,
          weather_condition: s.weather_condition,
          duration_minutes: 75,
          is_indoor: s.is_indoor,
          category: s.category,
          vibe_tags: [s.time_block, s.category, s.is_indoor ? "indoor" : "outdoor"]
        }))
      }))
    }
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// 2. CONSTRUCTION MOCK DATA (Safety Check: Crane Wind & Concrete Temperature)
// ─────────────────────────────────────────────────────────────────────────────
export function getConstructionMockResponse(query: string): ChatResult {
  const tech_stack_info: TechStackInfo = {
    reasoning_model: "DeepSeek-R1-Distill-Llama-70B (NVIDIA NIM CoT)",
    domain_agent: "Construction Safety & Concrete Thermal Agent",
    weather_sources: ["ECMWF 0.1° High-Res Wind Shear", "ERA5 Solar Flux", "Open-Meteo Lightning CAPE"],
    vector_db: "Qdrant Vector DB (TCVN 5574:2018 & QCVN 18:2021/BXD Index)",
    guardrails_score: "99.2% Safety Compliance Verified",
    latency: "1.24s",
    tokens_per_sec: "44.8 tok/s"
  };

  const domain_metrics: DomainMetricItem[] = [
    { label: "Tower Crane Wind Velocity", value: "14.8 m/s", source: "QCVN 18:2021/BXD (Limit: 12.0 m/s)", sub: "High-elevation gust hazard" },
    { label: "Concrete Hydration Temp", value: "36.5°C", source: "TCVN 5574:2018 Crack Control", sub: "Core thermal gradient limit" },
    { label: "Convective Energy (CAPE)", value: "2,350 J/kg", source: "ECMWF CAPE Convection Model", sub: "Severe afternoon lightning risk" },
    { label: "Scaffolding Wind Load", value: "38.0 km/h", source: "TCVN 5308:1991 (Beaufort 6)", sub: "Tie-back reinforcement required" },
    { label: "Safe Pouring Window", value: "05:30 - 09:30", source: "ACI 305R Hot Weather Standard", sub: "Temp 27°C, wind 8 km/h" },
    { label: "Water Evaporation Rate", value: "1.18 kg/m²/h", source: "ACI 308 Nomograph Protocol", sub: "Surface moisture loss threshold" },
    { label: "Accumulated Rain (4h)", value: "32.0 mm", source: "NCHMF Radar Precipitation", sub: "Cement paste washout hazard" },
    { label: "Safety Compliance Standard", value: "ISO 45001", source: "Occupational Safety Standard", sub: "Automated standard verification" },
  ];

  const overview: DomainOverviewData = {
    title: "Operational Safety Assessment & Structural Risk Overview",
    subtitle: "Standardized evaluation according to QCVN 18:2021/BXD & TCVN 5574:2018 for Da Nang",
    executive_summary: "High atmospheric instability and strong convective activity are forecast over Da Nang between 13:00 - 17:00 tomorrow. Peak wind gusts reach 14.8 m/s (exceeding tower crane safe limit of 12.0 m/s) with 32mm convective downpours and CAPE energy of 2,350 J/kg, mandating suspension of high-elevation crane lifts and outdoor concrete casting during the critical afternoon window.",
    compliance_status: "CRITICAL SAFETY RESTRICTIONS ACTIVE",
    hazards: [
      {
        title: "Tower Crane Wind Shear Hazard",
        standard_code: "QCVN 18:2021/BXD Section 2.4",
        status: "Threshold Exceeded",
        threshold_limit: "12.0 m/s (Max operational limit)",
        observed_value: "14.8 m/s (Beaufort Scale 6-7 gusts)",
        impact_description: "Excessive lateral wind load on crane jib and suspended loads creates tipping and uncontrolled swinging hazard.",
        severity: "high"
      },
      {
        title: "Concrete Thermal Cracking & Evaporation Risk",
        standard_code: "TCVN 5574:2018 & ACI 308",
        status: "Evaporation Warning",
        threshold_limit: "1.00 kg/m²/h evaporation rate",
        observed_value: "1.18 kg/m²/h at 36.5°C peak ambient",
        impact_description: "Rapid surface moisture loss causes severe plastic shrinkage cracking and surface dusting before initial set.",
        severity: "medium"
      },
      {
        title: "Convective Lightning & High-Voltage Equipment",
        standard_code: "TCVN 9385:2012 Lightning Protection",
        status: "Severe Risk (13:30 - 16:30)",
        threshold_limit: "CAPE < 1,000 J/kg",
        observed_value: "CAPE 2,350 J/kg (Deep Convection)",
        impact_description: "Cloud-to-ground lightning discharge risk near tall scaffolding towers and metallic structural frameworks.",
        severity: "high"
      }
    ],
    operational_protocols: [
      "Mandatory shutdown of all tower cranes and hoisting equipment by 12:30 PM; release slewing brakes to free-weathervaning mode.",
      "Reschedule concrete batching to early morning window (05:30 - 09:30) or evening shift after 20:00 when ambient temp < 28°C.",
      "Apply aliphatic alcohol evaporation retardant immediately following screeding, followed by wet burlap and polyethylene curing sheeting.",
      "Inspect harness lifeline anchors and scaffolding perimeter netting against 38 km/h localized gusts."
    ]
  };

  const weather_view: WeatherPredictionView = {
    title: "Construction Weather Safety Assessment — Da Nang",
    location: {
      name: "Da Nang Industrial Construction Zone",
      latitude: 16.0748,
      longitude: 108.1499
    },
    date_range: {
      start: "2026-09-08",
      end: "2026-09-14",
      label: "7-Day Operational Window"
    },
    assumption: {
      summary: "Safety advisory according to QCVN 18:2021/BXD & TCVN 5574:2018 standards. Peak wind gusts of 14.8 m/s and 32mm convective thunderstorm rainfall are forecast between 13:00 - 17:00 tomorrow in Da Nang.",
      should_go: false,
      decision_category: "CONSTRUCTION SAFETY & RISK MANAGEMENT",
      decision_label: "SUSPEND OUTDOOR CONCRETE & CRANE LIFTS (13:00 - 17:00)",
      key_stat_badge: "TOWER CRANE WIND ALERT",
      key_stat_value: "Peak Gust 14.8 m/s (Exceeds 12.0 m/s Limit)",
      reason: "Peak wind velocity exceeds the safe tower crane operational limit (12 m/s per QCVN 18:2021/BXD), and intense rainfall poses a critical risk of cement binder erosion during initial hydration setting."
    },
    statistics: {
      avg_temperature_c: 31.8,
      min_temperature_c: 26.2,
      max_temperature_c: 36.5,
      avg_wind_kmh: 24.2,
      total_rainfall_mm: 48.5,
      rain_risk: "High",
      wind_risk: "High",
      heat_risk: "High",
      overall_risk: "High",
      most_common_condition: "Thunderstorms & Heat Peak"
    },
    domain_metrics,
    tech_stack_info,
    overview,
    daily_forecast: [
      { date: "2026-09-08", day_label: "Tuesday (Today)", condition: "Thunderstorms", condition_icon: "cloud-lightning", max_temp_c: 35.5, min_temp_c: 26.8, wind_kmh: 38, rain_probability: 75, rain_mm: 32, risk: "High" },
      { date: "2026-09-09", day_label: "Wednesday", condition: "Partly Cloudy", condition_icon: "cloud-sun", max_temp_c: 33.2, min_temp_c: 25.5, wind_kmh: 18, rain_probability: 25, rain_mm: 2, risk: "Low" },
      { date: "2026-09-10", day_label: "Thursday", condition: "Sunny", condition_icon: "sun", max_temp_c: 34.0, min_temp_c: 26.0, wind_kmh: 14, rain_probability: 10, rain_mm: 0, risk: "Low" },
      { date: "2026-09-11", day_label: "Friday", condition: "Sunny", condition_icon: "sun", max_temp_c: 35.0, min_temp_c: 26.5, wind_kmh: 15, rain_probability: 15, rain_mm: 0, risk: "Medium" },
      { date: "2026-09-12", day_label: "Saturday", condition: "Cloudy", condition_icon: "cloud", max_temp_c: 32.5, min_temp_c: 25.0, wind_kmh: 20, rain_probability: 30, rain_mm: 4, risk: "Low" },
      { date: "2026-09-13", day_label: "Sunday", condition: "Rain", condition_icon: "cloud-rain", max_temp_c: 30.0, min_temp_c: 24.5, wind_kmh: 26, rain_probability: 60, rain_mm: 18, risk: "Medium" },
      { date: "2026-09-14", day_label: "Monday", condition: "Partly Cloudy", condition_icon: "cloud-sun", max_temp_c: 31.5, min_temp_c: 25.0, wind_kmh: 16, rain_probability: 20, rain_mm: 1, risk: "Low" }
    ],
    recommendations: [
      "Optimal Concrete Pouring Windows: Reschedule batching to early morning (05:00 - 09:30) or night shift (after 20:00) when surface temp < 30°C and no convective storms.",
      "Tower Crane Operation: Lock rotation brakes and lower hooks before 12:30 PM when wind velocity crosses 10 m/s threshold.",
      "Curing Management: Apply evaporation retardant and deploy polyethylene curing sheets to prevent plastic shrinkage cracking (temp gradient > 8°C).",
      "Scaffolding & High-Elevation Work: Inspect tie-backs and harness anchor points against localized afternoon squalls."
    ],
    alternatives: [
      {
        name: "Early Morning Pouring Shift (05:30 - 09:30)",
        description: "Ambient temp 27°C, gentle 8 km/h wind, 82% RH, optimal per TCVN 5574:2018 standards.",
        distance_label: "Primary Recommendation"
      },
      {
        name: "Night Concrete Placement (20:00 - 02:00)",
        description: "Dry conditions with steady 26.5°C temperature to ensure uniform mass concrete hydration.",
        distance_label: "Contingency Window"
      }
    ],
    map: {
      center: { name: "Da Nang Construction Zone", latitude: 16.0748, longitude: 108.1499 },
      markers: [
        { id: "site-1", label: "🏗️ Tower Crane Zone", latitude: 16.0748, longitude: 108.1499, title: "Da Nang Main Structural Zone", description: "Warning: 14.8 m/s wind gusts expected 13:00-17:00 (QCVN 18:2021/BXD)", temperature_c: 35.5, weather_condition: "Convective Storms" },
        { id: "site-2", label: "🚢 Marine Berth", latitude: 16.1285, longitude: 108.1412, title: "Lien Chieu Port Deepwater Pier", description: "Scaffolding tie-back reinforcement against 38 km/h coastal gusts", temperature_c: 33.0, weather_condition: "High Coastal Gusts" },
        { id: "site-3", label: "🏭 Concrete Plant", latitude: 16.0820, longitude: 108.1050, title: "Hi-Tech Park Concrete Plant", description: "Early morning batching shift 05:30 - 09:30 recommended", temperature_c: 27.0, weather_condition: "Optimal Pouring" }
      ]
    },
    insights: [
      {
        title: "QCVN 18:2021/BXD - Tower Crane Wind Limits",
        body: "National building safety code mandates complete stoppage of high-elevation lifting when wind gusts reach Beaufort Scale 6 (> 10.8 - 13.8 m/s). Peak gust forecast: 14.8 m/s at 14:30.",
        type: "wind"
      },
      {
        title: "Hydration Heat & Thermal Cracking (TCVN 5574:2018)",
        body: "Peak midday temp of 36.5°C coupled with humidity drops elevates water loss > 1.0 kg/m²/h, requiring immediate curing membrane application.",
        type: "heat"
      },
      {
        title: "Lightning Hazard & Extreme Rainfall",
        body: "CAPE energy index > 2,350 J/kg indicates high cloud-to-ground lightning risk, necessitating power cutoff for outdoor high-voltage equipment.",
        type: "rain"
      }
    ]
  };

  return {
    session_id: "demo-session-construction",
    status: "success",
    response_type: "weather_prediction",
    domain: "construction",
    location: "Da Nang Construction Zone",
    prediction: "Tomorrow afternoon (13:00 - 17:00) in Da Nang features localized thunderstorm rainfall of 32mm with wind gusts reaching 38 km/h (14.8 m/s). Morning hours and subsequent days remain dry and workable.",
    recommendation: "Shift concrete pouring to early morning (05:30 - 09:30) or evening shift after 20:00. Secure tower cranes and inspect scaffolding anchor ties before 12:30 PM.",
    risk_assessment: {
      rain_risk: "High",
      wind_risk: "High",
      heat_risk: "High",
      overall_risk: "High",
      construction_safety_risk: "High"
    },
    weather_stats: {
      avg_temperature_c: 31.8,
      min_temperature_c: 26.2,
      max_temp: 36.5,
      max_rain_prob: 75,
      max_wind_speed: 38.0,
      total_rainfall_mm: 32.0
    },
    time_range: {
      start: "2026-09-08",
      end: "2026-09-09",
      raw_text: "Tomorrow (13:00 - 17:00 Critical Window)"
    },
    weather_path: "Path-A (ECMWF & Open-Meteo Solar/Wind Integration)",
    weather_confidence: 0.96,
    weather_mode: "standard_multi_agent",
    sources_used: ["QCVN 18:2021/BXD Construction Safety Rules", "TCVN 5574:2018 Concrete Standards", "ECMWF High-Res Wind Shear Model"],
    tech_stack_info,
    weather_view,
    coordinates: { latitude: 16.0748, longitude: 108.1499 }
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// 3. AGRICULTURE MOCK DATA (Smart Irrigation & Crop Disease Prevention)
// ─────────────────────────────────────────────────────────────────────────────
export function getAgricultureMockResponse(query: string): ChatResult {
  const tech_stack_info: TechStackInfo = {
    reasoning_model: "DeepSeek-R1-Distill-Llama-70B (NVIDIA NIM CoT)",
    domain_agent: "Agro-Meteorology & Smart Irrigation Domain Agent",
    weather_sources: ["FAO-56 Penman-Monteith Evapotranspiration", "ERA5 Agricultural Reanalysis", "Open-Meteo Soil & Flux Grid"],
    vector_db: "Qdrant Hybrid Vector Store (Agro-Knowledge Base NeMo 1024-d)",
    guardrails_score: "99.6% Agro-Safety Verification Passed",
    latency: "1.08s",
    tokens_per_sec: "49.2 tok/s"
  };

  const domain_metrics: DomainMetricItem[] = [
    { label: "Reference Evapotranspiration (ETo)", value: "3.6 mm/day", source: "FAO-56 Penman-Monteith Model", sub: "Low crop water demand" },
    { label: "Crop Coefficient (Kc)", value: "1.05", source: "FAO Irrigation Paper No. 56", sub: "Mid-season rice / vegetative phase" },
    { label: "Current Soil Moisture", value: "76.0%", source: "ERA5 Agricultural Reanalysis", sub: "Optimal field capacity: 88%" },
    { label: "Resource Conserved", value: "+38.5%", source: "Smart Irrigation Energy Model", sub: "Pumping electricity & water saved" },
    { label: "Rice Blast Disease Index", value: "64.0%", source: "Pyricularia Oryzae Microclimate Model", sub: "Relative humidity > 85% for 48h" },
    { label: "NPK Leaching Risk", value: "HIGH RISK", source: "Nutrient Runoff Risk Index", sub: "46mm rain washes topdress urea" },
    { label: "Solar Radiation (Rs)", value: "18.4 MJ/m²", source: "Copernicus Atmosphere Service", sub: "Stable photosynthetic active flux" },
    { label: "Vapor Pressure Deficit (VPD)", value: "0.85 kPa", source: "Atmospheric Moisture Flux", sub: "Stomatal conductance equilibrium" },
  ];

  const overview: DomainOverviewData = {
    title: "Agro-Meteorological Advisory & Crop Protection Overview",
    subtitle: "Smart irrigation and crop protection schedule for Hoa Vang, Da Nang",
    executive_summary: "A 48-hour natural precipitation event (46mm total accumulation) will fully replenish root zone soil moisture to 88% Field Capacity in Hoa Vang. Evapotranspiration demand is low (ETo 3.6 mm/day), allowing complete suspension of motor pump irrigation across Hoa Vang farming districts for 48-72 hours, saving 38.5% in operational pumping energy costs.",
    compliance_status: "IRRIGATION SUSPENDED · DISEASE MONITORING ACTIVE",
    hazards: [
      {
        title: "Nutrient Leaching & Urea Washout Hazard",
        standard_code: "MARD Agro-Chemical Directive 2024",
        status: "High Leaching Risk",
        threshold_limit: "Precipitation < 15 mm/day for topdressing",
        observed_value: "46 mm cumulative 48h rainfall",
        impact_description: "Broadcasting granular nitrogen fertilizer prior to rainfall leads to 60-70% nutrient loss via surface runoff into canal waterways.",
        severity: "high"
      },
      {
        title: "Rice Blast Fungus (Pyricularia oryzae)",
        standard_code: "National Plant Protection Standard (QCVN 01-189)",
        status: "Stage 2 Warning Alert",
        threshold_limit: "RH > 85% for > 36 consecutive hours",
        observed_value: "RH 86-90% forecast across 48 hours",
        impact_description: "Extended leaf wetness and warm temperatures (24-30°C) favor fungal spore germination on tender vegetative tillers.",
        severity: "medium"
      },
      {
        title: "Root Hypoxia & Waterlogging in Low Plots",
        standard_code: "FAO Soil Drainage Guidelines",
        status: "Managed Drainage Required",
        threshold_limit: "Soil Moisture < 90% Saturation",
        observed_value: "Moisture peaking at 88% Field Capacity",
        impact_description: "Stagnant standing water in heavy clay furrows reduces root oxygenation if field drainage channels are clogged.",
        severity: "low"
      }
    ],
    operational_protocols: [
      "Shut down electrical pump stations across Hoa Vang co-operative blocks; conserve 38.5% in pumping energy costs.",
      "Withhold all granular urea and NPK topdressing until Friday, Sep 11, when root beds stabilize and sunshine returns.",
      "Inspect and open primary field drainage gates to prevent localized submergence of nursery plots.",
      "Schedule preventive biological fungicide (Tricyclazole / Kasugamycin) application for Thursday morning, Sep 10, once leaf surface dew evaporates."
    ]
  };

  const weather_view: WeatherPredictionView = {
    title: "Agricultural Weather & Irrigation Advisory — Da Nang",
    location: {
      name: "Hoa Vang Agricultural Zone, Da Nang",
      latitude: 15.9866,
      longitude: 108.1511
    },
    date_range: {
      start: "2026-09-08",
      end: "2026-09-14",
      label: "7-Day Agro-Meteorological Cycle"
    },
    assumption: {
      summary: "Cumulative natural rainfall of 46mm forecast over the next 48 hours in Hoa Vang, Da Nang. Soil moisture currently at 76%, reference evapotranspiration ETo = 3.6 mm/day.",
      should_go: false,
      decision_category: "AGRO-METEOROLOGY & SMART IRRIGATION",
      decision_label: "PAUSE ARTIFICIAL IRRIGATION FOR NEXT 48 HOURS",
      key_stat_badge: "RESOURCE OPTIMIZATION",
      key_stat_value: "+38.5% Water & Energy Conserved",
      reason: "Anticipated 46mm rainfall satisfies crop water requirements for the next 9-10 days, saving 38.5% in pumping energy costs while preventing root waterlogging and hypoxia."
    },
    statistics: {
      avg_temperature_c: 28.4,
      min_temperature_c: 23.8,
      max_temperature_c: 32.5,
      avg_wind_kmh: 12.5,
      total_rainfall_mm: 52.0,
      rain_risk: "High",
      wind_risk: "Low",
      heat_risk: "Low",
      overall_risk: "Medium",
      most_common_condition: "Beneficial Rainfall & High Humidity"
    },
    domain_metrics,
    tech_stack_info,
    overview,
    daily_forecast: [
      { date: "2026-09-08", day_label: "Tuesday", condition: "Rain", condition_icon: "cloud-rain", max_temp_c: 30.0, min_temp_c: 24.5, wind_kmh: 14, rain_probability: 80, rain_mm: 28, risk: "High" },
      { date: "2026-09-09", day_label: "Wednesday", condition: "Showers", condition_icon: "cloud-rain", max_temp_c: 29.5, min_temp_c: 24.0, wind_kmh: 12, rain_probability: 65, rain_mm: 18, risk: "Medium" },
      { date: "2026-09-10", day_label: "Thursday", condition: "Partly Cloudy", condition_icon: "cloud-sun", max_temp_c: 31.0, min_temp_c: 24.5, wind_kmh: 10, rain_probability: 20, rain_mm: 2, risk: "Low" },
      { date: "2026-09-11", day_label: "Friday", condition: "Sunny", condition_icon: "sun", max_temp_c: 32.5, min_temp_c: 25.0, wind_kmh: 11, rain_probability: 10, rain_mm: 0, risk: "Low" },
      { date: "2026-09-12", day_label: "Saturday", condition: "Sunny", condition_icon: "sun", max_temp_c: 33.0, min_temp_c: 25.2, wind_kmh: 13, rain_probability: 15, rain_mm: 0, risk: "Low" },
      { date: "2026-09-13", day_label: "Sunday", condition: "Partly Cloudy", condition_icon: "cloud-sun", max_temp_c: 31.8, min_temp_c: 24.8, wind_kmh: 12, rain_probability: 25, rain_mm: 3, risk: "Low" },
      { date: "2026-09-14", day_label: "Monday", condition: "Cloudy", condition_icon: "cloud", max_temp_c: 30.5, min_temp_c: 24.0, wind_kmh: 15, rain_probability: 30, rain_mm: 5, risk: "Low" }
    ],
    recommendations: [
      "Smart Irrigation Schedule (Penman-Monteith): Suspend motor pumps on Sep 8-9. Resume drip/furrow cycle on Sep 11 morning (35 m³/ha).",
      "Fertilizer Nutrient Management: Do NOT broadcast urea or foliar nitrogen prior to rainfall to eliminate runoff into canal waterways.",
      "Blast Fungus Early Warning: Sustained 86% RH triggers Pyricularia oryzae sporulation. Schedule biological fungicide spray on Sep 10 after morning dew clears.",
      "Field Drainage: Clear furrow channels for orchards and low-lying vegetable plots."
    ],
    alternatives: [
      {
        name: "Post-Rain Fertilizer Topdressing (Sep 11)",
        description: "Optimal fertilizer uptake when soil is moist and sunny temps reach 31°C.",
        distance_label: "Recommended Timing"
      },
      {
        name: "Foliar Fungicide Application (Sep 10 Morning)",
        description: "Dry leaf canopy enhances adhesion of biological plant protection agents.",
        distance_label: "Preventive Measure"
      }
    ],
    map: {
      center: { name: "Hoa Vang Agricultural Zone", latitude: 15.9866, longitude: 108.1511 },
      markers: [
        { id: "agri-1", label: "🌾 Rice Co-op Block A", latitude: 15.9866, longitude: 108.1511, title: "Hoa Vang Main Paddy Block A", description: "Forecasted 46mm rainfall - Artificial irrigation suspended", temperature_c: 29.5, weather_condition: "Moisture Recharge" },
        { id: "agri-2", label: "💧 Drainage Canal", latitude: 15.9622, longitude: 108.1750, title: "Hoa Tien Primary Drainage Canal", description: "Sluice gates opened for gravity drainage of low plots", temperature_c: 28.5, weather_condition: "Active Drainage" },
        { id: "agri-3", label: "🔬 Spore Station", latitude: 15.9955, longitude: 108.1288, title: "Tuy Loan Bio-Protection Post", description: "RH 88% triggers Pyricularia oryzae fungal warning alert", temperature_c: 29.0, weather_condition: "Fungal Watch" }
      ]
    },
    insights: [
      {
        title: "FAO-56 Evapotranspiration Analysis (ETo)",
        body: "Forecast ETo of 3.6 mm/day with crop coefficient Kc = 1.05 indicates 46mm rainfall fully sustains crop water requirements for 9-10 days.",
        type: "rain"
      },
      {
        title: "Root Zone Soil Moisture Balance (0-30cm)",
        body: "Soil moisture expected to reach Field Capacity (88%) without causing anaerobic root stress.",
        type: "general"
      },
      {
        title: "Fungal Disease Micro-Climate Risk",
        body: "Mean relative humidity of 86% activates Stage 2 early warning for rice blast fungus (Pyricularia oryzae).",
        type: "general"
      }
    ]
  };

  return {
    session_id: "demo-session-agriculture",
    status: "success",
    response_type: "weather_prediction",
    domain: "agriculture",
    location: "Hoa Vang Agricultural Zone, Da Nang",
    prediction: "Widespread beneficial rainfall with 46mm cumulative accumulation over the next 48 hours in Da Nang, followed by warm, sunny conditions (31-33°C) starting Thursday.",
    recommendation: "Pause artificial irrigation for 2 days (Sep 8-9) to save energy and water. Hold fertilizer application and schedule preventive blast fungus treatment for Thursday morning, Sep 10.",
    risk_assessment: {
      rain_risk: "High",
      wind_risk: "Low",
      heat_risk: "Low",
      overall_risk: "Medium",
      disease_risk: "Medium"
    },
    weather_stats: {
      avg_temperature_c: 28.4,
      min_temperature_c: 23.8,
      max_temp: 33.0,
      max_rain_prob: 80,
      max_wind_speed: 15.0,
      total_rainfall_mm: 46.0
    },
    time_range: {
      start: "2026-09-08",
      end: "2026-09-14",
      raw_text: "Next 7 Days Farming Advisory"
    },
    weather_path: "Path-A (FAO-56 Penman-Monteith Evapotranspiration Agent)",
    weather_confidence: 0.95,
    weather_mode: "standard_multi_agent",
    sources_used: ["FAO-56 Irrigation Model", "ERA5 Agrometeorological Reanalysis", "Vietnam National Agricultural Extension Portal"],
    tech_stack_info,
    weather_view,
    coordinates: { latitude: 15.9866, longitude: 108.1511 }
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// 4. SEVERE WEATHER / ALERTS MOCK DATA
// ─────────────────────────────────────────────────────────────────────────────
export function getSevereWeatherMockResponse(query: string): ChatResult {
  const tech_stack_info: TechStackInfo = {
    reasoning_model: "DeepSeek-R1-Distill-Llama-70B (NVIDIA NIM CoT)",
    domain_agent: "Severe Hydro-Meteorological Hazard & Typhoon Tracking Agent",
    weather_sources: ["JMA Himawari-9 Satellite IR/Water Vapor", "SWAN Coastal Wave Model", "NCHMF Radar Integration"],
    vector_db: "Qdrant Vector DB (Emergency Disaster Contingency SOPs)",
    guardrails_score: "99.8% Safety Verification Passed",
    latency: "1.15s",
    tokens_per_sec: "47.6 tok/s"
  };

  const domain_metrics: DomainMetricItem[] = [
    { label: "Atmospheric Barometric Pressure", value: "1008.2 hPa", source: "WMO Station 48855 (Da Nang)", sub: "Barometric trend stable" },
    { label: "Significant Wave Height (Hs)", value: "1.2 - 1.8 m", source: "SWAN Coastal Wave Model", sub: "Calm to moderate nearshore" },
    { label: "Himawari Satellite Tracking", value: "Band 8 IR", source: "JMA Himawari-9 Geostationary", sub: "Tropical trough at 14°N axis" },
    { label: "Disaster Risk Level", value: "Level 1 (Yellow)", source: "National Disaster Committee", sub: "Advisory for offshore fleets" },
    { label: "Offshore Wind Gust", value: "42.0 km/h", source: "ECMWF Marine Surface Wind", sub: "Beaufort Scale 6 in open sea" },
    { label: "Marine Visibility Range", value: "> 10 km", source: "Coastal Navigational Sensor", sub: "Drops to 4-6km during showers" },
    { label: "Urban Inundation Probability", value: "< 15%", source: "Da Nang Hydrodynamic Model", sub: "Han River drainage operational" },
    { label: "Emergency Readiness", value: "24/7 Active Watch", source: "Central Forecast Center", sub: "Automated alert monitoring" },
  ];

  const overview: DomainOverviewData = {
    title: "Coastal Early Warning & Meteorological Hazard Overview",
    subtitle: "Hydro-meteorological risk evaluation for Da Nang Coastal Zone & Son Tra",
    executive_summary: "Monitoring tropical low-pressure trough in the central South China Sea. Satellite tracking confirms no direct typhoon formation or landfall for Da Nang over the next 5-7 days. Nearshore tourism and city activities proceed normally; offshore fishing vessels are advised of Force 6 winds in open waters.",
    compliance_status: "NORMAL COASTAL OPERATIONS · MARITIME ADVISORY",
    hazards: [
      {
        title: "Offshore Wave & Wind Surge",
        standard_code: "Maritime Safety Authority Standard",
        status: "Advisory Level",
        threshold_limit: "Wave height Hs < 2.0m for small craft",
        observed_value: "Hs 1.2 - 1.8m nearshore / 2.5m offshore",
        impact_description: "Small leisure boats should avoid deep-sea night sailing; nearshore swimming zones remain safe.",
        severity: "medium"
      },
      {
        title: "Urban Drainage & Runoff Capacity",
        standard_code: "Urban Flood Control Regulation",
        status: "Low Inundation Risk",
        threshold_limit: "Rainfall < 50mm/2h threshold",
        observed_value: "16-20mm localized afternoon showers",
        impact_description: "Han River tidal sluice gates and municipal drainage pumps maintain adequate discharge capacity.",
        severity: "low"
      }
    ],
    operational_protocols: [
      "Maintain 24/7 radio contact with Son Tra Maritime Station on VHF Channel 16.",
      "Beach safety lifeguards active across My Khe, Non Nuoc, and Pham Van Dong beaches.",
      "Monitor daily 06:00 and 18:00 bulletin updates from NCHMF Da Nang Station."
    ]
  };

  const weather_view: WeatherPredictionView = {
    title: "Severe Weather & Coastal Early Warning System — Da Nang",
    location: {
      name: "Da Nang Coastal Waters & Son Tra Peninsula",
      latitude: 16.0544,
      longitude: 108.2022
    },
    date_range: {
      start: "2026-09-08",
      end: "2026-09-14",
      label: "7-Day Coastal Alert Horizon"
    },
    assumption: {
      summary: "Monitoring tropical low-pressure trough in the central South China Sea. No direct typhoon landfall is forecast for the Da Nang mainland over the next 5 days.",
      should_go: true,
      decision_category: "DISASTER MONITORING & OCEANOGRAPHY",
      decision_label: "MAINLAND SAFE - CAUTION FOR OFFSHORE VESSELS",
      key_stat_badge: "120H HORIZON",
      key_stat_value: "No Direct Typhoon Landfall",
      reason: "Mainland operations remain normal with brief evening showers; offshore waters experience Force 6-7 wind gusts and 2.0 - 3.0m wave heights."
    },
    statistics: {
      avg_temperature_c: 30.5,
      min_temperature_c: 25.0,
      max_temperature_c: 34.0,
      avg_wind_kmh: 22.0,
      total_rainfall_mm: 36.0,
      rain_risk: "Medium",
      wind_risk: "Medium",
      heat_risk: "Medium",
      overall_risk: "Medium",
      most_common_condition: "Afternoon Convective Storms"
    },
    domain_metrics,
    tech_stack_info,
    overview,
    daily_forecast: [
      { date: "2026-09-08", day_label: "Tuesday", condition: "Thunderstorms", condition_icon: "cloud-lightning", max_temp_c: 33.5, min_temp_c: 25.5, wind_kmh: 28, rain_probability: 65, rain_mm: 16, risk: "Medium" },
      { date: "2026-09-09", day_label: "Wednesday", condition: "Partly Cloudy", condition_icon: "cloud-sun", max_temp_c: 32.0, min_temp_c: 25.0, wind_kmh: 22, rain_probability: 30, rain_mm: 4, risk: "Low" },
      { date: "2026-09-10", day_label: "Thursday", condition: "Sunny", condition_icon: "sun", max_temp_c: 33.0, min_temp_c: 25.5, wind_kmh: 16, rain_probability: 15, rain_mm: 0, risk: "Low" },
      { date: "2026-09-11", day_label: "Friday", condition: "Sunny", condition_icon: "sun", max_temp_c: 34.0, min_temp_c: 26.0, wind_kmh: 18, rain_probability: 10, rain_mm: 0, risk: "Low" },
      { date: "2026-09-12", day_label: "Saturday", condition: "Cloudy", condition_icon: "cloud", max_temp_c: 32.0, min_temp_c: 24.8, wind_kmh: 24, rain_probability: 40, rain_mm: 6, risk: "Low" },
      { date: "2026-09-13", day_label: "Sunday", condition: "Showers", condition_icon: "cloud-rain", max_temp_c: 30.5, min_temp_c: 24.2, wind_kmh: 26, rain_probability: 55, rain_mm: 10, risk: "Medium" },
      { date: "2026-09-14", day_label: "Monday", condition: "Partly Cloudy", condition_icon: "cloud-sun", max_temp_c: 31.5, min_temp_c: 25.0, wind_kmh: 18, rain_probability: 20, rain_mm: 0, risk: "Low" }
    ],
    recommendations: [
      "Offshore Fishing & Commercial Fleets: Maintain routine communications with regional maritime safety stations.",
      "Coastal Tourism & Cable Cars: Operations proceed normally during daylight; avoid late-night beach activities during squalls.",
      "Urban Structural Maintenance: Inspect billboards and roadside trees ahead of seasonal storm transition."
    ],
    alternatives: [
      {
        name: "Da Nang City Center Indoor Attractions",
        description: "Museum of Cham Sculpture, Dragon Bridge promenade, Han Market, and Vincom Center remain fully sheltered.",
        distance_label: "Sheltered Zone"
      }
    ],
    map: {
      center: { name: "Da Nang - Son Tra Coastal Waters", latitude: 16.0544, longitude: 108.2022 },
      markers: [
        { id: "alert-1", label: "📡 Radar 48855", latitude: 16.1200, longitude: 108.2800, title: "Son Tra WMO Doppler Radar", description: "Himawari-9 satellite & radar surveillance active 24/7", temperature_c: 29.0, weather_condition: "Monitoring Axis" },
        { id: "alert-2", label: "⚓ Maritime Berth", latitude: 16.1286, longitude: 108.2215, title: "Tien Sa Seaport & Fleet Berth", description: "Force 4-5 winds, 1.2m waves - Maritime advisory broadcast", temperature_c: 30.0, weather_condition: "Sea Breeze" },
        { id: "alert-3", label: "🏖️ My Khe Sentry", latitude: 16.0580, longitude: 108.2480, title: "My Khe Coastal Lifeguard Post", description: "Wave height 1.2 - 1.6m, nearshore swimming safe with flags", temperature_c: 31.0, weather_condition: "Normal Coastal" }
      ]
    },
    insights: [
      {
        title: "South China Sea Trough Tracking",
        body: "Himawari-9 satellite infrared imagery indicates the 12-15°N trough is tracking slowly westward with no intensification into a tropical depression within 120 hours.",
        type: "wind"
      },
      {
        title: "Nearshore Wave Forecasting (SWAN Model)",
        body: "Significant wave height (Hs) at My Khe Beach ranges between 0.8 - 1.4m, supporting water recreational activities during daytime.",
        type: "general"
      }
    ]
  };

  return {
    session_id: "demo-session-severe-alert",
    status: "success",
    response_type: "weather_prediction",
    domain: "severe_weather",
    location: "Da Nang Coastal Waters & Son Tra Peninsula",
    prediction: "No direct storm impact on Da Nang mainland over the next 5-7 days. Stable daytime weather with brief evening showers.",
    recommendation: "Tourism, industrial, and construction operations proceed normally. Offshore vessels maintain scheduled maritime VHF watch.",
    risk_assessment: {
      rain_risk: "Medium",
      wind_risk: "Medium",
      heat_risk: "Medium",
      overall_risk: "Medium"
    },
    weather_stats: {
      avg_temperature_c: 30.5,
      min_temperature_c: 25.0,
      max_temp: 34.0,
      max_rain_prob: 65,
      max_wind_speed: 28.0,
      total_rainfall_mm: 36.0
    },
    time_range: {
      start: "2026-09-08",
      end: "2026-09-14",
      raw_text: "7-Day Coastal Horizon"
    },
    weather_path: "Path-A (High-Resolution NWP & Himawari Satellite Tracking)",
    weather_confidence: 0.97,
    weather_mode: "standard_multi_agent",
    sources_used: ["National Center for Hydro-Meteorological Forecasting (NCHMF)", "JMA Himawari-9 Satellite", "ECMWF Coastal Wave Model"],
    tech_stack_info,
    weather_view,
    coordinates: { latitude: 16.0544, longitude: 108.2022 }
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// 5. SMART QUERY ROUTER
// ─────────────────────────────────────────────────────────────────────────────
export function routeMockQuery(query: string): ChatResult {
  const q = (query || "").toLowerCase();

  // 1. Construction / Concrete / Crane / Safety
  if (
    q.includes("construct") ||
    q.includes("xây dựng") ||
    q.includes("bê tông") ||
    q.includes("concrete") ||
    q.includes("cẩu") ||
    q.includes("crane") ||
    q.includes("công trường") ||
    q.includes("giàn giáo") ||
    q.includes("đổ bê tông") ||
    q.includes("pour") ||
    q.includes("curing") ||
    q.includes("scaffold")
  ) {
    return getConstructionMockResponse(query);
  }

  // 2. Agriculture / Irrigation / Farming / Crops
  if (
    q.includes("agri") ||
    q.includes("nông nghiệp") ||
    q.includes("irrigate") ||
    q.includes("tưới") ||
    q.includes("lúa") ||
    q.includes("farm") ||
    q.includes("ruộng") ||
    q.includes("hòa vang") ||
    q.includes("hoa vang") ||
    q.includes("bón phân") ||
    q.includes("đạo ôn") ||
    q.includes("crop") ||
    q.includes("harvest") ||
    q.includes("evapotranspiration") ||
    q.includes("fertilizer")
  ) {
    return getAgricultureMockResponse(query);
  }

  // 3. Severe weather / Storm / Typhoon / Alert
  if (
    q.includes("storm") ||
    q.includes("bão") ||
    q.includes("severe") ||
    q.includes("typhoon") ||
    q.includes("alert") ||
    q.includes("cảnh báo") ||
    q.includes("lốc") ||
    q.includes("ngập") ||
    q.includes("lũ") ||
    q.includes("warning") ||
    q.includes("disaster") ||
    q.includes("wave")
  ) {
    return getSevereWeatherMockResponse(query);
  }

  // 4. Tourism / Travel / Itinerary / Trip
  if (
    q.includes("trip") ||
    q.includes("tour") ||
    q.includes("du lịch") ||
    q.includes("hành trình") ||
    q.includes("chơi") ||
    q.includes("lịch trình") ||
    q.includes("hội an") ||
    q.includes("sơn trà") ||
    q.includes("bà nà") ||
    q.includes("my khe") ||
    q.includes("mỹ khê") ||
    q.includes("itinerary") ||
    q.includes("plan") ||
    q.includes("visit") ||
    q.includes("beach") ||
    q.includes("hotel")
  ) {
    return getTourismMockResponse(query);
  }

  // Default fallback: Tourism Da Nang demo
  return getTourismMockResponse(query);
}

