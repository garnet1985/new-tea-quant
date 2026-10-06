"""滚动窗口对照：同一套旋钮，不同区间。"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Mapping, Optional, Sequence

from ...consts import SCHEMA_VERSION
from ..campaign.labels import CampaignLabels

_PREFERRED = (
    ("portfolio", "total_return"),
    ("portfolio", "max_drawdown"),
    ("enumerate", "total_opportunities"),
)
_READY = frozenset({"hit", "simulated"})


class RollingSummarizeStep:
    """按窗口排序，相对第一段和上一段写差分。"""

    @classmethod
    def run(cls, gathered: Mapping[str, Any]) -> Dict[str, Any]:
        rows = [
            row
            for row in gathered.get("rows") or []
            if isinstance(row, dict) and row.get("status") in _READY
        ]
        n = len(rows)
        if n < 1:
            return {
                "schema_version": SCHEMA_VERSION,
                "status": "skipped",
                "reason": "insufficient_ready_rows",
                "n": n,
                "generated_at": datetime.now().isoformat(),
                "headline": "没有可对照的窗口（缓存未命中，这次也没补跑）。",
                "highlights": [],
                "windows": [],
            }
        items = [cls._window_item(row, rows[0] if i else None, rows[i - 1] if i else None) for i, row in enumerate(rows)]
        best = cls._best(items)
        return {
            "schema_version": SCHEMA_VERSION,
            "status": "ok" if n >= 2 else "partial",
            "n": n,
            "generated_at": datetime.now().isoformat(),
            "headline": cls._headline(items, best, n),
            "highlights": cls._highlights(items),
            "windows": items,
        }

    @classmethod
    def _window_item(
        cls,
        row: Mapping[str, Any],
        baseline: Optional[Mapping[str, Any]],
        previous: Optional[Mapping[str, Any]],
    ) -> Dict[str, Any]:
        knobs = row.get("knobs") if isinstance(row.get("knobs"), dict) else {}
        start = str(knobs.get("simulation.execution.start_date") or "").strip()
        end = str(knobs.get("simulation.execution.end_date") or "").strip()
        layers = row.get("layers") if isinstance(row.get("layers"), dict) else {}
        outcomes = cls._outcomes(layers)
        item: Dict[str, Any] = {
            "index": row.get("index"),
            "version_id": row.get("version_id"),
            "start": start,
            "end": end,
            "label": f"{start}-{end}" if start and end else str(row.get("version_id") or ""),
            "outcomes": outcomes,
        }
        if baseline is not None:
            item["vs_first"] = cls._delta_map(
                outcomes, cls._outcomes(baseline.get("layers") or {})
            )
        if previous is not None:
            item["vs_prev"] = cls._delta_map(
                outcomes, cls._outcomes(previous.get("layers") or {})
            )
        return item

    @classmethod
    def _outcomes(cls, layers: Mapping[str, Any]) -> Dict[str, Optional[float]]:
        out: Dict[str, Optional[float]] = {}
        for layer, key in _PREFERRED:
            block = layers.get(layer)
            if not isinstance(block, dict):
                out[f"{layer}.{key}"] = None
                continue
            out[f"{layer}.{key}"] = CampaignLabels.maybe_float(block.get(key))
        return out

    @classmethod
    def _delta_map(
        cls,
        current: Mapping[str, Optional[float]],
        reference: Mapping[str, Optional[float]],
    ) -> Dict[str, Optional[float]]:
        out: Dict[str, Optional[float]] = {}
        for key, value in current.items():
            base = reference.get(key)
            if value is None or base is None:
                out[key] = None
            else:
                out[key] = float(value) - float(base)
        return out

    @classmethod
    def _best(cls, items: Sequence[Mapping[str, Any]]) -> Optional[Mapping[str, Any]]:
        ranked: List[Mapping[str, Any]] = []
        for item in items:
            outcomes = item.get("outcomes") if isinstance(item.get("outcomes"), dict) else {}
            ret = CampaignLabels.maybe_float(outcomes.get("portfolio.total_return"))
            if ret is None:
                continue
            ranked.append(item)
        if not ranked:
            return None
        return max(
            ranked,
            key=lambda item: float(
                (item.get("outcomes") or {}).get("portfolio.total_return") or 0.0
            ),
        )

    @classmethod
    def _headline(
        cls,
        items: Sequence[Mapping[str, Any]],
        best: Optional[Mapping[str, Any]],
        n: int,
    ) -> str:
        if n == 1:
            only = items[0]
            return f"只落到 {only.get('label')} 这一段，还不能对照窗口。"
        if best is None:
            return f"对照了 {n} 段窗口，账户收益没有可比较的数字。"
        ret = CampaignLabels.format_number(
            "total_return",
            (best.get("outcomes") or {}).get("portfolio.total_return"),
        )
        return f"{n} 段窗口里，{best.get('label')} 账户收益最好（{ret}）。"

    @classmethod
    def _highlights(cls, items: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for item in items:
            vs_first = item.get("vs_first") if isinstance(item.get("vs_first"), dict) else {}
            delta = CampaignLabels.maybe_float(vs_first.get("portfolio.total_return"))
            if delta is None:
                continue
            out.append(
                {
                    "window": item.get("label"),
                    "outcome": "total_return",
                    "delta": delta,
                }
            )
        out.sort(key=lambda row: abs(float(row.get("delta") or 0.0)), reverse=True)
        return out[:3]
