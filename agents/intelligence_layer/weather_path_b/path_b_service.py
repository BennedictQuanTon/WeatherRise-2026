"""Path B orchestration service following the multi-source weather diagram."""

from __future__ import annotations

from typing import Any

from .comparison_matrix import SourceComparisonBuilder
from .earth2_processing import Earth2StudioProcessingLayer
from .evidence_store import WeatherEvidenceStore
from .fusion_engine import WeatherFusionEngine
from .gold_weather_decision import GoldWeatherDecisionBuilder
from .multi_source_weather_fetcher import MultiSourceWeatherFetcher
from .nim_weather_arbiter import NIMWeatherArbiter
from .normalizers import SourceSpecificNormalizer
from .quality_validator import WeatherQualityValidator
from .rag_hooks import WeatherKnowledgeRetriever
from .schemas import GoldWeatherDecision
from .source_scorer import SourceScorer
from .weather_requirement_reader import WeatherRequirementReader
from .weather_source_planner import WeatherSourcePlanner


class PathBWeatherService:
    """Full Path B weather decision pipeline."""

    def __init__(
        self,
        requirement_reader: WeatherRequirementReader | None = None,
        source_planner: WeatherSourcePlanner | None = None,
        fetcher: MultiSourceWeatherFetcher | None = None,
        evidence_store: WeatherEvidenceStore | None = None,
        normalizer: SourceSpecificNormalizer | None = None,
        earth2_layer: Earth2StudioProcessingLayer | None = None,
        quality_validator: WeatherQualityValidator | None = None,
        source_scorer: SourceScorer | None = None,
        comparison_builder: SourceComparisonBuilder | None = None,
        fusion_engine: WeatherFusionEngine | None = None,
        arbiter: NIMWeatherArbiter | None = None,
        gold_builder: GoldWeatherDecisionBuilder | None = None,
        knowledge_retriever: WeatherKnowledgeRetriever | None = None,
    ):
        self.requirement_reader = requirement_reader or WeatherRequirementReader()
        self.source_planner = source_planner or WeatherSourcePlanner()
        self.fetcher = fetcher or MultiSourceWeatherFetcher()
        self.evidence_store = evidence_store or WeatherEvidenceStore()
        self.normalizer = normalizer or SourceSpecificNormalizer()
        self.earth2_layer = earth2_layer or Earth2StudioProcessingLayer()
        self.quality_validator = quality_validator or WeatherQualityValidator()
        self.source_scorer = source_scorer or SourceScorer()
        self.comparison_builder = comparison_builder or SourceComparisonBuilder()
        self.fusion_engine = fusion_engine or WeatherFusionEngine()
        self.arbiter = arbiter or NIMWeatherArbiter()
        self.gold_builder = gold_builder or GoldWeatherDecisionBuilder()
        self.knowledge_retriever = knowledge_retriever or WeatherKnowledgeRetriever()

    async def run(self, processed_json: Any) -> GoldWeatherDecision:
        requirement = self.requirement_reader.read(processed_json)
        source_plan = self.source_planner.plan(requirement)
        raw_responses = await self.fetcher.fetch(requirement, source_plan)
        raw_responses = [self.evidence_store.save_raw(requirement, raw) for raw in raw_responses]

        normalized_records = self.normalizer.normalize(raw_responses, requirement)
        normalized_records = self.evidence_store.save_normalized(requirement, normalized_records)
        earth2_report = self.earth2_layer.process(requirement, normalized_records)

        valid_records, quality_reports = self.quality_validator.validate(normalized_records, requirement)
        if not valid_records:
            return self.gold_builder.unavailable(
                requirement,
                quality_reports=quality_reports,
                warnings=[
                    "Path B could not produce valid weather evidence.",
                    *self.evidence_store.warnings,
                ],
            )

        source_scores = self.source_scorer.score(requirement, valid_records, quality_reports, raw_responses)
        comparison = self.comparison_builder.build(requirement, valid_records)
        comparison_path = self.evidence_store.save_comparison(requirement, comparison)

        rejected_sources = [
            report.source_code
            for report in quality_reports
            if not report.valid
        ] + [
            item["source_code"]
            for item in source_plan.skipped_sources
            if item.get("source_code")
        ]
        fused = self.fusion_engine.fuse(requirement, comparison, source_scores, rejected_sources)
        fused_path = self.evidence_store.save_fused(requirement, fused)

        context = processed_json.model_dump() if hasattr(processed_json, "model_dump") else dict(processed_json)
        retrieved_knowledge = await self.knowledge_retriever.retrieve(requirement, context)
        arbiter_decision = await self.arbiter.decide(
            requirement=requirement,
            source_scores=source_scores,
            quality_reports=quality_reports,
            comparison_matrix=comparison,
            fused_weather=fused,
            earth2_report=earth2_report,
            retrieved_weather_knowledge=retrieved_knowledge,
        )
        gold = self.gold_builder.build(
            requirement=requirement,
            valid_records=valid_records,
            source_scores=source_scores,
            quality_reports=quality_reports,
            comparison_matrix=comparison,
            fused_weather=fused,
            arbiter_decision=arbiter_decision,
            earth2_processing_report=earth2_report,
            evidence_paths={
                "comparison_report": comparison_path,
                "fused_weather": fused_path,
                "raw_root": str(self.evidence_store.root / "raw"),
                "normalized_root": str(self.evidence_store.root / "normalized"),
            },
            extra_warnings=self.evidence_store.warnings,
        )
        selected_path = self.evidence_store.save_selected(requirement, gold)
        gold.evidence_paths["selected_weather"] = selected_path
        return gold
