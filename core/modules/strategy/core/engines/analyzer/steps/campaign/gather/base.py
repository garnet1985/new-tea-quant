"""从命中的 {vid}/ 读 overall_report 和 effective_settings，拼成 N 行一张表。

不把每格展开成投资明细。旋钮以磁盘有效设置为准。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, ClassVar, Dict, List, Mapping, Optional, Sequence, Tuple

from core.modules.strategy.core.enums import SimulateKind
from core.modules.strategy.core.services.artifacts import ArtifactStore
from core.modules.strategy.core.services.artifacts.version_meta import VersionMetaStore

from ..attribute import AttributeStep
from ..contrasts import KnobContrasts
from ..metrics import READY
from ..plan import AttributionTask
from .enum_exits import exit_ratios_for_version

_ALL_LAYERS: Tuple[Tuple[SimulateKind, str], ...] = (
    (SimulateKind.ENUMERATE, "enumerate"),
    (SimulateKind.PRICE_FACTOR, "price_factor"),
    (SimulateKind.PORTFOLIO, "portfolio"),
)

_ENUM_KEYS = (
    "total_opportunities",
    "trigger_stocks",
    "trigger_ratio",
    "avg_per_stock",
    "completed_ratio",
    "cv",
    "mean_gap",
    "dispersion_conclusion",
    "opportunity_count_max",
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

_KEYS_BY_KIND = {
    SimulateKind.ENUMERATE: _ENUM_KEYS,
    SimulateKind.PRICE_FACTOR: _PRICE_KEYS,
    SimulateKind.PORTFOLIO: _PORTFOLIO_KEYS,
}


class GatherBase:
    """收集各 version 的层摘要。子类声明本层身份；读盘口径共用。"""

    LAYER: ClassVar[str] = ""
    KIND: ClassVar[SimulateKind] = SimulateKind.PORTFOLIO

    @classmethod
    def run(
        cls,
        folder: Path,
        tasks: Sequence[AttributionTask],
        executed: Mapping[str, Any],
    ) -> Dict[str, Any]:
        by_index = {task.cell.index: task for task in tasks}
        paths = AttributeStep.for_layer(cls.LAYER).filter_knobs(
            KnobContrasts.union_paths(task.cell.overlay for task in tasks)
        )
        rows: List[Dict[str, Any]] = []
        for raw in executed.get("cells") or []:
            if not isinstance(raw, dict):
                continue
            index = int(raw.get("index", -1))
            task = by_index.get(index)
            overlay = dict(task.cell.overlay) if task is not None else {}
            status = str(raw.get("status") or "")
            vid = str(raw.get("version_id") or "").strip() or None
            source: Any = task.cell.effective if task is not None else None
            if status in READY and vid:
                disk = VersionMetaStore.read_effective_settings(
                    ArtifactStore.simulations_root(folder), vid
                )
                if disk:
                    source = disk
            row: Dict[str, Any] = {
                "index": index,
                "status": status,
                "version_id": vid,
                "overlay": overlay,
                "knobs": KnobContrasts.read(source, paths),
                "layers": {},
            }
            if status in READY and vid:
                row["layers"] = cls._load_layers(folder, vid)
            rows.append(row)
        ready = [row for row in rows if row.get("status") in READY]
        return {
            "status": "ok" if ready else "empty",
            "row_count": len(rows),
            "ready_count": len(ready),
            "rows": rows,
        }

    @classmethod
    def _load_layers(cls, folder: Path, version_id: str) -> Dict[str, Any]:
        layers: Dict[str, Any] = {}
        for kind, key in _ALL_LAYERS:
            block = cls._read_layer(folder, version_id, kind)
            if kind is SimulateKind.ENUMERATE:
                block = attach_enum_exit_ratios(folder, version_id, block)
            layers[key] = block
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
        return compact_summary(kind, summary)


def compact_summary(kind: SimulateKind, summary: Mapping[str, Any]) -> Dict[str, Any]:
    keys = _KEYS_BY_KIND.get(kind, _PORTFOLIO_KEYS)
    out = {key: summary.get(key) for key in keys}
    if kind is SimulateKind.PRICE_FACTOR:
        # price_factor overall_report 把胜率写成 72.2（百分数）；战役表和资金层一样用 0–1。
        out["win_rate"] = _percent_to_ratio(out.get("win_rate"))
    if kind is SimulateKind.ENUMERATE:
        out["top_bucket_ratio"] = _top_bucket_ratio(summary)
    return out


def attach_enum_exit_ratios(
    folder: Path,
    version_id: str,
    layer_block: Optional[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """把出场比率并进 enumerate 层摘要。"""
    if not isinstance(layer_block, dict):
        return layer_block
    ratios = exit_ratios_for_version(folder, version_id)
    merged = dict(layer_block)
    for key, value in ratios.items():
        if key == "n_exits":
            continue
        merged[key] = value
    return merged


def _top_bucket_ratio(summary: Mapping[str, Any]) -> Optional[float]:
    """机会最多的那只票，其机会数占全部机会的比例。"""
    try:
        total = float(summary.get("total_opportunities"))
        top = float(summary.get("opportunity_count_max"))
    except (TypeError, ValueError):
        return None
    if total <= 0 or top < 0:
        return None
    return round(min(top, total) / total, 4)


def _percent_to_ratio(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value) / 100.0
    except (TypeError, ValueError):
        return None
