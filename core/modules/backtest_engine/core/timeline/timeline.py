"""BacktestEngine 时间轴契约（中性推进点；非 trade-calendar 专属）。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple


@dataclass(frozen=True)
class Timeline:
    """回测推进轴。

    - ``points``: 有序推进点（日 / 小时 / 事件 id 等，由 ``kind`` 解释）
    - ``start`` / ``end``: 可选裁剪界（与 point 同序可比较的字符串）
    - ``kind``: ``calendar`` | ``clock`` | ``event`` | ``custom``
    - 默认业务约定: ``kind=calendar`` 且 points = calendar 最小时间点（如交易日）
    """

    PAYLOAD_KEY = "timeline"

    points: Tuple[str, ...] = field(default_factory=tuple)
    start: str = ""
    end: str = ""
    kind: str = "calendar"
    meta: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_points(
        cls,
        points: Sequence[str],
        *,
        start: str = "",
        end: str = "",
        kind: str = "calendar",
        meta: Optional[Dict[str, Any]] = None,
    ) -> "Timeline":
        cleaned = tuple(str(p).strip() for p in points if str(p).strip())
        return cls(
            points=cleaned,
            start=str(start or "").strip(),
            end=str(end or "").strip(),
            kind=str(kind or "calendar").strip() or "calendar",
            meta=dict(meta or {}),
        )

    @classmethod
    def from_dict(cls, raw: Any) -> "Timeline":
        if isinstance(raw, Timeline):
            return raw
        if not isinstance(raw, dict):
            raise ValueError("Timeline.from_dict 需要 dict")
        points = raw.get("points")
        if not isinstance(points, (list, tuple)):
            raise ValueError("Timeline.points 必须是 list/tuple")
        return cls.from_points(
            points,
            start=str(raw.get("start") or ""),
            end=str(raw.get("end") or ""),
            kind=str(raw.get("kind") or "calendar"),
            meta=dict(raw.get("meta") or {})
            if isinstance(raw.get("meta"), dict)
            else {},
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "points": list(self.points),
            "start": self.start,
            "end": self.end,
            "kind": self.kind,
            "meta": dict(self.meta),
        }

    def clipped(self) -> "Timeline":
        """按 start/end 裁剪 points（空界表示不裁该侧）。"""
        start = self.start
        end = self.end
        if not start and not end:
            return self
        out: List[str] = []
        for point in self.points:
            if start and point < start:
                continue
            if end and point > end:
                continue
            out.append(point)
        return Timeline(
            points=tuple(out),
            start=start,
            end=end,
            kind=self.kind,
            meta=dict(self.meta),
        )

    @classmethod
    def from_payload(cls, payload: Optional[Dict[str, Any]]) -> Optional["Timeline"]:
        """从 job payload 读取显式注入的 timeline；未注入返回 None。"""
        if not isinstance(payload, dict):
            return None
        raw = payload.get(cls.PAYLOAD_KEY)
        if raw is None:
            return None
        return cls.from_dict(raw)

    @classmethod
    def require_from_payload(cls, payload: Optional[Dict[str, Any]]) -> "Timeline":
        timeline = cls.from_payload(payload)
        if timeline is None:
            raise ValueError(
                f"payload 缺少 {cls.PAYLOAD_KEY!r}：请显式注入 Timeline"
            )
        if not timeline.points:
            raise ValueError(f"payload[{cls.PAYLOAD_KEY!r}].points 不能为空")
        return timeline

    def with_prepended_points(self, extra: Sequence[str]) -> "Timeline":
        prefix = tuple(str(p).strip() for p in extra if str(p).strip())
        if not prefix:
            return self
        return Timeline(
            points=prefix + self.points,
            start=prefix[0],
            end=self.end or (self.points[-1] if self.points else prefix[-1]),
            kind=self.kind,
            meta=dict(self.meta),
        )


__all__ = ["Timeline"]
