"""战役报告：N 个 version 一张表。"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Sequence

from .cells import AttributionCell, AttributionTask


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
    ) -> Dict[str, Any]:
        by_index = {
            int(row["index"]): row
            for row in executed.get("cells") or []
            if isinstance(row, dict) and "index" in row
        }
        return {
            "success": True,
            "folder": str(Path(folder).resolve()),
            "mode": "select" if config.is_select else "matrix",
            "steps": [k.value for k in config.steps],
            "kind": config.simulate_kind.value,
            "ignore_cache": executed.get("ignore_cache"),
            "cell_count": len(cells),
            "headline": summarized.get("headline"),
            "report": summarized,
            "cells": [
                {
                    "index": cell.index,
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
