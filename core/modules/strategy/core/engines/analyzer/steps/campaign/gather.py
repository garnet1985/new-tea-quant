"""从命中的 {vid}/ 读 overall_report，拼成 N 行一张表。

不跑 N 次 Analyzer.run；不把每格展开成投资明细。归因要的旋钮对照在 version 层。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

from core.modules.strategy.core.enums import SimulateKind
from core.modules.strategy.core.services.artifacts import ArtifactStore

from .cells import AttributionTask

_LAYERS = (
    (SimulateKind.ENUMERATE, "enumerate"),
    (SimulateKind.PRICE_FACTOR, "price_factor"),
    (SimulateKind.PORTFOLIO, "portfolio"),
)

_ENUM_KEYS = (
    "total_opportunities",
    "trigger_ratio",
    "avg_per_stock",
    "completed_ratio",
)
_PRICE_KEYS = (
    "win_rate",
    "avg_roi",
    "total_completed_investments",
    "total_profit",
)
_PORTFOLIO_KEYS = (
    "total_return",
    "win_rate",
    "max_drawdown",
    "capital_utilization_ratio_pct",
)

_READY = frozenset({"hit", "simulated"})


class GatherStep:
    """收集各 version 的三层摘要。"""

    @classmethod
    def run(
        cls,
        folder: Path,
        tasks: Sequence[AttributionTask],
        executed: Mapping[str, Any],
    ) -> Dict[str, Any]:
        by_index = {task.cell.index: task for task in tasks}
        rows: List[Dict[str, Any]] = []
        for raw in executed.get("cells") or []:
            if not isinstance(raw, dict):
                continue
            index = int(raw.get("index", -1))
            task = by_index.get(index)
            overlay = dict(task.cell.overlay) if task is not None else {}
            status = str(raw.get("status") or "")
            vid = str(raw.get("version_id") or "").strip() or None
            row: Dict[str, Any] = {
                "index": index,
                "status": status,
                "version_id": vid,
                "overlay": overlay,
                "knobs": _flatten_overlay(overlay),
                "layers": {},
            }
            if status in _READY and vid:
                row["layers"] = cls._load_layers(folder, vid)
            rows.append(row)
        ready = [row for row in rows if row.get("status") in _READY]
        return {
            "status": "ok" if ready else "empty",
            "row_count": len(rows),
            "ready_count": len(ready),
            "rows": rows,
        }

    @classmethod
    def _load_layers(cls, folder: Path, version_id: str) -> Dict[str, Any]:
        layers: Dict[str, Any] = {}
        for kind, key in _LAYERS:
            layers[key] = cls._read_layer(folder, version_id, kind)
        return layers

    @classmethod
    def _read_layer(
        cls,
        folder: Path,
        version_id: str,
        kind: SimulateKind,
    ) -> Optional[Dict[str, Any]]:
        try:
            store = ArtifactStore.resolve(folder, kind=kind, version_id=version_id)
        except FileNotFoundError:
            return None
        path = store.file("overall_report")
        if not path.is_file():
            return None
        try:
            payload = store.read_json("overall_report")
        except Exception:
            return None
        if not isinstance(payload, dict):
            return None
        summary = payload.get("summary")
        if not isinstance(summary, dict):
            return None
        return _compact_summary(kind, summary)


def _compact_summary(kind: SimulateKind, summary: Mapping[str, Any]) -> Dict[str, Any]:
    if kind is SimulateKind.ENUMERATE:
        keys = _ENUM_KEYS
    elif kind is SimulateKind.PRICE_FACTOR:
        keys = _PRICE_KEYS
    else:
        keys = _PORTFOLIO_KEYS
    return {key: summary.get(key) for key in keys}


def _flatten_overlay(value: Any, prefix: str = "") -> Dict[str, Any]:
    if isinstance(value, Mapping):
        out: Dict[str, Any] = {}
        for key, item in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            out.update(_flatten_overlay(item, path))
        return out
    if isinstance(value, list):
        out = {}
        for i, item in enumerate(value):
            out.update(_flatten_overlay(item, f"{prefix}.{i}"))
        return out
    if not prefix:
        return {}
    return {prefix: value}
