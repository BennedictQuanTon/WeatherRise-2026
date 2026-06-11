# Path B Implementation Summary

## Overview

Path B is now implemented as the main weather intelligence engine inside the Weatherise Intelligence Layer.

The old Open-Meteo-only weather flow is no longer the primary design. Open-Meteo is now one provider inside the new multi-source Path B pipeline.

Current architecture:

```text
Parser
-> Orchestrator
-> Context Agent
-> IntelligenceService
-> PathBWeatherService
-> Weather Source Planner
-> Parallel Multi-Source Weather Fetcher
-> Raw Saver / Bronze Layer
-> Source-Specific Normalizers
-> Quality Validator
-> Source Scorer
-> Source Comparison Matrix
-> Weather Fusion Engine
-> NIM Weather Arbiter Brain
-> Gold Weather Decision
-> Prediction Engine
-> NIM Prompt Builder
-> NIM Final Reasoning
-> Response Builder
-> API / Frontend Response
```

## New Package

Path B lives at:

```text
agents/intelligence_layer/weather_path_b/
```

New file structure:

```text
agents/intelligence_layer/weather_path_b/
├── __init__.py
├── schemas.py
├── weather_requirement_reader.py
├── weather_source_planner.py
├── multi_source_weather_fetcher.py
├── clients.py
├── evidence_store.py
├── normalizers.py
├── quality_validator.py
├── source_scorer.py
├── comparison_matrix.py
├── fusion_engine.py
├── nim_weather_arbiter.py
├── gold_weather_decision.py
├── earth2_processing.py
├── rag_hooks.py
└── config/
    ├── __init__.py
    ├── source_registry.py
    └── weather_sources.yaml
```

## Core Contracts

Defined in:

```text
agents/intelligence_layer/weather_path_b/schemas.py
```

Main contracts:

```text
WeatherRequirement
WeatherSourcePlan
RawWeatherResponse
StandardWeatherRecord
QualityReport
SourceScore
SourceComparisonMatrix
FusedWeather
Earth2ProcessingReport
ArbiterDecision
GoldWeatherDecision
PathBRunArtifacts
```

Purpose:

- `WeatherRequirement`: request-level weather need extracted from context-agent payload.
- `WeatherSourcePlan`: selected and skipped providers.
- `RawWeatherResponse`: raw provider response or failure record.
- `StandardWeatherRecord`: normalized provider weather record.
- `QualityReport`: validation result per source.
- `SourceScore`: source ranking output.
- `SourceComparisonMatrix`: cross-provider disagreement report.
- `FusedWeather`: weighted fused weather result.
- `Earth2ProcessingReport`: guarded Earth2Studio alignment/model-readiness report.
- `ArbiterDecision`: NIM Weather Arbiter decision.
- `GoldWeatherDecision`: final trusted weather package sent to prediction.

## Implemented Pipeline Components

### Weather Requirement Reader

File:

```text
agents/intelligence_layer/weather_path_b/weather_requirement_reader.py
```

Purpose:

- Reads the fully processed payload from the Context Agent.
- Extracts domain, intent, coordinates, time range, location, user constraints, and required weather variables.
- Detects activity type such as beach, mountain, construction site, agriculture field, or outdoor city trip.
- Sets conservative safety mode for safety-sensitive cases.

### Weather Source Planner

File:

```text
agents/intelligence_layer/weather_path_b/weather_source_planner.py
```

Purpose:

- Chooses providers based on domain, activity, API key availability, source capability, and priority.
- Automatically skips keyed providers when the API key is missing.
- Keeps Open-Meteo and 7Timer available as no-key sources.

Supported first provider set:

```text
Open-Meteo
OpenWeatherMap
WeatherAPI
Tomorrow.io
Visual Crossing
7Timer
Stormglass
```

### Source Registry

Files:

```text
agents/intelligence_layer/weather_path_b/config/source_registry.py
agents/intelligence_layer/weather_path_b/config/weather_sources.yaml
```

Purpose:

- Defines provider metadata, priorities, timeouts, API key names, historical skill scores, and resolution scores.
- Python registry is used at runtime so the project does not require a new YAML dependency.
- YAML file documents the intended provider config shape.

### Parallel Multi-Source Weather Fetcher

File:

```text
agents/intelligence_layer/weather_path_b/multi_source_weather_fetcher.py
```

Purpose:

- Calls all selected providers concurrently.
- Each provider failure is isolated.
- A failed provider returns a failed `RawWeatherResponse` instead of crashing Path B.

### Provider Clients

File:

```text
agents/intelligence_layer/weather_path_b/clients.py
```

Implemented clients:

```text
OpenMeteoClient
WeatherAPIClient
TomorrowIOClient
VisualCrossingClient
OpenWeatherMapClient
SevenTimerClient
StormglassClient
```

Purpose:

- Fetch raw weather JSON from provider APIs.
- Return `RawWeatherResponse`.
- Track status, error message, fetched timestamp, and latency.

### Raw Saver / Bronze Layer

File:

```text
agents/intelligence_layer/weather_path_b/evidence_store.py
```

Purpose:

- Saves raw provider evidence.
- Saves normalized records.
- Saves comparison reports.
- Saves fused weather.
- Saves selected Gold Weather Decision.
- Appends metadata to `manifest.jsonl`.

Configured paths:

```env
WEATHER_EVIDENCE_DIR=/raid/team/weatherise/weather_evidence
WEATHER_EVIDENCE_FALLBACK_DIR=data/weather_evidence
```

If `/raid` cannot be written, Path B falls back to local `data/weather_evidence`.

Stored evidence layout:

```text
weather_evidence/
├── raw/<source_code>/
├── normalized/<source_code>/
├── comparison_reports/comparison/
├── fused/fusion/
├── selected/gold_weather_decision/
└── manifest.jsonl
```

### Source-Specific Normalizers

File:

```text
agents/intelligence_layer/weather_path_b/normalizers.py
```

Purpose:

- Converts provider-specific JSON into `StandardWeatherRecord`.
- Normalizes all units into Weatherise standard values.

Unit rules:

```text
rain_probability: 0.0-1.0
temperature: Celsius
wind_speed: km/h
visibility: km
pressure: hPa
```

Implemented normalizers:

```text
OpenMeteoNormalizer
WeatherAPINormalizer
TomorrowIONormalizer
VisualCrossingNormalizer
OpenWeatherMapNormalizer
SevenTimerNormalizer
StormglassNormalizer
```

### Quality Validator

File:

```text
agents/intelligence_layer/weather_path_b/quality_validator.py
```

Purpose:

- Checks missing fields.
- Rejects impossible weather values.
- Checks coordinates and unit ranges.
- Produces `QualityReport`.

Examples of invalid values:

```text
rain_probability > 1
temperature_c > 65
wind_speed_kmh < 0
humidity_percent outside 0-100
latitude outside -90 to 90
longitude outside -180 to 180
```

### Source Scorer

File:

```text
agents/intelligence_layer/weather_path_b/source_scorer.py
```

Purpose:

- Scores each valid source.
- Produces source rankings used by fusion and arbiter.

Scoring factors:

```text
quality_score
completeness_score
freshness_score
domain_relevance_score
latency_score
historical_skill_score
resolution_score
```

### Source Comparison Matrix

File:

```text
agents/intelligence_layer/weather_path_b/comparison_matrix.py
```

Purpose:

- Compares sources for the same request/location/time window.
- Detects major disagreement.

Compared fields:

```text
rain_probability
temperature_c
humidity_percent
precipitation_mm
wind_speed_kmh
wind_gust_kmh
visibility_km
uv_index
wave_height_m
```

Major conflict examples:

```text
rain probability range >= 0.35
temperature range >= 6 C
wind speed range >= 20 km/h
wave height range >= 1.0 m
```

### Weather Fusion Engine

File:

```text
agents/intelligence_layer/weather_path_b/fusion_engine.py
```

Purpose:

- Produces one fused weather package from multiple valid sources.
- Uses source scores as weights.
- Applies conservative logic for safety-sensitive cases.

Conservative fields:

```text
rain_probability
precipitation_mm
wind_speed_kmh
wind_gust_kmh
uv_index
wave_height_m
```

### NIM Weather Arbiter Brain

File:

```text
agents/intelligence_layer/weather_path_b/nim_weather_arbiter.py
```

Purpose:

- Separate NIM role from final user-facing reasoning.
- Receives structured evidence only.
- Selects trusted weather mode.
- Explains source conflict and confidence.

Allowed decision modes:

```text
fused_weather
best_single_source
conservative_risk
latest_snapshot
degraded_open_meteo_only
weather_unavailable
```

Guardrails:

- NIM must not invent weather values.
- NIM must return valid JSON.
- Invalid JSON triggers one retry.
- If retry fails, deterministic fallback is used.

### Gold Weather Decision

File:

```text
agents/intelligence_layer/weather_path_b/gold_weather_decision.py
```

Purpose:

- Builds the final trusted weather decision.
- Converts Gold Weather Decision to existing `CanonicalWeatherData` where needed.
- Preserves Path B confidence, selected mode, sources used, rejected sources, warnings, evidence paths, source scores, quality reports, comparison matrix, fusion output, arbiter decision, and Earth2 report.

Important adapter detail:

- Path B stores `rain_probability` as `0.0-1.0`.
- Existing `PredictionEngine` expects rain probability as percent.
- Adapter converts `0.74` to `74`.

### Earth2Studio Processing Stub

File:

```text
agents/intelligence_layer/weather_path_b/earth2_processing.py
```

Purpose:

- Adds the Earth2Studio processing position in the pipeline.
- Does not make Earth2Studio mandatory.
- If disabled, returns `enabled=false`.
- If enabled but dependency is missing, returns warning and continues.

Config:

```env
EARTH2STUDIO_ENABLED=false
EARTH2_OUTPUT_DIR=/raid/team/weatherise/weather_evidence/earth2_processed
```

### Qdrant / RAG Hooks

File:

```text
agents/intelligence_layer/weather_path_b/rag_hooks.py
```

Purpose:

- Adds read-only hooks for future weather knowledge retrieval.
- Does not store live weather numbers in Qdrant.
- Does not write Qdrant data in this implementation.

Current examples:

- beach safety weather rules
- construction weather interpretation rule

## Main Orchestration

File:

```text
agents/intelligence_layer/weather_path_b/path_b_service.py
```

`PathBWeatherService.run()` performs:

```text
1. Read WeatherRequirement
2. Plan sources
3. Fetch sources in parallel
4. Save raw evidence
5. Normalize records
6. Save normalized evidence
7. Run Earth2 processing stub
8. Validate quality
9. Score sources
10. Build comparison matrix
11. Save comparison report
12. Fuse weather
13. Save fused weather
14. Retrieve weather knowledge hooks
15. Run NIM Weather Arbiter
16. Build Gold Weather Decision
17. Save selected decision
18. Return GoldWeatherDecision
```

## Integration With Existing Intelligence Layer

Modified:

```text
agents/intelligence_layer/intelligence_service.py
agents/intelligence_layer/prediction_engine.py
agents/intelligence_layer/prompt_builder.py
agents/intelligence_layer/response_builder.py
```

### IntelligenceService

Now calls:

```python
gold_weather_decision = await self.path_b_service.run(processed_json)
prediction = self.prediction_engine.predict(processed_json, gold_weather_decision)
messages = self.prompt_builder.build_path_b_prompt(
    processed_json,
    gold_weather_decision,
    prediction,
)
nim_response = await self.nim_client.chat(messages)
return self.response_builder.build(
    prediction,
    nim_response,
    extra_metadata=self._path_b_metadata(gold_weather_decision),
)
```

### PredictionEngine

Now accepts:

```text
CanonicalWeatherData
or
GoldWeatherDecision
```

If given a Gold Weather Decision, it adapts it into canonical weather before deterministic scoring.

### PromptBuilder

Added:

```text
build_path_b_prompt()
```

The final NIM prompt now receives:

```text
Gold Weather Decision
weather confidence
sources used
source conflicts
PredictionEngine deterministic risk result
user constraints
knowledge context
```

### ResponseBuilder

Now accepts optional `extra_metadata`.

Path B metadata is attached to final `IntelligenceOutput.metadata`.

## API Changes

Modified:

```text
apps/api/app/schemas/response_schema.py
apps/api/app/services/pipeline_service.py
apps/api/app/routes/chat.py
apps/api/app/config.py
```

Added optional response fields:

```text
weather_path
weather_confidence
weather_mode
sources_used
sources_rejected
weather_debug
```

Existing response fields remain compatible:

```text
prediction
recommendation
risk_assessment
explanation
final_answer
trip_plan
coordinates
evidence
weather_stats
time_range
```

## Frontend Changes

Modified:

```text
apps/web/app/page.tsx
```

Added:

```text
WeatherDebug interface
Path B response fields on ChatResult
PathBDebugPanel component
DebugMetric component
formatConfidence helper
```

The debug panel appears only when:

```text
latestResult.weather_debug exists
```

It shows:

```text
selected mode
confidence
sources used
source scores
quality reports
warnings
```

## Config Additions

Modified:

```text
.env.example
.env.dev
apps/api/app/config.py
```

Added:

```env
WEATHER_EVIDENCE_DIR=/raid/team/weatherise/weather_evidence
WEATHER_EVIDENCE_FALLBACK_DIR=data/weather_evidence
NIM_WEATHER_ARBITER_ENABLED=true
NIM_WEATHER_ARBITER_MODEL=
EARTH2STUDIO_ENABLED=false
EARTH2_OUTPUT_DIR=/raid/team/weatherise/weather_evidence/earth2_processed

WEATHERAPI_KEY=
TOMORROW_IO_API_KEY=
VISUAL_CROSSING_API_KEY=
WEATHERBIT_API_KEY=
METEOSOURCE_API_KEY=
STORMGLASS_API_KEY=
ACCUWEATHER_API_KEY=
```

## Tests Added

Test path:

```text
tests/intelligence_layer/weather_path_b/
```

Files:

```text
tests/intelligence_layer/weather_path_b/test_path_b_pipeline.py
tests/intelligence_layer/weather_path_b/fixtures/open_meteo_danang.json
tests/intelligence_layer/weather_path_b/fixtures/openweathermap_danang.json
tests/intelligence_layer/weather_path_b/fixtures/weatherapi_danang.json
tests/intelligence_layer/weather_path_b/fixtures/tomorrow_io_danang.json
tests/intelligence_layer/weather_path_b/fixtures/visual_crossing_danang.json
tests/intelligence_layer/weather_path_b/fixtures/seven_timer_danang.json
tests/intelligence_layer/weather_path_b/fixtures/stormglass_danang_beach.json
```

Test coverage:

```text
source planner selection
missing API key skip
normalizer unit conversion
quality rejection
Path B end-to-end with fixture clients
bronze saver output
Gold Weather Decision to canonical adapter
arbiter invalid JSON deterministic fallback
API metadata schema compatibility
```

## Verification Run

Passed:

```bash
python3 -m compileall agents/intelligence_layer apps/api/app tests/intelligence_layer/weather_path_b
python3 -m pytest tests/intelligence_layer/weather_path_b -q
./node_modules/.bin/tsc --noEmit --incremental false
git diff --check
```

Result:

```text
6 Path B tests passed
Python compile passed
Frontend type-check passed
Diff check passed
```

Note:

```text
npm run lint could not run because Next prompts to create an ESLint config.
```

## Shared-System Safety

No changes were made to:

```text
Docker
Nginx
Redis writes
Postgres migrations
Qdrant writes
Parser endpoint/model
NIM base endpoint/model
shared container names
shared Docker volumes
```

Path B can increase:

```text
external weather API calls
NIM calls when NIM_WEATHER_ARBITER_ENABLED=true
evidence file writes under WEATHER_EVIDENCE_DIR
```

## Current Operational Behavior

For a normal request:

```text
1. Parser extracts domain/intent/location/time.
2. Orchestrator sends to the correct Context Agent.
3. Context Agent builds FullyProcessedPayload.
4. IntelligenceService calls PathBWeatherService.
5. Path B chooses sources.
6. Path B fetches multiple sources in parallel.
7. Raw responses are saved.
8. Provider responses are normalized.
9. Bad records are rejected.
10. Valid sources are scored.
11. Source disagreements are measured.
12. Weather is fused.
13. NIM Weather Arbiter selects/explains the trusted weather decision.
14. Gold Weather Decision is created.
15. PredictionEngine scores deterministic domain risk.
16. Final NIM produces user-facing language.
17. ResponseBuilder returns final JSON.
18. API sends response.
19. Frontend displays normal result plus Path B debug panel if present.
```

## What Is Still Future Work

Not implemented in this step:

```text
Postgres Path B evidence tables
Redis Path B cache/quota keys
Qdrant writes for weather knowledge
Earth2Studio model inference
FourCastNet/CorrDiff execution
Docker/Nginx production deployment changes
provider quota management
source health dashboards
```

These are intentionally left as future explicit infrastructure steps.
