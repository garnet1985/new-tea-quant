"""从枚举 overall_report + entities 收集层诊断事实。"""
from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional, Sequence

from core.infra.utils import Utils
from core.modules.strategy.core.engines.analyzer.steps.layer.consts import (
    EXIT_LABELS,
    PAPER_PATH_DISCLAIMER,
    TOP_N,
)
from core.modules.strategy.core.engines.analyzer.steps.layer.leftover import inspect_leftover
from core.modules.strategy.core.engines.enumerator.common.report_manager.overall_report import (
    OverallReport,
    OverallSummary,
)
from core.modules.strategy.core.engines.shared.enum_result_contract import (
    EnumResult,
    EnumResultsManager,
)
from core.modules.strategy.core.services.artifacts import ArtifactStore
from core.modules.strategy.core.services.artifacts.version_meta import VersionMetaStore


class EnumerateGather:
    """单 version 枚举事实；不含对照格、不含 SHAP。"""

    @classmethod
    def run(cls, store: ArtifactStore) -> Dict[str, Any]:
        rows = cls._load_rows(store)
        summary = cls._load_summary(store)
        return {
            "disclaimer": PAPER_PATH_DISCLAIMER,
            "quantity": cls._quantity(summary, rows),
            "time": cls._time(summary, rows),
            "exits": cls._exits(rows),
            "leftover_upside": inspect_leftover(cls._goal_from_store(store)),
            "gates": {"needs_overlay": True},
        }

    @staticmethod
    def _load_rows(store: ArtifactStore) -> List[EnumResult]:
        manager = EnumResultsManager.at(store.output_dir)
        ids = manager.list_entities()
        return manager.for_entities(ids)

    @staticmethod
    def _load_summary(store: ArtifactStore) -> OverallSummary:
        path = store.file("overall_report")
        if not path.is_file():
            return OverallSummary()
        return OverallReport.load(store.output_dir).summary

    @staticmethod
    def _goal_from_store(store: ArtifactStore) -> Dict[str, Any]:
        version_dir = store.output_dir.parent
        root = version_dir.parent
        vid = str(store.version_id or version_dir.name or "").strip()
        if not vid:
            return {}
        payload = VersionMetaStore.read_effective_settings(root, vid) or {}
        goal = payload.get("goal")
        return dict(goal) if isinstance(goal, dict) else {}

    @classmethod
    def _quantity(cls, summary: OverallSummary, rows: Sequence[EnumResult]) -> Dict[str, Any]:
        total = int(summary.total_opportunities or len(rows))
        by_entity = Counter(str(row.entity_id) for row in rows if str(row.entity_id or "").strip())
        ranked = by_entity.most_common(TOP_N)
        top5 = sum(count for _, count in by_entity.most_common(TOP_N))
        return {
            "total_opportunities": total,
            "total_stocks": int(summary.total_stocks or 0),
            "trigger_stocks": int(summary.trigger_stocks or len(by_entity)),
            "trigger_ratio": float(summary.trigger_ratio or 0.0),
            "avg_per_stock": float(summary.avg_per_stock or 0.0),
            "completed_count": int(summary.completed_count or 0),
            "unfinished_count": int(summary.unfinished_count or 0),
            "completed_ratio": float(summary.completed_ratio or 0.0),
            "opportunity_buckets": summary.opportunity_buckets.to_dict(),
            "top_stocks": [
                {
                    "entity_id": eid,
                    "count": count,
                    "share": _share(count, total),
                }
                for eid, count in ranked
            ],
            "top5_share": _share(top5, total),
        }

    @classmethod
    def _time(cls, summary: OverallSummary, rows: Sequence[EnumResult]) -> Dict[str, Any]:
        timing = summary.timing
        months = Counter(_month_key(row.trigger_date) for row in rows)
        months.pop("", None)
        month_total = sum(months.values())
        ranked = months.most_common()
        peak_month, peak_count = ranked[0] if ranked else ("", 0)
        return {
            "calendar": {
                "months": [
                    {
                        "month": month,
                        "count": count,
                        "share": _share(count, month_total),
                    }
                    for month, count in ranked
                ],
                "peak_month": peak_month,
                "peak_share": _share(peak_count, month_total),
            },
            "per_stock": {
                "mean_gap": float(timing.mean_gap or 0.0),
                "cv": float(timing.cv or 0.0),
                "dispersion_conclusion": str(timing.dispersion_conclusion or ""),
            },
        }

    @classmethod
    def _exits(cls, rows: Sequence[EnumResult]) -> Dict[str, Any]:
        completed = [row for row in rows if row.is_complete()]
        by_reason: Dict[str, List[EnumResult]] = defaultdict(list)
        for row in completed:
            reason = str(row.exit_reason or "").strip() or "unknown"
            by_reason[reason].append(row)
        total = len(completed)
        mix = [
            cls._reason_row(reason, group, total)
            for reason, group in sorted(
                by_reason.items(), key=lambda item: (-len(item[1]), item[0])
            )
        ]
        sl_rows = by_reason.get("stop_loss") or []
        return {
            "completed_count": total,
            "by_reason": mix,
            "stop_loss_share": _share(len(sl_rows), total),
            "take_profit_share": _share(len(by_reason.get("take_profit") or []), total),
            "expiration_share": _share(len(by_reason.get("expired") or []), total),
            "concentrated_stop_loss": _top_entities(sl_rows, total=len(sl_rows)),
            "stop_loss_by_month": _month_rows(sl_rows),
        }

    @staticmethod
    def _reason_row(
        reason: str, group: Sequence[EnumResult], total: int
    ) -> Dict[str, Any]:
        rois = [float(row.weighted_roi or 0.0) for row in group]
        days = [float(row.holding_days or 0) for row in group]
        return {
            "reason": reason,
            "label": EXIT_LABELS.get(reason, reason),
            "count": len(group),
            "share": _share(len(group), total),
            "mean_roi": _mean(rois),
            "mean_holding_days": _mean(days),
        }


def _share(part: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round(float(part) / float(total), 4)


def _mean(values: Sequence[float]) -> Optional[float]:
    if not values:
        return None
    return round(sum(values) / len(values), 4)


def _month_key(raw: Any) -> str:
    text = Utils.date.normalize_str(str(raw or "")) if raw else ""
    if not isinstance(text, str) or len(text) < 6:
        return ""
    return f"{text[:4]}-{text[4:6]}"


def _top_entities(rows: Sequence[EnumResult], *, total: int) -> List[Dict[str, Any]]:
    counts = Counter(str(row.entity_id) for row in rows if str(row.entity_id or "").strip())
    return [
        {"entity_id": eid, "count": count, "share": _share(count, total)}
        for eid, count in counts.most_common(TOP_N)
    ]


def _month_rows(rows: Sequence[EnumResult]) -> List[Dict[str, Any]]:
    months = Counter(_month_key(row.trigger_date) for row in rows)
    months.pop("", None)
    total = sum(months.values())
    return [
        {"month": month, "count": count, "share": _share(count, total)}
        for month, count in months.most_common()
    ]
