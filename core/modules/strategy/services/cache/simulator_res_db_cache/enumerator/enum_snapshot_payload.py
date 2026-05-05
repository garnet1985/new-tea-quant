#!/usr/bin/env python3
"""Enumerator-specific snapshot payload transforms (stored inside result_summary.enum)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from core.infra.project_context.path_manager import PathManager


def sanitize_enum_payload_for_snapshot(enum_payload: Dict[str, Any]) -> Dict[str, Any]:
    payload = dict(enum_payload or {})
    payload.pop("stockRows", None)
    return payload


def summary_row_to_storable_enum_payload(row: Dict[str, Any]) -> Dict[str, Any]:
    """Same shape as strategy workbench cache_helper._enum_summary_row_to_bff_payload."""
    if not isinstance(row, dict):
        row = {}
    out: Dict[str, Any] = {
        "opportunities": int(row.get("opportunities") or 0),
        "totalStocks": int(row.get("totalStocks") or 0),
        "triggerStocks": int(row.get("triggerStocks") or 0),
        "completedCount": int(row.get("completedCount") or 0),
        "unfinishedCount": int(row.get("unfinishedCount") or 0),
        "completionRate": float(row.get("completionRate") or 0.0),
    }
    version_dir = str(row.get("version_dir") or "").strip()
    if version_dir:
        out["versionDir"] = version_dir
    enum_metrics = row.get("enumMetrics")
    if isinstance(enum_metrics, dict):
        out["enumMetrics"] = enum_metrics
    stock_rows = row.get("stockRows")
    if isinstance(stock_rows, list):
        out["stockRows"] = stock_rows
    if row.get("strategy_name"):
        out["strategy_name"] = str(row.get("strategy_name") or "")
    if row.get("version_id") is not None:
        out["version_id"] = int(row.get("version_id") or 0)
    if row.get("elapsed_seconds") is not None:
        out["elapsed_seconds"] = float(row.get("elapsed_seconds") or 0.0)
    return out


def cached_storable_to_summary_row(strategy_name: str, cached: Dict[str, Any]) -> Dict[str, Any]:
    """Rebuild enumerate summary row (cf. OpportunityEnumeratorFlowImpl.build_result_summary)."""
    c = cached or {}
    vd = str(c.get("versionDir") or c.get("version_dir") or "").strip()
    return {
        "strategy_name": str(c.get("strategy_name") or strategy_name),
        "version_id": int(c.get("version_id") or 0),
        "version_dir": vd,
        "opportunities": int(c.get("opportunities") or 0),
        "totalStocks": int(c.get("totalStocks") or 0),
        "triggerStocks": int(c.get("triggerStocks") or 0),
        "completedCount": int(c.get("completedCount") or 0),
        "unfinishedCount": int(c.get("unfinishedCount") or 0),
        "completionRate": float(c.get("completionRate") or 0.0),
        "elapsed_seconds": float(c.get("elapsed_seconds") or 0.0),
    }


def resolve_enum_output_dir(strategy_name: str, version_dir_name: str) -> Optional[Path]:
    if not version_dir_name:
        return None
    output_candidate = PathManager.strategy_opportunity_enums(strategy_name, use_sampling=False) / version_dir_name
    if output_candidate.exists() and output_candidate.is_dir():
        return output_candidate
    sampling_candidate = PathManager.strategy_opportunity_enums(strategy_name, use_sampling=True) / version_dir_name
    if sampling_candidate.exists() and sampling_candidate.is_dir():
        return sampling_candidate
    return None


def load_enum_report_enrichment(strategy_name: str, enum_payload: Dict[str, Any]) -> Dict[str, Any]:
    version_dir_name = str(enum_payload.get("versionDir") or "").strip()
    output_dir = resolve_enum_output_dir(strategy_name, version_dir_name)
    if output_dir is None:
        return {}
    try:
        report_file = output_dir / "0_report_enum.json"
        if not report_file.exists():
            return {}
        payload = json.loads(report_file.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


__all__ = [
    "cached_storable_to_summary_row",
    "load_enum_report_enrichment",
    "resolve_enum_output_dir",
    "sanitize_enum_payload_for_snapshot",
    "summary_row_to_storable_enum_payload",
]
