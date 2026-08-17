"""仿真 version 目录文件名与相对路径（仅 ArtifactStore 使用）。"""
from __future__ import annotations

from pathlib import Path

RUNTIME_ENV_FILE = "runtime_env.json"
ENTITY_IDS_FILE = "entity_ids.txt"
PERFORMANCE_FILE = "performance.json"
OVERALL_REPORT_FILE = "overall_report.json"
ENTITY_LIST_FILE = "entity_list.json"
TRADES_FILE = "trades.json"
EQUITY_CURVE_FILE = "equity_curve.json"

ENTITIES_SUBDIR = "entities"

STOCK_INVESTMENTS_SUFFIX = "_stock_investments.csv"
GOAL_ACHIEVEMENTS_SUFFIX = "_goal_achievements.csv"
SIGNAL_SNAPSHOTS_SUFFIX = "_signal_snapshots.csv"
PRICE_INVESTMENTS_SUFFIX = "_investments.csv"

ENUM_REPORT_FILES = (
    OVERALL_REPORT_FILE,
    ENTITY_LIST_FILE,
    PERFORMANCE_FILE,
)
PRICE_REPORT_FILES = ENUM_REPORT_FILES
PORTFOLIO_REPORT_FILES = ENUM_REPORT_FILES

ENUM_VERSION_REQUIRED_FILES = (
    RUNTIME_ENV_FILE,
    ENTITY_IDS_FILE,
    *ENUM_REPORT_FILES,
)
PRICE_VERSION_REQUIRED_FILES = (
    RUNTIME_ENV_FILE,
    ENTITY_IDS_FILE,
    *PRICE_REPORT_FILES,
)
PORTFOLIO_VERSION_REQUIRED_FILES = (
    RUNTIME_ENV_FILE,
    *PORTFOLIO_REPORT_FILES,
)


def entities_dir(output_dir: Path) -> Path:
    return Path(output_dir) / ENTITIES_SUBDIR


def named_file(output_dir: Path, filename: str) -> Path:
    return Path(output_dir) / filename


def entity_file(output_dir: Path, entity_id: str, suffix: str) -> Path:
    eid = str(entity_id or "").strip().replace("/", "_")
    return entities_dir(output_dir) / f"{eid}{suffix}"


__all__ = [
    "ENTITIES_SUBDIR",
    "ENTITY_IDS_FILE",
    "ENTITY_LIST_FILE",
    "ENUM_REPORT_FILES",
    "ENUM_VERSION_REQUIRED_FILES",
    "EQUITY_CURVE_FILE",
    "GOAL_ACHIEVEMENTS_SUFFIX",
    "OVERALL_REPORT_FILE",
    "PERFORMANCE_FILE",
    "PRICE_INVESTMENTS_SUFFIX",
    "PRICE_REPORT_FILES",
    "PRICE_VERSION_REQUIRED_FILES",
    "PORTFOLIO_REPORT_FILES",
    "PORTFOLIO_VERSION_REQUIRED_FILES",
    "RUNTIME_ENV_FILE",
    "SIGNAL_SNAPSHOTS_SUFFIX",
    "STOCK_INVESTMENTS_SUFFIX",
    "TRADES_FILE",
    "entities_dir",
    "entity_file",
    "named_file",
]
