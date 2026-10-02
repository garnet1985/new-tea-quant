"""把战役报告写到 ``results/attribution/{n}/{task}/``。

组号是短数字；``env_fp`` 只写在 ``meta.json`` / ``group_meta.json`` 里。
平时 Run 经 ``AttributionGroupStore.record_version`` 记账（含样本窗）。
战役结束时合并 ``tasks``，并保留已有 ``samples``。
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, ClassVar, Dict, List, Mapping, Optional, Sequence

from core.infra.project_context import ProjectContext
from core.modules.strategy.core.enums import SimulateKind
from core.modules.strategy.core.services.artifacts.io import ArtifactIO
from core.modules.strategy.core.services.fingerprint import FingerprintCalculator

from ..execute import ExecuteStep
from .groups import AttributionGroupStore

PARAMETER_TASK_ID = "parameter"
ROLLING_TASK_ID = "rolling"
GROUP_META_FILE = "group_meta.json"
REPORT_FILE = "report.json"
TABLE_FILE = "table.json"
ATTRIBUTE_FILE = "attribute.json"
TASK_META_FILE = "task_meta.json"


class PersistBase:
    """战役产物落盘。子类默认 ``task_id`` = ``LAYER``。"""

    LAYER: ClassVar[str] = ""
    KIND: ClassVar[SimulateKind] = SimulateKind.PORTFOLIO
    TASK_ID: ClassVar[str] = ""

    @classmethod
    def run(
        cls,
        folder: Path,
        config: Any,
        report: Mapping[str, Any],
        *,
        executed: Optional[Mapping[str, Any]] = None,
        task_id: str = "",
        task_kind: str = "",
    ) -> Dict[str, Any]:
        out = dict(report)
        env_fp = cls._resolve_env_fp(folder, executed or {})
        if not env_fp:
            out["persist"] = {
                "status": "skipped",
                "reason": "group_id_unavailable",
            }
            return out

        root = ProjectContext.path.get_strategy_attribution_directory(folder)
        group_id = AttributionGroupStore.resolve(root, env_fp)
        default_task = str(cls.TASK_ID or cls.LAYER or PARAMETER_TASK_ID).strip()
        task_key = str(task_id or default_task).strip() or default_task
        kind_key = str(task_kind or task_key).strip() or "parameter"
        group_dir = root / group_id
        task_dir = group_dir / task_key
        task_dir.mkdir(parents=True, exist_ok=True)

        generated_at = datetime.now().isoformat()
        report_path = _write_json(
            task_dir / REPORT_FILE,
            cls._report_payload(out, group_id, env_fp, task_key, generated_at),
        )
        _write_json(
            task_dir / TABLE_FILE,
            out.get("table") if out.get("table") is not None else [],
        )
        _write_json(task_dir / ATTRIBUTE_FILE, out.get("attribute") or {})
        _write_json(
            task_dir / TASK_META_FILE,
            cls._task_meta(
                out, config, group_id, env_fp, task_key, generated_at, kind=kind_key
            ),
        )
        group_meta_path = _write_json(
            group_dir / GROUP_META_FILE,
            cls._merge_group_meta(
                group_dir / GROUP_META_FILE,
                group_id,
                env_fp,
                task_key,
                out,
                generated_at,
                kind=kind_key,
            ),
        )

        out["group_id"] = group_id
        out["env_fp"] = env_fp
        out["task_id"] = task_key
        out["group_dir"] = str(group_dir.resolve())
        out["task_dir"] = str(task_dir.resolve())
        out["report_path"] = str(report_path.resolve())
        out["persist"] = {
            "status": "ok",
            "group_id": group_id,
            "env_fp": env_fp,
            "task_id": task_key,
            "group_dir": str(group_dir.resolve()),
            "task_dir": str(task_dir.resolve()),
            "group_meta_path": str(group_meta_path.resolve()),
            "report_path": str(report_path.resolve()),
        }
        return out

    @classmethod
    def _resolve_env_fp(
        cls,
        folder: Path,
        executed: Mapping[str, Any],
    ) -> Optional[str]:
        strategy_info = ExecuteStep._resolve_strategy_info(folder)
        if strategy_info is not None:
            return FingerprintCalculator.to_env_fingerprint(strategy_info)
        seen: List[str] = []
        for row in executed.get("cells") or []:
            if not isinstance(row, dict):
                continue
            fp = str(row.get("env_fp") or "").strip()
            if fp and fp not in seen:
                seen.append(fp)
        if len(seen) == 1:
            return seen[0]
        return None

    @classmethod
    def _report_payload(
        cls,
        report: Mapping[str, Any],
        group_id: str,
        env_fp: str,
        task_id: str,
        generated_at: str,
    ) -> Dict[str, Any]:
        summarized = dict(report.get("report") or {})
        families = report.get("families")
        if isinstance(families, dict) and families:
            summarized["overlays"] = families.get("overlays") or summarized.get("overlays") or {}
            summarized["matrix"] = families.get("matrix") or summarized.get("matrix") or {}
        if isinstance(report.get("trades"), dict) and report.get("trades"):
            summarized["trades"] = report.get("trades")
        summarized.update(
            {
                "group_id": group_id,
                "env_fp": env_fp,
                "task_id": task_id,
                "mode": report.get("mode"),
                "layer": report.get("layer") or report.get("kind") or cls.LAYER,
                "kind": report.get("kind") or cls.LAYER,
                "strategy_key": report.get("strategy_key")
                or Path(str(report.get("folder") or "")).name
                or None,
                "ignore_cache": report.get("ignore_cache"),
                "cell_count": report.get("cell_count"),
                "ready_count": (report.get("gather") or {}).get("ready_count", 0),
                "headline": report.get("headline") or summarized.get("headline"),
                "generated_at": summarized.get("generated_at") or generated_at,
            }
        )
        return summarized

    @classmethod
    def _task_meta(
        cls,
        report: Mapping[str, Any],
        config: Any,
        group_id: str,
        env_fp: str,
        task_id: str,
        generated_at: str,
        *,
        kind: str,
    ) -> Dict[str, Any]:
        cells: List[Dict[str, Any]] = []
        for cell in report.get("cells") or []:
            if not isinstance(cell, dict):
                continue
            row = {
                key: value
                for key, value in cell.items()
                if key != "execute_settings"
            }
            cells.append(row)
        return {
            "group_id": group_id,
            "env_fp": env_fp,
            "task_id": task_id,
            "kind": kind,
            "mode": report.get("mode"),
            "layer": report.get("layer") or report.get("kind") or cls.LAYER,
            "simulate_kind": report.get("kind")
            or getattr(config, "layer", None)
            or cls.LAYER
            or "portfolio",
            "ignore_cache": report.get("ignore_cache"),
            "generated_at": generated_at,
            "cell_count": report.get("cell_count"),
            "cells": cells,
            "execute": report.get("execute") or {},
            "gather": report.get("gather") or {},
        }

    @classmethod
    def _merge_group_meta(
        cls,
        path: Path,
        group_id: str,
        env_fp: str,
        task_id: str,
        report: Mapping[str, Any],
        generated_at: str,
        *,
        kind: str,
    ) -> Dict[str, Any]:
        existing: Dict[str, Any] = {}
        if path.is_file():
            try:
                loaded = ArtifactIO.read_json(path)
            except (OSError, json.JSONDecodeError, ValueError, TypeError):
                loaded = {}
            if isinstance(loaded, dict):
                existing = loaded

        versions = sorted(
            _union_strings(existing.get("versions"), _ready_version_ids(report)),
            key=_version_sort_key,
        )
        tasks_by_id: Dict[str, Dict[str, Any]] = {}
        for item in existing.get("tasks") or []:
            if not isinstance(item, dict):
                continue
            existing_id = str(item.get("task_id") or "").strip()
            if existing_id:
                tasks_by_id[existing_id] = dict(item)
        tasks_by_id[task_id] = {
            "task_id": task_id,
            "kind": kind,
            "mode": report.get("mode"),
            "updated_at": generated_at,
            "headline": report.get("headline"),
            "cell_count": report.get("cell_count"),
            "ready_count": (report.get("gather") or {}).get("ready_count", 0),
        }
        return {
            "group_id": group_id,
            "env_fp": env_fp,
            "updated_at": generated_at,
            "versions": versions,
            "samples": list(existing.get("samples") or []),
            "tasks": list(tasks_by_id.values()),
        }


def _ready_version_ids(report: Mapping[str, Any]) -> List[str]:
    ready = set()
    for cell in _iter_cell_rows(report):
        status = str(cell.get("execute_status") or cell.get("status") or "")
        if status not in {"hit", "simulated"}:
            continue
        vid = str(cell.get("version_id") or "").strip()
        if vid:
            ready.add(vid)
    return sorted(ready, key=_version_sort_key)


def _iter_cell_rows(report: Mapping[str, Any]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for cell in report.get("cells") or []:
        if isinstance(cell, dict):
            rows.append(cell)
    table = report.get("table")
    if isinstance(table, list):
        rows.extend(item for item in table if isinstance(item, dict))
    elif isinstance(table, dict):
        for group in table.values():
            if isinstance(group, list):
                rows.extend(item for item in group if isinstance(item, dict))
    families = report.get("families")
    if isinstance(families, dict):
        for block in families.values():
            if not isinstance(block, dict):
                continue
            for cell in block.get("cells") or []:
                if isinstance(cell, dict):
                    rows.append(cell)
            for row in block.get("table") or []:
                if isinstance(row, dict):
                    rows.append(row)
    return rows


def _union_strings(*groups: Any) -> List[str]:
    seen: List[str] = []
    for group in groups:
        if not isinstance(group, Sequence) or isinstance(group, (str, bytes)):
            continue
        for item in group:
            text = str(item or "").strip()
            if text and text not in seen:
                seen.append(text)
    return seen


def _version_sort_key(vid: str) -> Any:
    try:
        return (0, int(vid))
    except (TypeError, ValueError):
        return (1, vid)


def _write_json(path: Path, payload: Any) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    return target
