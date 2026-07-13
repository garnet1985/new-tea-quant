"""枚举 version 目录产物路径约定。"""
from __future__ import annotations

from pathlib import Path

# 全局产物（0_ 前缀 — 目录列表中排在 per-entity 文件之前）
GLOBAL_PREFIX = ""
RUNTIME_ENV_FILE = f"{GLOBAL_PREFIX}runtime_env.json"
ENTITY_IDS_FILE = f"{GLOBAL_PREFIX}entity_ids.txt"
PERFORMANCE_FILE = f"{GLOBAL_PREFIX}performance.json"
OVERALL_REPORT_FILE = f"{GLOBAL_PREFIX}overall_report.json"

# 每股 CSV 子目录（避免 version 根目录上千文件）
ENTITIES_SUBDIR = "entities"

PERFORMANCE_DETAIL_SUMMARY = "summary"
PERFORMANCE_DETAIL_FULL = "full"


def entities_dir(output_dir: Path) -> Path:
    return Path(output_dir) / ENTITIES_SUBDIR


def resolve_performance_detail(performance_config: dict | None) -> str:
    raw = str((performance_config or {}).get("performance_detail") or "").strip().lower()
    if raw in {PERFORMANCE_DETAIL_FULL, "full", "detailed", "jobs"}:
        return PERFORMANCE_DETAIL_FULL
    return PERFORMANCE_DETAIL_SUMMARY


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
    "GLOBAL_PREFIX",
    "OVERALL_REPORT_FILE",
    "PERFORMANCE_DETAIL_FULL",
    "PERFORMANCE_DETAIL_SUMMARY",
    "PERFORMANCE_FILE",
    "RUNTIME_ENV_FILE",
    "entities_dir",
    "report_output_config",
    "resolve_performance_detail",
]
