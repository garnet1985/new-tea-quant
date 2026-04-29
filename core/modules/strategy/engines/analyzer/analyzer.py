#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List
import logging

from .data_classes import AnalysisContext
from .helpers import MLAnalyzer, ReportBuilder, StatisticalAnalyzer

logger = logging.getLogger(__name__)


@dataclass
class AnalyzerConfig:
    enabled: bool = False
    statistical_enabled: bool = False
    statistical_metrics: List[str] = None  # type: ignore[assignment]
    ml_enabled: bool = False
    ml_target: str = "enumerator"
    ml_task: str = "classification"

    @classmethod
    def from_raw_settings(cls, raw_settings: Dict[str, Any]) -> "AnalyzerConfig":
        analyzer_cfg = raw_settings.get("analyzer", {}) or {}
        stat_cfg = analyzer_cfg.get("statistical", {}) or {}
        ml_cfg = analyzer_cfg.get("ml", {}) or {}
        metrics = stat_cfg.get("metrics", []) or []
        if not isinstance(metrics, list):
            metrics = []
        return cls(
            enabled=bool(analyzer_cfg.get("enabled", False)),
            statistical_enabled=bool(stat_cfg.get("enabled", False)),
            statistical_metrics=metrics,
            ml_enabled=bool(ml_cfg.get("enabled", False)),
            ml_target=str(ml_cfg.get("target", "enumerator") or "enumerator"),
            ml_task=str(ml_cfg.get("task", "classification") or "classification"),
        )


class Analyzer:
    @staticmethod
    def run_for_simulator(
        strategy_name: str,
        sim_type: str,
        sim_version_dir: Path,
        raw_settings: Dict[str, Any],
    ) -> None:
        try:
            cfg = AnalyzerConfig.from_raw_settings(raw_settings)
        except Exception as exc:
            logger.warning("[Analyzer] Parse config failed: %s", exc)
            return
        if not cfg.enabled:
            return
        context = AnalysisContext(
            strategy_name=strategy_name,
            sim_type=sim_type,
            sim_version_dir=sim_version_dir,
            raw_settings=raw_settings,
        )
        analysis_root = sim_version_dir / "analysis"
        analysis_root.mkdir(parents=True, exist_ok=True)
        if cfg.statistical_enabled:
            try:
                stat_analyzer = StatisticalAnalyzer(context=context, metrics=cfg.statistical_metrics)
                stat_report = stat_analyzer.run()
                ReportBuilder.write_json(analysis_root / "statistical_report.json", stat_report)
                ReportBuilder.write_markdown_statistical(analysis_root / "statistical_report.md", stat_report)
            except Exception as exc:
                logger.warning("[Analyzer] Statistical analysis failed: %s", exc)
        if cfg.ml_enabled and cfg.ml_target == "enumerator":
            try:
                ml_analyzer = MLAnalyzer(context=context, task=cfg.ml_task)
                ml_report = ml_analyzer.run()
                ReportBuilder.write_json(analysis_root / "ml_factor_importance.json", ml_report)
                ReportBuilder.write_markdown_ml(analysis_root / "ml_factor_importance.md", ml_report)
            except Exception as exc:
                logger.warning("[Analyzer] ML analysis failed: %s", exc)

    @staticmethod
    def run_for_enumerator(strategy_name: str, enum_version_dir: Path, raw_settings: Dict[str, Any]) -> None:
        logger.info("[Analyzer] run_for_enumerator not implemented: %s", enum_version_dir)


__all__ = ["AnalyzerConfig", "Analyzer"]
