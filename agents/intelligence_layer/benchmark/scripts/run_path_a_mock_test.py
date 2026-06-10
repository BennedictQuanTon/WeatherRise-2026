#!/usr/bin/env python3
"""
Weatherise Path A benchmark runner.

─────────────────────────────────────────────────────────────
MODEL SELECTION
─────────────────────────────────────────────────────────────
  --model env        (DEFAULT) Auto-reads NIM_LLM_BASE_URL and NIM_LLM_MODEL
                     directly from the repo-root .env file. Change the model
                     there and just re-run — no yaml editing needed.

  --model <key>      Use a named entry from config/nim_models.yaml.
                     e.g. --model nemotron_nano_8b

─────────────────────────────────────────────────────────────
WEATHER SOURCE
─────────────────────────────────────────────────────────────
  (default)  Load frozen canonical weather JSON from mock_data/.
             Results are 100% reproducible across runs.

  --live     Fetch real hourly weather from Open-Meteo right now.
             Results will reflect actual current conditions.
             Falls back to mock file if Open-Meteo is unreachable.

─────────────────────────────────────────────────────────────
NIM CALL
─────────────────────────────────────────────────────────────
  (default)  Call the NIM LLM endpoint. Requires NIM container running.

  --dry-run  Skip NIM. Use prediction engine text as the final answer.
             No GPU, no NIM container needed. Good for testing the pipeline.

─────────────────────────────────────────────────────────────
ALL 4 COMBINATIONS
─────────────────────────────────────────────────────────────
  Mock + NIM (reproducible benchmark):
    python3 scripts/run_path_a_mock_test.py \\
      --case benchmark_cases/path_a_cases.json

  Mock + no NIM (fast smoke-test, zero dependencies):
    python3 scripts/run_path_a_mock_test.py \\
      --case benchmark_cases/path_a_cases.json --dry-run

  Live weather + NIM (full end-to-end test):
    python3 scripts/run_path_a_mock_test.py \\
      --case benchmark_cases/path_a_cases.json --live

  Live weather + no NIM (test Open-Meteo fetch only):
    python3 scripts/run_path_a_mock_test.py \\
      --case benchmark_cases/path_a_cases.json --live --dry-run

  Override model from yaml (instead of .env):
    python3 scripts/run_path_a_mock_test.py \\
      --case benchmark_cases/path_a_cases.json --model nemotron_nano_8b

Dependencies:
  pip install openai pyyaml httpx
"""

import argparse
import asyncio
import csv
import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
import yaml

# Use openai for NIM calls (matching intelligence layer's nim_client.py)
from openai import AsyncOpenAI


# ── Path resolution ──────────────────────────────────────────

BENCHMARK_ROOT = Path(__file__).resolve().parents[1]  # benchmark/
LAYER_ROOT = BENCHMARK_ROOT.parent                     # intelligence_layer/
REPO_ROOT = LAYER_ROOT.parents[1]                      # WeatherRise-2026/


# ── .env auto-loader (no python-dotenv dependency) ───────────

def _load_dotenv(env_path: Path) -> None:
    """
    Parse key=value pairs from a .env file and set them in os.environ.
    - Skips blank lines and comment lines (starting with #)
    - Does NOT override vars already set in the shell environment
    - Strips surrounding quotes from values
    """
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        # Never overwrite shell-level env vars — they take priority
        if key and key not in os.environ:
            os.environ[key] = value


# Load .env as early as possible so NIM_LLM_* vars are available
_load_dotenv(REPO_ROOT / ".env")


# ── Model config resolver ─────────────────────────────────────

def resolve_model_config(model_key: str, registry: dict) -> dict:
    """
    Resolve model configuration from either:
      - 'env'  → read NIM_LLM_BASE_URL and NIM_LLM_MODEL from environment
      - <key>  → look up in nim_models.yaml registry

    Raises SystemExit with helpful message if the key is not found.
    """
    if model_key == "env":
        base_url = os.environ.get("NIM_LLM_BASE_URL", "http://localhost:8001/v1")
        model = os.environ.get("NIM_LLM_MODEL", "nvidia/llama-3.1-nemotron-nano-8b-v1")
        print(f"[config] Using model from .env: {model} @ {base_url}")
        return {
            "display_name": f"{model} (from .env)",
            "provider": "nvidia_nim",
            "base_url": base_url,
            "model": model,
            "temperature": 0.2,
            "max_tokens": 2048,
            "timeout_seconds": 60,
            "enabled": True,
        }

    models = registry.get("models", {})
    if model_key not in models:
        available = ["env"] + list(models.keys())
        raise SystemExit(
            f"Unknown model key: '{model_key}'.\n"
            f"Available keys: {available}\n"
            f"  'env'  → reads NIM_LLM_BASE_URL + NIM_LLM_MODEL from .env\n"
            f"  others → entries in config/nim_models.yaml"
        )
    cfg = models[model_key]
    print(f"[config] Using model from yaml key '{model_key}': {cfg['model']} @ {cfg['base_url']}")
    return cfg


def load_json(path: str | Path) -> Any:
    path = Path(path)
    if not path.is_absolute():
        path = BENCHMARK_ROOT / path
    return json.loads(path.read_text(encoding="utf-8"))


def load_yaml(path: str | Path) -> Any:
    path = Path(path)
    if not path.is_absolute():
        path = BENCHMARK_ROOT / path
    return yaml.safe_load(path.read_text(encoding="utf-8"))


# ── Open-Meteo Live Fetcher ──────────────────────────────────

OPEN_METEO_URL = os.getenv("OPEN_METEO_BASE_URL", "https://api.open-meteo.com/v1")

HOURLY_VARIABLES = [
    "temperature_2m",
    "relative_humidity_2m",
    "precipitation_probability",
    "precipitation",
    "wind_speed_10m",
    "wind_gusts_10m",
    "weather_code",
]

OPEN_METEO_FIELD_MAP = {
    "temperature_2m":            "temperature_c",
    "relative_humidity_2m":      "humidity_percent",
    "precipitation_probability":  "rain_probability",
    "precipitation":             "precipitation_mm",
    "wind_speed_10m":            "wind_speed_kmh",
    "wind_gusts_10m":            "wind_gust_kmh",
    "weather_code":              "weather_code",
}


async def fetch_open_meteo(
    latitude: float,
    longitude: float,
    timezone: str = "Asia/Ho_Chi_Minh",
    forecast_days: int = 7,
) -> dict[str, Any]:
    """
    Call Open-Meteo API and return raw response dict.
    Raises on network or HTTP errors.
    """
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": ",".join(HOURLY_VARIABLES),
        "timezone": timezone,
        "forecast_days": forecast_days,
    }
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.get(f"{OPEN_METEO_URL}/forecast", params=params)
        resp.raise_for_status()
        return resp.json()


def raw_to_canonical(
    raw: dict[str, Any],
    case: dict[str, Any],
    fully: dict[str, Any],
) -> dict[str, Any]:
    """
    Convert a raw Open-Meteo API response into Canonical Weather JSON.
    Mirrors the logic in adapters/open_meteo_adapter.py.
    """
    hourly = raw.get("hourly", {})
    times = hourly.get("time", [])
    geo = fully.get("geographical_location", {})
    coords = geo.get("coordinates", {})
    time_range = fully.get("time_range", {})

    variables = []
    for idx, t in enumerate(times):
        point: dict[str, Any] = {"time": t}
        for raw_field, canonical_field in OPEN_METEO_FIELD_MAP.items():
            values = hourly.get(raw_field)
            if values and idx < len(values):
                point[canonical_field] = values[idx]
            else:
                point[canonical_field] = None
        point["storm_risk"] = None
        variables.append(point)

    missing = [f for f in OPEN_METEO_FIELD_MAP if not hourly.get(f)]

    return {
        "source": "open_meteo",
        "source_type": "api_forecast_live",
        "location": {
            "name": fully.get("location", "Unknown"),
            "latitude": coords.get("latitude", raw.get("latitude")),
            "longitude": coords.get("longitude", raw.get("longitude")),
            "timezone": time_range.get("timezone", "Asia/Ho_Chi_Minh"),
        },
        "forecast_window": {
            "start": time_range.get("start", ""),
            "end": time_range.get("end", ""),
        },
        "resolution": {
            "temporal": "hourly",
            "spatial": "city_level",
        },
        "variables": variables,
        "data_quality": {
            "missing_fields": missing,
            "confidence": "high" if not missing else "medium",
            "notes": [
                "Live data fetched from Open-Meteo API.",
                f"Fetched at {datetime.utcnow().isoformat()}Z",
            ],
        },
    }


# ── Prediction Engine (inline for benchmark independence) ────

def score_rain(prob: float | None) -> str:
    if prob is None:
        return "medium"
    if prob < 30:
        return "low"
    if prob <= 60:
        return "medium"
    return "high"


def score_temp(temp_c: float | None) -> str:
    if temp_c is None:
        return "medium"
    if temp_c < 35:
        return "low"
    if temp_c <= 38:
        return "medium"
    return "high"


def score_wind(wind_kmh: float | None) -> str:
    if wind_kmh is None:
        return "medium"
    if wind_kmh < 30:
        return "low"
    if wind_kmh <= 45:
        return "medium"
    return "high"


def combine_trip_risk(*risks: str) -> str:
    if "high" in risks:
        return "high"
    if list(risks).count("medium") >= 2:
        return "high"
    if "medium" in risks:
        return "medium"
    return "low"


def max_value(points: list[dict[str, Any]], key: str) -> float | None:
    values = [p.get(key) for p in points if isinstance(p.get(key), (int, float))]
    return max(values) if values else None


def predict_tourism(canonical_weather: dict[str, Any]) -> dict[str, Any]:
    points = canonical_weather.get("variables", [])
    max_rain = max_value(points, "rain_probability")
    max_temp = max_value(points, "temperature_c")
    max_wind = max_value(points, "wind_speed_kmh")

    rain_risk = score_rain(max_rain)
    heat_risk = score_temp(max_temp)
    wind_risk = score_wind(max_wind)
    trip_risk = combine_trip_risk(rain_risk, heat_risk, wind_risk)

    return {
        "domain": "tourism",
        "prediction_summary": (
            f"Rain risk is {rain_risk}, heat risk is {heat_risk}, "
            f"and wind risk is {wind_risk}."
        ),
        "recommendation_summary": (
            "Adjust outdoor activities based on the highest weather risk "
            "and keep suitable indoor backups."
        ),
        "risk_assessment": {
            "rain_risk": rain_risk,
            "heat_risk": heat_risk,
            "wind_risk": wind_risk,
            "trip_disruption_risk": trip_risk,
        },
        "evidence": [
            f"Maximum rain probability: {max_rain}%",
            f"Maximum temperature: {max_temp}°C",
            f"Maximum wind speed: {max_wind} km/h",
        ],
    }


# ── Prompt Builder ───────────────────────────────────────────

def build_messages(
    fully_processed: dict[str, Any],
    canonical_weather: dict[str, Any],
    prediction: dict[str, Any],
) -> list[dict[str, str]]:
    system = (
        "You are Weatherise, a weather-aware advisory system. "
        "Use the deterministic Prediction Engine result exactly. "
        "Do not overwrite risk_assessment. Do not invent weather data, warnings, or sources. "
        "Return valid JSON only."
    )
    user_payload = {
        "task": "Generate a final Weatherise response for Path A.",
        "domain": fully_processed.get("domain"),
        "intent": fully_processed.get("intent"),
        "raw_user_input": fully_processed.get("raw_user_input"),
        "user_constraints": fully_processed.get("user_constraints", []),
        "knowledge_context": fully_processed.get("knowledge_context", {}),
        "weather_data_quality": canonical_weather.get("data_quality", {}),
        "prediction_engine_result": prediction,
        "required_output_schema": {
            "prediction": "string",
            "recommendation": "string",
            "explanation": "string",
            "final_answer": "string",
        },
        "hard_rules": [
            "Do not change risk levels.",
            "Do not add typhoon, flood, or official warning unless present in input.",
            "Base recommendations only on the provided evidence and context.",
        ],
    }
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False, indent=2)},
    ]


# ── NIM Client (using openai) ────────────────────────────────

async def call_nim(
    model_cfg: dict[str, Any],
    messages: list[dict[str, str]],
) -> dict[str, Any]:
    start = time.perf_counter()

    client = AsyncOpenAI(
        base_url=model_cfg["base_url"],
        api_key=os.getenv("NGC_API_KEY", "not-needed"),
    )

    response = await client.chat.completions.create(
        model=model_cfg["model"],
        messages=messages,
        temperature=model_cfg.get("temperature", 0.2),
        max_tokens=model_cfg.get("max_tokens", 2048),
    )

    latency_ms = round((time.perf_counter() - start) * 1000, 2)

    usage = {}
    if response.usage:
        usage = {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens,
        }

    return {
        "model": model_cfg["model"],
        "content": response.choices[0].message.content.strip(),
        "usage": usage,
        "raw": response.model_dump() if hasattr(response, "model_dump") else {},
        "latency_ms": latency_ms,
        "error": None,
    }


# ── Output Validation ────────────────────────────────────────

def parse_json_response(content: str) -> tuple[bool, dict[str, Any] | None]:
    try:
        return True, json.loads(content)
    except Exception:
        stripped = content.strip()
        if stripped.startswith("```"):
            stripped = stripped.strip("`")
            stripped = stripped.replace("json\n", "", 1).replace("JSON\n", "", 1)
            try:
                return True, json.loads(stripped)
            except Exception:
                pass
        return False, None


def check_output(
    parsed: dict[str, Any] | None,
    expected: dict[str, Any],
    prediction: dict[str, Any],
) -> dict[str, Any]:
    if parsed is None:
        return {
            "valid_json": False,
            "required_fields_present": False,
            "risk_preserved": False,
            "hallucination_warning_count": None,
            "must_mention_score": 0,
        }

    required = ["prediction", "recommendation", "explanation", "final_answer"]
    required_fields_present = all(field in parsed for field in required)

    risk_preserved = True
    if "risk_assessment" in parsed:
        risk_preserved = parsed["risk_assessment"] == prediction["risk_assessment"]

    output_text = json.dumps(parsed, ensure_ascii=False).lower()
    must_not = expected.get("must_not_invent", [])
    hallucination_warning_count = sum(
        1 for term in must_not if term.lower() in output_text
    )
    must_mention = expected.get("must_mention", [])
    must_mention_score = sum(
        1 for term in must_mention if term.lower() in output_text
    )

    return {
        "valid_json": True,
        "required_fields_present": required_fields_present,
        "risk_preserved": risk_preserved,
        "hallucination_warning_count": hallucination_warning_count,
        "must_mention_score": must_mention_score,
    }


# ── Main Runner ──────────────────────────────────────────────

async def run(args: argparse.Namespace) -> None:
    registry = load_yaml("config/nim_models.yaml")
    model_cfg = resolve_model_config(args.model, registry)

    cases = load_json(args.case)
    mode_label = "live" if args.live else "mock"
    dry_label = "_dryrun" if args.dry_run else ""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = (
        BENCHMARK_ROOT / "outputs" / "path_a_runs"
        / f"{timestamp}_{args.model}_{mode_label}{dry_label}"
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    raw_jsonl = output_dir / "raw_model_outputs.jsonl"
    parsed_outputs = []
    summary_rows = []
    review_lines = [
        f"# Human Review — Path A Benchmark\n",
        f"Model: `{model_cfg['model']}`\n",
        f"Mode: `{mode_label}`\n",
        f"Dry-run: `{args.dry_run}`\n",
        f"Timestamp: `{timestamp}`\n",
    ]

    for case in cases:
        case_id = case["case_id"]
        fully = load_json(case["fully_processed_json_path"])

        # ── Weather source decision ───────────────────────────
        if args.live:
            # Fetch real weather from Open-Meteo
            geo = fully.get("geographical_location", {})
            coords = geo.get("coordinates", {})
            lat = coords.get("latitude", 16.0544)
            lon = coords.get("longitude", 108.2022)
            tz = fully.get("time_range", {}).get("timezone", "Asia/Ho_Chi_Minh")

            print(f"[{case_id}] Fetching live weather from Open-Meteo ({lat}, {lon})...")
            try:
                raw_weather = await fetch_open_meteo(lat, lon, tz)
                canonical_weather = raw_to_canonical(raw_weather, case, fully)
                weather_source = f"open_meteo_live ({lat}, {lon})"
            except Exception as exc:
                print(f"[{case_id}] Open-Meteo fetch failed: {exc}. Falling back to mock.")
                canonical_weather = load_json(case["canonical_weather_json_path"])
                weather_source = "mock_fallback_after_error"
        else:
            # Load frozen mock canonical weather file
            canonical_weather = load_json(case["canonical_weather_json_path"])
            weather_source = "mock_canonical_file"

        # ── Prediction Engine ─────────────────────────────────
        prediction = predict_tourism(canonical_weather)
        messages = build_messages(fully, canonical_weather, prediction)

        print(
            f"[{case_id}] Weather: {weather_source} | "
            f"Prediction: {prediction['risk_assessment']}"
        )

        # ── NIM call (or dry-run) ─────────────────────────────
        if args.dry_run:
            response = {
                "model": model_cfg["model"],
                "content": json.dumps({
                    "prediction": prediction["prediction_summary"],
                    "recommendation": prediction["recommendation_summary"],
                    "explanation": "DRY RUN: no NIM endpoint was called.",
                    "final_answer": (
                        f"DRY RUN — {prediction['prediction_summary']} "
                        f"({prediction['recommendation_summary']})"
                    ),
                }, ensure_ascii=False),
                "usage": {},
                "latency_ms": 0,
                "error": None,
                "weather_source": weather_source,
            }
        else:
            print(f"[{case_id}] Calling NIM ({model_cfg['model']})...")
            try:
                response = await call_nim(model_cfg, messages)
                response["weather_source"] = weather_source
            except Exception as exc:
                response = {
                    "model": model_cfg["model"],
                    "content": "",
                    "usage": {},
                    "latency_ms": None,
                    "error": str(exc),
                    "weather_source": weather_source,
                }

        # ── Validate + collect ────────────────────────────────
        _, parsed = parse_json_response(response["content"])
        checks = check_output(parsed, case.get("expected_behavior", {}), prediction)

        record = {
            "case_id": case_id,
            "description": case.get("description"),
            "model_key": args.model,
            "model": response["model"],
            "weather_source": weather_source,
            "prediction_engine_result": prediction,
            "messages": messages,
            "response": response,
            "parsed_output": parsed,
            "checks": checks,
        }
        with raw_jsonl.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        parsed_outputs.append(record)

        summary_rows.append({
            "case_id": case_id,
            "model": response["model"],
            "weather_source": weather_source,
            "valid_json": checks["valid_json"],
            "required_fields_present": checks["required_fields_present"],
            "risk_preserved": checks["risk_preserved"],
            "hallucination_warning_count": checks["hallucination_warning_count"],
            "must_mention_score": checks["must_mention_score"],
            "latency_ms": response["latency_ms"],
            "error": response["error"],
        })

        print(
            f"[{case_id}] VALID_JSON={checks['valid_json']} "
            f"RISK_PRESERVED={checks['risk_preserved']} "
            f"LATENCY_MS={response['latency_ms']} ERROR={response['error']}"
        )

        review_lines.extend([
            f"\n## {case_id}\n",
            f"- Description: {case.get('description')}\n",
            f"- Weather source: `{weather_source}`\n",
            f"- Risk: `{prediction['risk_assessment']}`\n",
            f"- Valid JSON: {checks['valid_json']}\n",
            f"- Risk preserved: {checks['risk_preserved']}\n",
            f"- Latency: {response['latency_ms']} ms\n",
            f"- Error: {response['error']}\n",
            "\n### Final answer\n",
            (parsed or {}).get("final_answer", response["content"][:1200]),
            "\n\n### Manual notes\n\n- TODO: Add human review here.\n",
        ])

    # ── Save outputs ──────────────────────────────────────────
    (output_dir / "parsed_outputs.json").write_text(
        json.dumps(parsed_outputs, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    if summary_rows:
        with (output_dir / "benchmark_summary.csv").open(
            "w", newline="", encoding="utf-8"
        ) as f:
            writer = csv.DictWriter(f, fieldnames=list(summary_rows[0].keys()))
            writer.writeheader()
            writer.writerows(summary_rows)
    (output_dir / "human_review.md").write_text(
        "\n".join(review_lines), encoding="utf-8"
    )
    print(f"\nSaved outputs to: {output_dir}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Weatherise Path A benchmark runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
MODEL SELECTION
  --model env     (default) reads NIM_LLM_BASE_URL + NIM_LLM_MODEL from .env
  --model <key>   named entry in config/nim_models.yaml

EXAMPLES
  Use whatever model is in .env, frozen mock, call NIM:
    python3 scripts/run_path_a_mock_test.py --case benchmark_cases/path_a_cases.json

  Use whatever model is in .env, frozen mock, no NIM (smoke-test):
    python3 scripts/run_path_a_mock_test.py --case benchmark_cases/path_a_cases.json --dry-run

  Use whatever model is in .env, live Open-Meteo, call NIM:
    python3 scripts/run_path_a_mock_test.py --case benchmark_cases/path_a_cases.json --live

  Use whatever model is in .env, live weather, no NIM:
    python3 scripts/run_path_a_mock_test.py --case benchmark_cases/path_a_cases.json --live --dry-run

  Force a specific model from yaml, frozen mock, call NIM:
    python3 scripts/run_path_a_mock_test.py --case benchmark_cases/path_a_cases.json --model nemotron_nano_8b

  Force a specific model, live weather, call NIM:
    python3 scripts/run_path_a_mock_test.py --case benchmark_cases/path_a_cases.json --model nemotron_nano_8b --live
        """,
    )
    parser.add_argument(
        "--case", required=True,
        help="Path to benchmark case JSON (relative to benchmark/ root)",
    )
    parser.add_argument(
        "--model", default="env",
        help=(
            "Model to use. 'env' (default) reads NIM_LLM_BASE_URL + NIM_LLM_MODEL "
            "from the repo .env file. Any other value is looked up in config/nim_models.yaml."
        ),
    )
    parser.add_argument(
        "--live", action="store_true",
        help="Fetch real weather from Open-Meteo instead of frozen mock files",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Skip NIM call — use prediction engine text as final answer (no GPU needed)",
    )
    args = parser.parse_args()
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
