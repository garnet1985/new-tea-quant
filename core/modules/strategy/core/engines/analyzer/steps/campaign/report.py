"""战役报告：N 个 version 一张表。overlays 与 matrix 各一张，最后并排。"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence

from .cells import AttributionCell, AttributionTask

_FAMILY_LABELS = {
    "overlays": "单因子",
    "matrix": "交叉",
    "select": "选号",
}


class CampaignReportStep:
    """组装战役返回体。落盘见 ``PersistStep``。"""

    @classmethod
    def run(
        cls,
        folder: Path,
        config: Any,
        cells: Sequence[AttributionCell],
        tasks: Sequence[AttributionTask],
        *,
        executed: Dict[str, Any],
        gathered: Dict[str, Any],
        attributed: Dict[str, Any],
        summarized: Dict[str, Any],
        family: str = "",
    ) -> Dict[str, Any]:
        by_index = {
            int(row["index"]): row
            for row in executed.get("cells") or []
            if isinstance(row, dict) and "index" in row
        }
        mode = family or config.parameter_mode
        return {
            "success": True,
            "folder": str(Path(folder).resolve()),
            "family": family,
            "mode": mode,
            "steps": [k.value for k in config.steps],
            "kind": config.simulate_kind.value,
            "ignore_cache": executed.get("ignore_cache"),
            "cell_count": len(cells),
            "headline": summarized.get("headline"),
            "report": summarized,
            "cells": [
                {
                    "index": cell.index,
                    "family": cell.family or family,
                    "version_id": (by_index.get(cell.index) or {}).get("version_id")
                    or cell.version_id,
                    "overlay": cell.overlay,
                    "execute_settings": cell.execute_settings,
                    "execute_status": (by_index.get(cell.index) or {}).get("status"),
                    "execute_reason": (by_index.get(cell.index) or {}).get("reason") or None,
                    "output_dir": (by_index.get(cell.index) or {}).get("output_dir"),
                }
                for cell in cells
            ],
            "task_count": len(tasks),
            "execute": {
                "status": executed.get("status"),
                "hits": executed.get("hits") or [],
                "simulated": executed.get("simulated") or [],
                "skipped": executed.get("skipped") or [],
            },
            "gather": {
                "status": gathered.get("status"),
                "row_count": gathered.get("row_count", 0),
                "ready_count": gathered.get("ready_count", 0),
            },
            "table": gathered.get("rows") or [],
            "attribute": {
                "status": attributed.get("status"),
                "n": attributed.get("n", 0),
                "varying_knobs": attributed.get("varying_knobs") or [],
                "layers": attributed.get("layers") or {},
                "contributions": attributed.get("contributions") or {},
            },
        }

    @classmethod
    def merge(
        cls,
        config: Any,
        executed: Mapping[str, Any],
        families: Mapping[str, Mapping[str, Any]],
        *,
        trades: Optional[Mapping[str, Any]] = None,
    ) -> Dict[str, Any]:
        items = [
            (name, dict(block))
            for name, block in families.items()
            if isinstance(block, Mapping)
        ]
        if len(items) == 1:
            out = dict(items[0][1])
            out["mode"] = config.parameter_mode
            if trades:
                out["trades"] = dict(trades)
            return out
        views: Dict[str, Dict[str, Any]] = {}
        headlines: list[str] = []
        all_cells: list[Any] = []
        tables: Dict[str, Any] = {}
        attributes: Dict[str, Any] = {}
        ready = 0
        cell_count = 0
        folder = ""
        for name, block in items:
            views[name] = _family_view(block)
            label = _FAMILY_LABELS.get(name, name)
            text = str(block.get("headline") or "").strip()
            if text:
                headlines.append(f"{label}：{text}")
            all_cells.extend(block.get("cells") or [])
            tables[name] = block.get("table") or []
            attributes[name] = block.get("attribute") or {}
            ready += int((block.get("gather") or {}).get("ready_count") or 0)
            cell_count += int(block.get("cell_count") or 0)
            folder = str(block.get("folder") or folder)
        headline = "；".join(headlines) if headlines else ""
        first = items[0][1]
        return {
            "success": True,
            "folder": folder or str(first.get("folder") or ""),
            "mode": config.parameter_mode,
            "steps": list(first.get("steps") or []),
            "kind": first.get("kind"),
            "ignore_cache": executed.get("ignore_cache"),
            "cell_count": cell_count,
            "headline": headline,
            "families": views,
            "report": {
                "headline": headline,
                "status": _merge_status(items),
                "overlays": views.get("overlays") or {},
                "matrix": views.get("matrix") or {},
            },
            "cells": all_cells,
            "task_count": int(executed.get("task_count") or 0),
            "execute": {
                "status": executed.get("status"),
                "hits": executed.get("hits") or [],
                "simulated": executed.get("simulated") or [],
                "skipped": executed.get("skipped") or [],
            },
            "gather": {
                "status": "ok" if ready else "empty",
                "row_count": cell_count,
                "ready_count": ready,
            },
            "table": tables,
            "attribute": attributes,
            "trades": dict(trades) if trades else {},
        }


def _family_view(block: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "family": block.get("family"),
        "mode": block.get("mode"),
        "headline": block.get("headline"),
        "cell_count": block.get("cell_count"),
        "report": block.get("report") or {},
        "table": block.get("table") or [],
        "attribute": block.get("attribute") or {},
        "cells": block.get("cells") or [],
        "gather": block.get("gather") or {},
        "execute": block.get("execute") or {},
        "highlights": (block.get("report") or {}).get("highlights") or [],
        "hints": (block.get("report") or {}).get("hints") or [],
        "contributions": (block.get("report") or {}).get("contributions")
        or (block.get("attribute") or {}).get("contributions")
        or {},
    }


def _merge_status(items: Sequence[tuple]) -> str:
    statuses: list[str] = []
    for _name, block in items:
        nested = block.get("report") if isinstance(block, Mapping) else None
        status = None
        if isinstance(nested, dict):
            status = nested.get("status")
        if not status and isinstance(block, Mapping):
            status = (block.get("attribute") or {}).get("status")
        if status:
            statuses.append(str(status))
    if any(item == "ok" for item in statuses) and all(
        item in ("ok", "partial") for item in statuses
    ):
        return "ok" if all(item == "ok" for item in statuses) else "partial"
    if any(item in ("ok", "partial") for item in statuses):
        return "partial"
    return "skipped"
