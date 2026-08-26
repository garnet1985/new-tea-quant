"""Analyzer artifact path constants (delegate to artifact service layout)."""
from __future__ import annotations

from pathlib import Path

from core.modules.strategy.core.services.artifacts.consts import (
    ANALYSIS_REPORT_JSON,
    ANALYSIS_SOURCE_JSON,
    ANALYSIS_SUBDIR,
)


class AnalyzerPaths:
    ANALYSIS_SUBDIR = ANALYSIS_SUBDIR
    SOURCE_JSON = ANALYSIS_SOURCE_JSON
    REPORT_JSON = ANALYSIS_REPORT_JSON
    SCHEMA_VERSION = "1"

    @classmethod
    def source_json(cls, output_dir: Path) -> Path:
        return Path(output_dir) / cls.ANALYSIS_SUBDIR / cls.SOURCE_JSON

    @classmethod
    def report_json(cls, output_dir: Path) -> Path:
        return Path(output_dir) / cls.ANALYSIS_SUBDIR / cls.REPORT_JSON

    @classmethod
    def report_ready(cls, output_dir: Path) -> bool:
        return cls.report_json(Path(output_dir)).is_file()
