"""Analyzer artifact path constants and helpers."""
from __future__ import annotations

from pathlib import Path


class AnalyzerPaths:
    ANALYSIS_SUBDIR = "analysis"
    SOURCE_JSON = "source.json"
    REPORT_JSON = "report.json"
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
