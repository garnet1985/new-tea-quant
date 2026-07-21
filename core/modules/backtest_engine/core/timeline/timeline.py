"""BacktestEngine 时间轴：契约、注入/发布、推进、worker 入口。

职责::

    - Timeline 值对象（points / clip / serialize）
    - 注入：set / clear / run(timeline=) 优先级
    - 默认：CalendarService 开市日轴
    - 发布：SharedMemory（失败则嵌入 payload.global）
    - 读取：read_for_job
    - 推进：drive / drive_for_job（调 on_tick）
    - TimelineWorkerExecute：process-pool 可 pickle 入口
"""
from __future__ import annotations

import logging
import pickle
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, ClassVar, Dict, List, Optional, Sequence, Tuple, Union

if TYPE_CHECKING:
    from core.modules.backtest_engine.core.shared.types import JobContext, RunCallbacks, TickFn

logger = logging.getLogger(__name__)

try:
    from multiprocessing.shared_memory import SharedMemory

    _SHM_AVAILABLE = True
except ImportError:
    SharedMemory = None  # type: ignore[misc, assignment]
    _SHM_AVAILABLE = False

TimelineInput = Union["Timeline", Sequence[str], None]
_idle_tick_warned = False


@dataclass(frozen=True)
class Timeline:
    """回测推进轴。

    - ``points``: 有序推进点（日 / 小时 / 事件 id 等，由 ``kind`` 解释）
    - ``start`` / ``end``: 可选裁剪界
    - ``kind``: ``calendar`` | ``clock`` | ``event`` | ``custom``

    类方法负责引擎侧：set / 默认 calendar / 探针前发布 / worker 读取。
    """

    # enumerator 等仍可把轴写在 payload["timeline"]
    PAYLOAD_KEY = "timeline"
    # 引擎发布：优先 SHM 引用；失败时整份嵌入
    SHM_KEY = "_engine_timeline_shm"
    EMBEDDED_KEY = "_engine_timeline"

    points: Tuple[str, ...] = field(default_factory=tuple)
    start: str = ""
    end: str = ""
    kind: str = "calendar"
    meta: Dict[str, Any] = field(default_factory=dict)

    # ── 主进程状态（一次 run）──
    _override: ClassVar[Optional["Timeline"]] = None
    _run_active: ClassVar[bool] = False
    _shm_name: ClassVar[Optional[str]] = None
    _shm_size: ClassVar[int] = 0

    # ── 构造 ──

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

    @classmethod
    def normalize(cls, timeline: TimelineInput) -> Optional["Timeline"]:
        if timeline is None:
            return None
        if isinstance(timeline, Timeline):
            if not timeline.points:
                raise ValueError("timeline.points 不能为空")
            return timeline
        points = [str(p).strip() for p in timeline if str(p).strip()]
        if not points:
            raise ValueError("timeline 日期列表不能为空")
        return cls.from_points(points, start=points[0], end=points[-1], kind="calendar")

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

    # ── 引擎：注入 / 默认 / 发布 ──

    @classmethod
    def set(cls, timeline: TimelineInput) -> None:
        """注入覆盖轴。应在 ``run`` / 探针前调用。"""
        if cls._run_active:
            logger.warning(
                "Timeline.set 应在 run/探针前调用；"
                "当前 run 已启动，本次设置不会影响本轮已发布的 timeline"
            )
        normalized = cls.normalize(timeline)
        if normalized is None:
            raise ValueError("Timeline.set 需要非空 Timeline 或日期列表")
        cls._override = normalized
        logger.info(
            "Timeline.set: points=%d start=%s end=%s",
            len(normalized.points),
            normalized.start,
            normalized.end,
        )

    @classmethod
    def clear(cls) -> None:
        """清除 Timeline.set 覆盖。"""
        if cls._run_active:
            logger.warning(
                "Timeline.clear 在 run 进行中调用；本轮已发布 timeline 不受影响"
            )
        cls._override = None

    @classmethod
    def default_from_calendar(cls, *, market: str = "SSE") -> "Timeline":
        """CalendarService：data.json 默认 start → latest completed 开市日。"""
        from core.infra.project_context import ProjectContext
        from core.modules.data_manager import DataManager

        data_mgr = DataManager(is_verbose=False)
        cal = data_mgr.service.calendar
        start = str(ProjectContext.config.get_default_start_date() or "").strip()
        end = str(cal.get_latest_completed_trading_date() or "").strip()
        if not start or not end:
            raise ValueError(
                f"默认 timeline 需要有效 start/end：start={start!r} end={end!r}"
            )
        points = list(cal.load_open_dates(start, end, market=market) or [])
        if not points:
            raise ValueError(
                f"CalendarService 未返回开市日：start={start} end={end} market={market}"
            )
        return cls.from_points(
            points,
            start=start,
            end=end,
            kind="calendar",
            meta={"source": "calendar_service", "market": market},
        )

    @classmethod
    def resolve(cls, timeline_arg: TimelineInput = None) -> "Timeline":
        """探针前解析：run 参数 > set > calendar 默认。"""
        from_run = cls.normalize(timeline_arg)
        if from_run is not None:
            logger.info("Timeline: 使用 run(timeline=) points=%d", len(from_run.points))
            return from_run
        if cls._override is not None:
            logger.info(
                "Timeline: 使用 Timeline.set points=%d",
                len(cls._override.points),
            )
            return cls._override
        default = cls.default_from_calendar()
        logger.info(
            "Timeline: 使用 CalendarService 默认轴 points=%d start=%s end=%s",
            len(default.points),
            default.start,
            default.end,
        )
        return default

    @classmethod
    def begin_run(
        cls,
        jobs: List[Dict[str, Any]],
        timeline_arg: TimelineInput = None,
    ) -> Tuple[List[Dict[str, Any]], "Timeline"]:
        """探针前：解析 → 发布 → stamp jobs。"""
        effective = cls.resolve(timeline_arg)
        cls._publish(effective)
        stamped = cls._stamp_jobs(jobs, effective)
        cls._run_active = True
        return stamped, effective

    @classmethod
    def end_run(cls) -> None:
        """run 结束：释放本轮 SHM。"""
        cls._unlink_shm()
        cls._run_active = False

    # ── worker 读 ──

    @classmethod
    def read_for_job(cls, payload: Optional[Dict[str, Any]]) -> Optional["Timeline"]:
        """Worker：读引擎发布的轴（SHM → 嵌入 → payload.timeline）。"""
        if not isinstance(payload, dict):
            return None
        global_block = payload.get("global")
        if isinstance(global_block, dict):
            shm_info = global_block.get(cls.SHM_KEY)
            if isinstance(shm_info, dict):
                timeline = cls._read_shm(shm_info)
                if timeline is not None:
                    return timeline
            embedded = global_block.get(cls.EMBEDDED_KEY)
            if embedded is not None:
                return cls.from_dict(embedded)
        raw = payload.get(cls.PAYLOAD_KEY)
        if raw is None:
            return None
        return cls.from_dict(raw)

    # ── 推进 ──

    @classmethod
    def drive_for_job(
        cls,
        job_context: "JobContext",
        *,
        on_tick: Optional["TickFn"] = None,
        on_ticks_complete: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """读 job 上已发布的轴并推进。"""
        timeline = cls.read_for_job(job_context.payload)
        if timeline is None:
            raise ValueError(
                "未找到引擎 timeline：请在探针前 Timeline.set / run(timeline=)，"
                "或依赖 CalendarService 默认轴"
            )
        return cls.drive(
            job_context,
            timeline,
            on_tick=on_tick,
            on_ticks_complete=on_ticks_complete,
        )

    @classmethod
    def drive(
        cls,
        job_context: "JobContext",
        timeline: "Timeline",
        *,
        on_tick: Optional["TickFn"] = None,
        on_ticks_complete: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """按 timeline.points 调 on_tick；缺省空转 + warning 一次。"""
        clipped = timeline.clipped()
        if not clipped.points:
            logger.warning(
                "Timeline.drive: 无有效 points（kind=%s start=%s end=%s）",
                timeline.kind,
                timeline.start,
                timeline.end,
            )
            result: Dict[str, Any] = {"success": True}
        else:
            for index, point in enumerate(clipped.points):
                cls._dispatch_tick(job_context, point, index, on_tick=on_tick)
            result = {"success": True}

        if on_ticks_complete is not None:
            extra = on_ticks_complete(job_context, clipped)
            if isinstance(extra, dict):
                result = {**result, **extra}
        return result

    @classmethod
    def _dispatch_tick(
        cls,
        job_context: "JobContext",
        point: str,
        index: int,
        *,
        on_tick: Optional["TickFn"],
    ) -> None:
        if on_tick is not None:
            on_tick(job_context, point, index)
            return
        global _idle_tick_warned
        if not _idle_tick_warned:
            logger.warning(
                "RunCallbacks.on_tick 未提供：时间轴将空转（仅 warning 一次）"
            )
            _idle_tick_warned = True

    # ── 内部：SHM / stamp ──

    @classmethod
    def _publish(cls, timeline: "Timeline") -> None:
        cls._unlink_shm()
        if not _SHM_AVAILABLE or SharedMemory is None:
            logger.warning("SharedMemory 不可用：timeline 将整份嵌入 payload.global")
            cls._shm_name = None
            cls._shm_size = 0
            return
        blob = pickle.dumps(timeline.to_dict(), protocol=pickle.HIGHEST_PROTOCOL)
        try:
            shm = SharedMemory(create=True, size=len(blob))
        except (PermissionError, OSError) as exc:
            logger.warning(
                "SharedMemory 创建失败（%s）：timeline 将整份嵌入 payload.global",
                exc,
            )
            cls._shm_name = None
            cls._shm_size = 0
            return
        shm.buf[: len(blob)] = blob
        cls._shm_name = shm.name
        cls._shm_size = len(blob)
        shm.close()
        logger.info(
            "Timeline SHM: name=%s size=%d points=%d",
            cls._shm_name,
            cls._shm_size,
            len(timeline.points),
        )

    @classmethod
    def _unlink_shm(cls) -> None:
        if not cls._shm_name or not _SHM_AVAILABLE or SharedMemory is None:
            cls._shm_name = None
            cls._shm_size = 0
            return
        try:
            shm = SharedMemory(name=cls._shm_name)
            shm.close()
            shm.unlink()
        except FileNotFoundError:
            pass
        except Exception as exc:
            logger.warning("Timeline SHM unlink 失败: %s", exc)
        cls._shm_name = None
        cls._shm_size = 0

    @classmethod
    def _stamp_jobs(cls, jobs: list, timeline: "Timeline") -> list:
        stamped = []
        for job in jobs:
            if not isinstance(job, dict):
                stamped.append(job)
                continue
            payload = dict(job.get("payload") or {})
            global_block = dict(payload.get("global") or {})
            if cls._shm_name and cls._shm_size > 0:
                global_block[cls.SHM_KEY] = {
                    "name": cls._shm_name,
                    "size": int(cls._shm_size),
                }
                global_block.pop(cls.EMBEDDED_KEY, None)
            else:
                global_block[cls.EMBEDDED_KEY] = timeline.to_dict()
                global_block.pop(cls.SHM_KEY, None)
            payload["global"] = global_block
            stamped.append({**job, "payload": payload})
        return stamped

    @classmethod
    def _read_shm(cls, shm_info: Dict[str, Any]) -> Optional["Timeline"]:
        if not _SHM_AVAILABLE or SharedMemory is None:
            return None
        name = str(shm_info.get("name") or "").strip()
        size = int(shm_info.get("size") or 0)
        if not name or size <= 0:
            return None
        shm = SharedMemory(name=name)
        try:
            raw = bytes(shm.buf[:size])
            return cls.from_dict(pickle.loads(raw))
        finally:
            shm.close()


class TimelineWorkerExecute:
    """可 pickle 的 process-pool 入口：``Timeline.drive_for_job`` + callbacks。"""

    def __init__(self, callbacks: Optional["RunCallbacks"] = None) -> None:
        from core.modules.backtest_engine.core.shared.types import RunCallbacks

        self.callbacks = callbacks or RunCallbacks()

    def __call__(self, job_context: "JobContext") -> Dict[str, Any]:
        return Timeline.drive_for_job(
            job_context,
            on_tick=self.callbacks.on_tick,
            on_ticks_complete=self.callbacks.on_ticks_complete,
        )


__all__ = ["Timeline", "TimelineInput", "TimelineWorkerExecute"]
