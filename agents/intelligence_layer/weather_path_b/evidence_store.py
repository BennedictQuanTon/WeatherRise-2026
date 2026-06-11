"""File-based bronze/normalized/selected evidence storage for Path B."""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .schemas import (
    FusedWeather,
    GoldWeatherDecision,
    RawWeatherResponse,
    SourceComparisonMatrix,
    StandardWeatherRecord,
    WeatherRequirement,
)


def _model_dump(obj: Any) -> dict[str, Any]:
    return obj.model_dump() if hasattr(obj, "model_dump") else dict(obj)


class WeatherEvidenceStore:
    """Writes evidence snapshots to a configured file root.

    The configured production root is `/raid/team/weatherise/weather_evidence`.
    If the process cannot write there, the store falls back to
    `data/weather_evidence` so Path B can still return a decision.
    """

    def __init__(self, root_dir: str | None = None):
        self.configured_root = Path(root_dir or os.getenv("WEATHER_EVIDENCE_DIR", "/raid/team/weatherise/weather_evidence"))
        self.fallback_root = Path(os.getenv("WEATHER_EVIDENCE_FALLBACK_DIR", "data/weather_evidence"))
        self.root = self.configured_root
        self.warnings: list[str] = []

    def save_raw(self, requirement: WeatherRequirement, raw: RawWeatherResponse) -> RawWeatherResponse:
        payload = {
            "metadata": raw.model_dump(exclude={"raw_payload"}),
            "raw_payload": raw.raw_payload,
        }
        path = self._write_json("raw", raw.source_code, requirement, payload)
        raw.raw_file_path = str(path)
        self._append_manifest("raw", raw.source_code, requirement, path, raw.status)
        return raw

    def save_normalized(
        self,
        requirement: WeatherRequirement,
        records: list[StandardWeatherRecord],
    ) -> list[StandardWeatherRecord]:
        by_source: dict[str, list[dict[str, Any]]] = {}
        for record in records:
            by_source.setdefault(record.source_code, []).append(record.model_dump())
        for source, items in by_source.items():
            path = self._write_json("normalized", source, requirement, {"records": items})
            for record in records:
                if record.source_code == source:
                    record.normalized_file_path = str(path)
            self._append_manifest("normalized", source, requirement, path, "success")
        return records

    def save_comparison(self, requirement: WeatherRequirement, comparison: SourceComparisonMatrix) -> str:
        path = self._write_json("comparison_reports", "comparison", requirement, comparison.model_dump())
        self._append_manifest("comparison", "comparison", requirement, path, "success")
        return str(path)

    def save_fused(self, requirement: WeatherRequirement, fused: FusedWeather) -> str:
        path = self._write_json("fused", "fusion", requirement, fused.model_dump())
        self._append_manifest("fused", "fusion", requirement, path, "success")
        return str(path)

    def save_selected(self, requirement: WeatherRequirement, gold: GoldWeatherDecision) -> str:
        path = self._write_json("selected", "gold_weather_decision", requirement, gold.model_dump())
        self._append_manifest("selected", "gold_weather_decision", requirement, path, "success")
        return str(path)

    def _write_json(
        self,
        layer: str,
        source_code: str,
        requirement: WeatherRequirement,
        payload: dict[str, Any],
    ) -> Path:
        directory = self._ensure_dir(self.root / layer / source_code)
        filename = self._filename(requirement, source_code)
        path = directory / filename
        with path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2, default=str)
        return path

    def _append_manifest(
        self,
        layer: str,
        source_code: str,
        requirement: WeatherRequirement,
        path: Path,
        status: str,
    ) -> None:
        manifest_dir = self._ensure_dir(self.root)
        manifest = manifest_dir / "manifest.jsonl"
        item = {
            "request_id": requirement.request_id,
            "layer": layer,
            "source_code": source_code,
            "path": str(path),
            "status": status,
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
        }
        with manifest.open("a", encoding="utf-8") as f:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    def _ensure_dir(self, path: Path) -> Path:
        try:
            path.mkdir(parents=True, exist_ok=True)
            return path
        except OSError as exc:
            if self.root != self.fallback_root:
                self.warnings.append(f"Evidence root {self.root} unavailable: {exc}. Using {self.fallback_root}.")
                self.root = self.fallback_root
                fallback = self.fallback_root / path.relative_to(self.configured_root)
                fallback.mkdir(parents=True, exist_ok=True)
                return fallback
            raise

    def _filename(self, requirement: WeatherRequirement, source_code: str) -> str:
        location = self._slug(requirement.location_name)
        time_part = self._slug(requirement.start_time or datetime.now(timezone.utc).isoformat())
        return f"{location}_{time_part}_{source_code}_{requirement.request_id}.json"

    def _slug(self, value: str) -> str:
        return re.sub(r"[^a-zA-Z0-9_-]+", "_", value.strip().lower()).strip("_") or "weather"
