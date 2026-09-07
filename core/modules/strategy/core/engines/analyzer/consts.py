"""Analyzer artifact layout (delegates to artifact service consts)."""
from __future__ import annotations

from pathlib import Path

from core.modules.strategy.core.services.artifacts.consts import (
    ANALYSIS_REPORT_JSON,
    ANALYSIS_SOURCE_JSON,
    ANALYSIS_SUBDIR,
)

SCHEMA_VERSION = "1"


def source_json(output_dir: Path) -> Path:
    return Path(output_dir) / ANALYSIS_SUBDIR / ANALYSIS_SOURCE_JSON


def report_json(output_dir: Path) -> Path:
    return Path(output_dir) / ANALYSIS_SUBDIR / ANALYSIS_REPORT_JSON


def report_ready(output_dir: Path) -> bool:
    return report_json(Path(output_dir)).is_file()
