#!/usr/bin/env python3
"""
Analyzer 统一入口

职责：
- 解析策略 settings 中的 analyzer 配置
- 调用 StatisticalAnalyzer / MLAnalyzer 生成分析报告
- 将报告写入模拟结果目录下的 analysis/ 子目录

注意：
- Analyzer 只读模拟/枚举结果文件，不修改原始结果
- Analyzer 的失败不能影响模拟器主流程
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List
import logging

from .base_analyzer import AnalysisContext
from .statistical_analyzer import StatisticalAnalyzer
from .ml_analyzer import MLAnalyzer
from .report_builder import ReportBuilder


logger = logging.getLogger(__name__)


@dataclass
class AnalyzerConfig:
    """解析自 settings 的 analyzer 配置（内部使用的轻量模型）。"""

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

        enabled = bool(analyzer_cfg.get("enabled", False))
        stat_enabled = bool(stat_cfg.get("enabled", False))
        metrics = stat_cfg.get("metrics", []) or []
        if not isinstance(metrics, list):
            metrics = []

        ml_enabled = bool(ml_cfg.get("enabled", False))
        ml_target = str(ml_cfg.get("target", "enumerator") or "enumerator")
        ml_task = str(ml_cfg.get("task", "classification") or "classification")

        return cls(
            enabled=enabled,
            statistical_enabled=stat_enabled,
            statistical_metrics=metrics,
            ml_enabled=ml_enabled,
            ml_target=ml_target,
            ml_task=ml_task,
        )


class Analyzer:
    """
    Analyzer 统一入口。

    使用方式（在模拟器完成结果保存后）：

        Analyzer.run_for_simulator(
            strategy_name=strategy_name,
            sim_type="price_factor",
            sim_version_dir=sim_version_dir,
            raw_settings=base_settings.to_dict(),
        )
    """

    @staticmethod
    def run_for_simulator(
        strategy_name: str,
        sim_type: str,
        sim_version_dir: Path,
        raw_settings: Dict[str, Any],
    ) -> None:
        """
        为某次模拟运行 Analyzer。

        Args:
            strategy_name: 策略名称
            sim_type: 模拟器类型（如 "price_factor" / "capital_allocation"）
            sim_version_dir: 本次模拟结果目录
            raw_settings: 原始策略 settings 字典
        """
        try:
            cfg = AnalyzerConfig.from_raw_settings(raw_settings)
        except Exception as exc:
            logger.warning("[Analyzer] 解析 analyzer 配置失败: %s", exc)
            return

        if not cfg.enabled:
            logger.info("[Analyzer] analyzer 未启用，跳过分析")
            return

        context = AnalysisContext(
            strategy_name=strategy_name,
            sim_type=sim_type,
            sim_version_dir=sim_version_dir,
            raw_settings=raw_settings,
        )

        analysis_root = sim_version_dir / "analysis"
        try:
            analysis_root.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            logger.warning("[Analyzer] 创建 analysis 目录失败: %s", exc)
            return

        # 1. 统计学分析
        if cfg.statistical_enabled:
            try:
                stat_analyzer = StatisticalAnalyzer(
                    context=context, metrics=cfg.statistical_metrics
                )
                stat_report = stat_analyzer.run()
                ReportBuilder.write_json(
                    analysis_root / "statistical_report.json", stat_report
                )
                ReportBuilder.write_markdown_statistical(
                    analysis_root / "statistical_report.md", stat_report
                )
                logger.info("[Analyzer] 统计学分析完成")
            except Exception as exc:
                logger.warning("[Analyzer] 统计学分析失败: %s", exc)

        # 2. 机器学习分析（仅在 target == 'enumerator' 时尝试）
        if cfg.ml_enabled and cfg.ml_target == "enumerator":
            try:
                ml_analyzer = MLAnalyzer(context=context, task=cfg.ml_task)
                ml_report = ml_analyzer.run()
                ReportBuilder.write_json(
                    analysis_root / "ml_factor_importance.json", ml_report
                )
                ReportBuilder.write_markdown_ml(
                    analysis_root / "ml_factor_importance.md", ml_report
                )
                logger.info("[Analyzer] ML 因子重要性分析完成")
            except Exception as exc:
                logger.warning("[Analyzer] ML 分析失败: %s", exc)

    @staticmethod
    def run_for_enumerator(
        strategy_name: str,
        enum_version_dir: Path,
        raw_settings: Dict[str, Any],
    ) -> None:
        """
        预留接口：直接基于枚举器版本目录运行 Analyzer。

        当前版本主要由模拟器触发 MLAnalyzer，枚举器入口暂未实现。
        """
        logger.info(
            "[Analyzer] run_for_enumerator 暂未实现，enum_version_dir=%s",
            enum_version_dir,
        )

