"""枚举 Report 输出配置（performance_detail 等）。

本文件: ReportOutput
边界: enumerator 私有；不进 artifacts 布局服务
"""
from __future__ import annotations

from typing import Any, Dict


class ReportOutput:
    """枚举 report 输出配置解析（namespace）。"""

    DETAIL_SUMMARY = "summary"
    DETAIL_FULL = "full"

    @classmethod
    def resolve_performance_detail(cls, performance_config: dict | None) -> str:
        raw = str((performance_config or {}).get("performance_detail") or "").strip().lower()
        if raw in {cls.DETAIL_FULL, "full", "detailed", "jobs"}:
            return cls.DETAIL_FULL
        return cls.DETAIL_SUMMARY

    @classmethod
    def config_from_settings(cls, raw_settings: dict | None) -> dict:
        """从 strategy settings 读取 report 输出配置。"""
        settings = dict(raw_settings or {})
        output = settings.get("output") or {}
        report = output.get("report") or {}
        if isinstance(report, dict):
            return dict(report)
        return {}


__all__ = ["ReportOutput"]
