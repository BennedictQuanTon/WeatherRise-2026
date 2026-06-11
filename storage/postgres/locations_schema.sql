-- Weatherise V3 — Locations Schema
-- Requires: postgis/postgis:16-3.4 image

CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pg_trgm; -- For fuzzy text search

-- ── Main locations table (Attractions + Restaurants unified) ──
CREATE TABLE IF NOT EXISTS locations (
    id VARCHAR(100) PRIMARY KEY,
    source VARCHAR(30) NOT NULL DEFAULT 'manual',
    -- 'foody_csv' | 'osm_attraction' | 'manual_seed' | 'mcp_cache'

    name_vi VARCHAR(200) NOT NULL,
    name_en VARCHAR(200),
    category VARCHAR(50) NOT NULL,
    -- 'attraction' | 'restaurant' | 'cafe' | 'entertainment' | 'market'
    sub_category VARCHAR(80),
    -- 'seafood' | 'beach' | 'museum' | 'street_food' | 'viewpoint' etc.

    address TEXT,
    district VARCHAR(80),
    city VARCHAR(80) DEFAULT 'Da Nang',
    country VARCHAR(50) DEFAULT 'Vietnam',

    -- Spatial
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    coordinate GEOGRAPHY(Point, 4326),

    -- Quality signals
    avg_rating DECIMAL(3, 2) DEFAULT 0.0,
    total_reviews INT DEFAULT 0,
    price_tier VARCHAR(10) DEFAULT 'medium',
    -- 'budget' | 'medium' | 'premium'

    -- Planning metadata
    avg_duration_minutes INT DEFAULT 60,
    opening_hours JSONB DEFAULT '{}',
    -- {"open": "08:00", "close": "22:00", "days": "Mon-Sun"}
    best_visit_times VARCHAR(20)[] DEFAULT '{}',
    -- {'morning','afternoon','evening','sunset','anytime'}
    vibe_tags VARCHAR(60)[] DEFAULT '{}',
    -- {'romantic','chill','family_friendly','photo_spot','street_food'}

    -- Weather intelligence (Weatherise core)
    is_indoor BOOLEAN DEFAULT FALSE,
    rain_sensitive BOOLEAN DEFAULT TRUE,
    uv_sensitive BOOLEAN DEFAULT FALSE,
    bad_weather_rules JSONB DEFAULT '{}',
    -- {"max_wind_kmh": 30, "max_precipitation_mm": 1.5, "max_rain_prob_pct": 60}
    safe_alternatives VARCHAR(100)[] DEFAULT '{}',
    -- Array of location IDs to suggest when weather is bad

    -- Foody-specific (nullable for non-restaurant)
    phone VARCHAR(30),
    is_opening BOOLEAN DEFAULT TRUE,
    has_delivery BOOLEAN DEFAULT FALSE,
    has_booking BOOLEAN DEFAULT FALSE,
    photo_url TEXT,
    foody_url TEXT,

    -- System fields
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Spatial index (for ST_DWithin distance queries)
CREATE INDEX IF NOT EXISTS idx_locations_coordinate
    ON locations USING GIST (coordinate);

-- Category + city index (for filtered lookups)
CREATE INDEX IF NOT EXISTS idx_locations_category_city
    ON locations (category, city);

-- Trigram index for Vietnamese fuzzy text search
CREATE INDEX IF NOT EXISTS idx_locations_name_trgm
    ON locations USING GIN (name_vi gin_trgm_ops);

-- Source index
CREATE INDEX IF NOT EXISTS idx_locations_source
    ON locations (source);

-- Auto-update coordinate from lat/lon on insert/update
CREATE OR REPLACE FUNCTION sync_coordinate()
RETURNS TRIGGER AS $$
BEGIN
    NEW.coordinate = ST_SetSRID(ST_MakePoint(NEW.longitude, NEW.latitude), 4326)::GEOGRAPHY;
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_sync_coordinate ON locations;
CREATE TRIGGER trg_sync_coordinate
    BEFORE INSERT OR UPDATE OF latitude, longitude
    ON locations
    FOR EACH ROW EXECUTE FUNCTION sync_coordinate();

-- ── Trip plans cache table ──────────────────────────────────
CREATE TABLE IF NOT EXISTS trip_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id VARCHAR(100) NOT NULL,
    raw_user_input TEXT,
    location VARCHAR(100),
    duration_days INT,
    trip_plan_json JSONB NOT NULL,
    -- Full V3 trip_plan_context
    weather_snapshot JSONB DEFAULT '{}',
    context_quality VARCHAR(30),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_trip_plans_session
    ON trip_plans (session_id, created_at DESC);

-- ── MCP cache table (avoid repeated external calls) ─────────
CREATE TABLE IF NOT EXISTS mcp_cache (
    id SERIAL PRIMARY KEY,
    route VARCHAR(100) NOT NULL,
    cache_key VARCHAR(255) NOT NULL UNIQUE,
    response_json JSONB NOT NULL,
    source_provider VARCHAR(80),
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_mcp_cache_key
    ON mcp_cache (cache_key, expires_at);

-- ── Pipeline observability ───────────────────────────────────
CREATE TABLE IF NOT EXISTS pipeline_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id VARCHAR(100),
    raw_input TEXT,
    parsed_domain VARCHAR(50),
    parsed_intent VARCHAR(100),
    intent_subtype VARCHAR(100),
    context_quality VARCHAR(30),
    mcp_routes_called TEXT[],
    total_duration_ms INT,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pipeline_runs_session
    ON pipeline_runs (session_id, created_at DESC);
-- ===========================================================================
-- V3 Context Observability Tables
-- Migration: storage/postgres/context_observability_tables.sql
-- Run: psql $POSTGRES_URL -f this_file.sql
-- ===========================================================================

-- Context Gap Reports: what was requested vs found in KB per session
CREATE TABLE IF NOT EXISTS context_gap_reports (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id      TEXT NOT NULL,
    domain          TEXT NOT NULL,
    location        TEXT,
    required_context TEXT[],
    found_context   JSONB DEFAULT '{}',
    missing_context JSONB DEFAULT '[]',
    is_complete     BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_gap_reports_session ON context_gap_reports (session_id);
CREATE INDEX IF NOT EXISTS idx_gap_reports_domain  ON context_gap_reports (domain, created_at DESC);

-- MCP Route Calls: log every external API call with timing and status
CREATE TABLE IF NOT EXISTS mcp_route_calls (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id  TEXT NOT NULL,
    route       TEXT NOT NULL,           -- e.g. "place.searchPlaces"
    source      TEXT,                    -- e.g. "qdrant_kb", "osm_live", "mock_seed"
    status      TEXT NOT NULL,           -- "success" | "partial" | "error"
    duration_ms INT,
    input_json  JSONB,
    output_summary TEXT,                 -- short preview, not full payload
    warnings    TEXT[],
    errors      TEXT[],
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_mcp_calls_session ON mcp_route_calls (session_id);
CREATE INDEX IF NOT EXISTS idx_mcp_calls_route   ON mcp_route_calls (route, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_mcp_calls_source  ON mcp_route_calls (source);

-- Context Assembly Runs: final quality assessment per pipeline execution
CREATE TABLE IF NOT EXISTS context_assembly_runs (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id          TEXT NOT NULL,
    domain              TEXT NOT NULL,
    location            TEXT,
    intent_subtype      TEXT,
    context_quality     TEXT NOT NULL,   -- "complete"|"usable_for_trip_planning"|"partial"|"blocked"
    is_valid            BOOLEAN,
    kb_complete         BOOLEAN DEFAULT FALSE,
    has_trip_plan       BOOLEAN DEFAULT FALSE,
    has_forecast        BOOLEAN DEFAULT FALSE,
    missing_critical    TEXT[],
    warnings            TEXT[],
    mcp_routes_called   TEXT[],
    total_duration_ms   INT,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_assembly_session ON context_assembly_runs (session_id);
CREATE INDEX IF NOT EXISTS idx_assembly_quality ON context_assembly_runs (context_quality, created_at DESC);

-- KB Enrichment Log: track when new places get ingested into Qdrant from live fetch
CREATE TABLE IF NOT EXISTS kb_enrichment_log (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trigger_session TEXT,
    domain          TEXT NOT NULL,
    source          TEXT NOT NULL,       -- "osm_live" | "google_places"
    location        TEXT,
    lat             FLOAT,
    lon             FLOAT,
    places_count    INT DEFAULT 0,
    qdrant_ok       BOOLEAN DEFAULT FALSE,
    postgres_ok     BOOLEAN DEFAULT FALSE,
    error_msg       TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_enrichment_source ON kb_enrichment_log (source, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_enrichment_domain ON kb_enrichment_log (domain);

-- MCP Cache: HTTP-level cache for Overpass/external API responses (TTL-based)
-- (May already exist — CREATE IF NOT EXISTS is safe)
CREATE TABLE IF NOT EXISTS mcp_cache (
    cache_key   TEXT PRIMARY KEY,
    data        JSONB NOT NULL,
    domain      TEXT,
    source      TEXT,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    expires_at  TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_mcp_cache_expires ON mcp_cache (expires_at);
CREATE INDEX IF NOT EXISTS idx_mcp_cache_domain  ON mcp_cache (domain);

-- Auto-clean expired cache entries (run via pg_cron or periodic job)
-- SELECT delete FROM mcp_cache WHERE expires_at < NOW();

-- Trip Plans: persisted trip plans per session (for map-data endpoint)
-- (May already exist)
CREATE TABLE IF NOT EXISTS trip_plans (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id      TEXT NOT NULL,
    location        TEXT,
    duration_days   INT,
    weather_aware   BOOLEAN DEFAULT TRUE,
    trip_plan_json  JSONB NOT NULL,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_trip_plans_session ON trip_plans (session_id, created_at DESC);
