"""枚举 version 目录产物路径约定（entity_based / slice_based 共用契约）。"""
from __future__ import annotations

from pathlib import Path
from typing import FrozenSet

# 全局产物（0_ 前缀 — 目录列表中排在 per-entity 文件之前）
GLOBAL_PREFIX = "0_"
RUNTIME_ENV_FILE = f"{GLOBAL_PREFIX}runtime_env.json"
ENTITY_IDS_FILE = f"{GLOBAL_PREFIX}entity_ids.txt"
PERFORMANCE_FILE = f"{GLOBAL_PREFIX}performance.json"
OVERALL_REPORT_FILE = f"{GLOBAL_PREFIX}overall_report.json"

# 每股 CSV 子目录（避免 version 根目录上千文件）
ENTITIES_SUBDIR = "entities"

# version 根目录必有文件（契约；entities/ 内 CSV 按命中动态）
ENUM_VERSION_REQUIRED_FILES = (
    RUNTIME_ENV_FILE,
    ENTITY_IDS_FILE,
    PERFORMANCE_FILE,
    OVERALL_REPORT_FILE,
)

PERFORMANCE_DETAIL_SUMMARY = "summary"
PERFORMANCE_DETAIL_FULL = "full"

# overall「Goal 成交」不计这些退出腿（强制收口 / 到期，非目标止盈止损）
NON_GOAL_EXIT_REASONS: FrozenSet[str] = frozenset(
    {
        "simulate_end",
        "expired",
        "period_end",
        "max_holding",
    }
)


class ReportPaths:
    """枚举产物路径与 report 输出配置解析。

    边界:
    - 负责: version 目录路径约定、performance_detail / report config 读取
    - 不负责: 写盘、统计聚合
    - 调用方: ReportManager 子模块、entity/slice Pipeline
    """

    @staticmethod
    def entities_dir(output_dir: Path) -> Path:
        return Path(output_dir) / ENTITIES_SUBDIR

    @staticmethod
    def resolve_performance_detail(performance_config: dict | None) -> str:
        raw = str((performance_config or {}).get("performance_detail") or "").strip().lower()
        if raw in {PERFORMANCE_DETAIL_FULL, "full", "detailed", "jobs"}:
            return PERFORMANCE_DETAIL_FULL
        return PERFORMANCE_DETAIL_SUMMARY

    @staticmethod
    def report_output_config(raw_settings: dict | None) -> dict:
        """从 strategy settings 读取 report 输出配置。"""
        settings = dict(raw_settings or {})
        output = settings.get("output") or {}
        report = output.get("report") or {}
        if isinstance(report, dict):
            return dict(report)
        return {}


__all__ = [
    "ENTITIES_SUBDIR",
    "ENTITY_IDS_FILE",
    "ENUM_VERSION_REQUIRED_FILES",
    "GLOBAL_PREFIX",
    "NON_GOAL_EXIT_REASONS",
    "OVERALL_REPORT_FILE",
    "PERFORMANCE_DETAIL_FULL",
    "PERFORMANCE_DETAIL_SUMMARY",
    "PERFORMANCE_FILE",
    "RUNTIME_ENV_FILE",
    "ReportPaths",
]
