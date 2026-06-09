#!/usr/bin/env python3
"""
Weatherise Path A mock JSON benchmark runner.

Usage:
  python agents/intelligence_layer/benchmark/scripts/run_path_a_mock_test.py \\
    --case benchmark_cases/path_a_cases.json \\
    --model nemotron_nano_8b

  python agents/intelligence_layer/benchmark/scripts/run_path_a_mock_test.py \\
    --case benchmark_cases/path_a_cases.json \\
    --model nemotron_nano_8b --dry-run

Dependencies:
  pip install openai pyyaml
"""

import argparse
import asyncio
import csv
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

# Use openai for NIM calls (matching intelligence layer's nim_client.py)
from openai import AsyncOpenAI


# ── Path resolution ──────────────────────────────────────────

BENCHMARK_ROOT = Path(__file__).resolve().parents[1]  # benchmark/
LAYER_ROOT = BENCHMARK_ROOT.parent  # intelligence_layer/


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
        "prediction_summary": f"Rain risk is {rain_risk}, heat risk is {heat_risk}, and wind risk is {wind_risk}.",
        "recommendation_summary": "Adjust outdoor activities based on the highest weather risk and keep suitable indoor backups.",
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


# ── NIM Client (using openai) ───────────────────────────────

async def call_nim(model_cfg: dict[str, Any], messages: list[dict[str, str]]) -> dict[str, Any]:
    start = time.perf_counter()

    client = AsyncOpenAI(
        base_url=model_cfg["base_url"],
        api_key="not-needed",
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
    hallucination_warning_count = sum(1 for term in must_not if term.lower() in output_text)

    must_mention = expected.get("must_mention", [])
    must_mention_score = sum(1 for term in must_mention if term.lower() in output_text)

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
    if args.model not in registry["models"]:
        raise SystemExit(f"Unknown model key: {args.model}")
    model_cfg = registry["models"][args.model]

    cases = load_json(args.case)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = BENCHMARK_ROOT / "outputs" / "path_a_runs" / f"{timestamp}_{args.model}"
    output_dir.mkdir(parents=True, exist_ok=True)

    raw_jsonl = output_dir / "raw_model_outputs.jsonl"
    parsed_outputs = []
    summary_rows = []
    review_lines = [f"# Human Review — Path A Benchmark\n", f"Model key: `{args.model}`\n"]

    for case in cases:
        fully = load_json(case["fully_processed_json_path"])
        weather = load_json(case["canonical_weather_json_path"])
        prediction = predict_tourism(weather)
        messages = build_messages(fully, weather, prediction)

        if args.dry_run:
            response = {
                "model": model_cfg["model"],
                "content": json.dumps({
                    "prediction": prediction["prediction_summary"],
                    "recommendation": prediction["recommendation_summary"],
                    "explanation": "DRY RUN: no NIM endpoint was called.",
                    "final_answer": "DRY RUN response generated locally."
                }, ensure_ascii=False),
                "usage": {},
                "latency_ms": 0,
                "error": None,
            }
        else:
            try:
                response = await call_nim(model_cfg, messages)
            except Exception as exc:
                response = {
                    "model": model_cfg["model"],
                    "content": "",
                    "usage": {},
                    "latency_ms": None,
                    "error": str(exc),
                }

        valid, parsed = parse_json_response(response["content"])
        checks = check_output(parsed, case.get("expected_behavior", {}), prediction)

        record = {
            "case_id": case["case_id"],
            "description": case.get("description"),
            "model_key": args.model,
            "model": response["model"],
            "prediction_engine_result": prediction,
            "messages": messages,
            "response": response,
            "parsed_output": parsed,
            "checks": checks,
        }
        with raw_jsonl.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        parsed_outputs.append(record)

        row = {
            "case_id": case["case_id"],
            "model": response["model"],
            "valid_json": checks["valid_json"],
            "required_fields_present": checks["required_fields_present"],
            "risk_preserved": checks["risk_preserved"],
            "hallucination_warning_count": checks["hallucination_warning_count"],
            "must_mention_score": checks["must_mention_score"],
            "latency_ms": response["latency_ms"],
            "error": response["error"],
        }
        summary_rows.append(row)

        print(
            f"CASE={case['case_id']} MODEL={response['model']} "
            f"VALID_JSON={checks['valid_json']} RISK_PRESERVED={checks['risk_preserved']} "
            f"LATENCY_MS={response['latency_ms']} ERROR={response['error']}"
        )

        review_lines.extend([
            f"\n## {case['case_id']}\n",
            f"- Description: {case.get('description')}\n",
            f"- Valid JSON: {checks['valid_json']}\n",
            f"- Risk preserved: {checks['risk_preserved']}\n",
            f"- Latency: {response['latency_ms']} ms\n",
            f"- Error: {response['error']}\n",
            "\n### Final answer\n",
            (parsed or {}).get("final_answer", response["content"][:1200]),
            "\n\n### Manual notes\n\n- TODO: Add human review here.\n",
        ])

    (output_dir / "parsed_outputs.json").write_text(
        json.dumps(parsed_outputs, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    if summary_rows:
        with (output_dir / "benchmark_summary.csv").open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(summary_rows[0].keys()))
            writer.writeheader()
            writer.writerows(summary_rows)
    (output_dir / "human_review.md").write_text(
        "\n".join(review_lines), encoding="utf-8"
    )

    print(f"\nSaved outputs to: {output_dir}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Weatherise Path A mock benchmark runner")
    parser.add_argument("--case", required=True, help="Path to benchmark case JSON file")
    parser.add_argument("--model", default="nemotron_nano_8b", help="Model key from config/nim_models.yaml")
    parser.add_argument("--dry-run", action="store_true", help="Do not call NIM; generate local dry-run response")
    args = parser.parse_args()
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
