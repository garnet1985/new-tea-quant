"""枚举器时间轴：全局 trade.calendar 解析（不往 job 里塞全量 points）。"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Sequence

from core.modules.backtest_engine.contracts import JobContext, Timeline
from core.modules.backtest_engine.core.shared.jobs import BacktestJob

logger = logging.getLogger(__name__)


class EnumeratorTimeline:
    """枚举器侧时间轴入口。

    - 规划侧：只写 ``timeline_point_count``（避免 pickle 全量 points）
    - 执行侧：从 job_context.init.global_data 的 trade.calendar 解析（SHM / 全局共享）
    """

    @classmethod
    def bind_point_count(cls, payload: Dict[str, Any], point_count: int) -> Dict[str, Any]:
        """规划用：写入 timeline_point_count，禁止注入全量 Timeline.points。"""
        if not isinstance(payload, dict):
            raise TypeError("payload 必须是 dict")
        if not isinstance(point_count, int) or point_count <= 0:
            raise ValueError("timeline_point_count 必须是正整数")
        payload[BacktestJob.TIMELINE_POINT_COUNT_KEY] = point_count
        # 禁止残留全量 timeline，避免误 pickle
        payload.pop(Timeline.PAYLOAD_KEY, None)
        return payload

    @classmethod
    def resolve_for_job(cls, job_context: JobContext) -> Timeline:
        """Worker 侧：从 init.global_data 的 trade.calendar 解析（兼容旧路径）。"""
        timeline = cls.default_from_trade_calendar(job_context)
        pad = cls._experiment_pad_points()
        if pad:
            timeline = timeline.with_prepended_points(pad)
        if not timeline.points:
            raise ValueError(
                "Timeline.points 为空：确保 trade.calendar 已加载到 global_data（SHM）"
            )
        return timeline

    @classmethod
    def from_global_cache(cls, cache: Any) -> Timeline:
        """主进程：用 GlobalEntityCache 已加载的 trade.calendar 构造轴（传给 BE timeline=）。"""
        from core.modules.data_contract import DATA_KEY

        calendar_data = list(cache.get_trade_calendar() or [])
        points: List[str] = [
            str(item.get("date") or "").strip()
            for item in calendar_data
            if item.get("is_open") and str(item.get("date") or "").strip()
        ]
        timeline = cls.from_open_points(
            points,
            meta={"source": "trade.calendar"},
        )
        pad = cls._experiment_pad_points()
        if pad:
            timeline = timeline.with_prepended_points(pad)
        if not timeline.points:
            raise ValueError(
                "Timeline.points 为空：GlobalEntityCache 未加载有效 trade.calendar"
            )
        return timeline

    @classmethod
    def default_from_trade_calendar(cls, job_context: JobContext) -> Timeline:
        """默认轴: kind=calendar，points=交易日历开市点（按 payload start/end 裁剪界）。"""
        from core.modules.data_contract import DATA_KEY

        loaded = job_context.init or {}
        global_data = loaded.get("global_data") or {}
        calendar_data = global_data.get(DATA_KEY.TRADE_CALENDAR, [])
        points: List[str] = [
            str(item.get("date") or "").strip()
            for item in calendar_data
            if item.get("is_open") and str(item.get("date") or "").strip()
        ]
        start = points[0] if points else ""
        end = points[-1] if points else ""
        period = cls._period_bounds_from_payload(job_context.payload or {})
        if period[0]:
            start = period[0]
        if period[1]:
            end = period[1]
        return Timeline.from_points(
            points,
            start=start,
            end=end,
            kind="calendar",
            meta={"source": "trade.calendar"},
        )

    @classmethod
    def from_open_points(
        cls,
        points: Sequence[str],
        *,
        start: str = "",
        end: str = "",
        meta: Optional[Dict[str, Any]] = None,
    ) -> Timeline:
        """由已解析的开市点构造 calendar Timeline（主进程规划计数用，不进 payload）。"""
        cleaned = [str(p).strip() for p in points if str(p).strip()]
        return Timeline.from_points(
            cleaned,
            start=start or (cleaned[0] if cleaned else ""),
            end=end or (cleaned[-1] if cleaned else ""),
            kind="calendar",
            meta=dict(meta or {"source": "trade.calendar"}),
        )

    @classmethod
    def _period_bounds_from_payload(cls, payload: Dict[str, Any]) -> tuple:
        start = str(payload.get("start_date") or "").strip()
        end = str(payload.get("end_date") or "").strip()
        if start and end:
            return start, end
        entity_shared = payload.get("entity_shared") or {}
        if isinstance(entity_shared, dict) and entity_shared:
            first = next(iter(entity_shared.values()), {}) or {}
            if isinstance(first, dict):
                return (
                    str(first.get("start") or "").strip(),
                    str(first.get("end") or "").strip(),
                )
        return "", ""

    @classmethod
    def _experiment_pad_points(cls) -> List[str]:
        """实验用空点垫片（NTQ_ENUM_PAD_EMPTY_START/END）；正式裁剪后可删。"""
        start_raw = str(os.environ.get("NTQ_ENUM_PAD_EMPTY_START") or "").strip()
        end_raw = str(os.environ.get("NTQ_ENUM_PAD_EMPTY_END") or "").strip()
        if not start_raw or not end_raw:
            return []
        try:
            start = datetime.strptime(start_raw, "%Y%m%d").date()
            end = datetime.strptime(end_raw, "%Y%m%d").date()
        except ValueError:
            logger.warning(
                "NTQ_ENUM_PAD_EMPTY_* 日期非法：start=%s end=%s",
                start_raw,
                end_raw,
            )
            return []
        if end < start:
            return []
        out: List[str] = []
        cur = start
        while cur <= end:
            if cur.weekday() < 5:
                out.append(cur.strftime("%Y%m%d"))
            cur += timedelta(days=1)
        return out


__all__ = ["EnumeratorTimeline"]
