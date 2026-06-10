"""
Context Gap Report — V3
Compares required context list against what was found in KB.
Produces a structured report of what's missing → drives MCP planning.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class FoundContextItem:
    context_type: str
    source: str          # "knowledge_base" | "mcp" | "parser"
    confidence: str      # "high" | "medium" | "low"
    data_preview: Optional[str] = None   # short repr for debugging


@dataclass
class MissingContextItem:
    context_type: str
    reason: str
    priority: int = 1    # 1=critical, 2=important, 3=optional


@dataclass
class ContextGapReport:
    domain: str
    location: str
    required_context: List[str]
    found_context: Dict[str, FoundContextItem]
    missing_context: List[MissingContextItem]

    @property
    def is_complete(self) -> bool:
        return len(self.missing_context) == 0

    @property
    def critical_missing(self) -> List[str]:
        return [m.context_type for m in self.missing_context if m.priority == 1]

    @property
    def missing_types(self) -> List[str]:
        return [m.context_type for m in self.missing_context]


def build_context_gap_report(
    required: List[str],
    kb_results: Dict[str, Any],
    domain: str = "tourism",
    location: str = "",
) -> ContextGapReport:
    """
    Compare required context list with KB results.
    
    Args:
        required: context types the agent needs
        kb_results: dict of context_type → data (None/empty = not found)
        domain: the domain being planned
        location: the location being queried
    
    Returns: ContextGapReport with found/missing breakdown
    """
    # Priority map — which context types are blocking vs optional
    PRIORITY = {
        "coordinates":                 1,
        "tourist_attractions":         1,
        "weather_forecast":            1,
        "time_range":                  1,
        "restaurants":                 2,
        "opening_hours":               2,
        "distance_matrix":             3,
        "indoor_outdoor_classification": 2,
        "trip_route_plan":             2,
        "backup_plan_options":         3,
        "weather_risk_rules":          2,
        "storm_risk":                  2,
        "uv_index":                    3,
    }

    found = {}
    missing = []

    for ctx_type in required:
        data = kb_results.get(ctx_type)
        has_data = bool(data) if not isinstance(data, bool) else data

        if has_data:
            preview = None
            if isinstance(data, list):
                preview = f"{len(data)} items"
            elif isinstance(data, dict):
                preview = str(list(data.keys())[:3])
            found[ctx_type] = FoundContextItem(
                context_type=ctx_type,
                source="knowledge_base",
                confidence="high",
                data_preview=preview,
            )
        else:
            missing.append(MissingContextItem(
                context_type=ctx_type,
                reason=f"Not found in Knowledge Base for '{location}'",
                priority=PRIORITY.get(ctx_type, 3),
            ))

    # Sort missing by priority (critical first)
    missing.sort(key=lambda m: m.priority)

    return ContextGapReport(
        domain=domain,
        location=location,
        required_context=required,
        found_context=found,
        missing_context=missing,
    )
