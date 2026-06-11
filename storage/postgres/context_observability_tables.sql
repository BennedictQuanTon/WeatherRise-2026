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
