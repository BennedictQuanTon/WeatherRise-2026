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
