"""抓取写入的字节预算：缓冲区、在飞请求、一块写库记录共用一份余量。"""
from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# 写库时一块记录的预留。不随机器变大。
WRITE_RESERVE_BYTES = 8 * 1024 * 1024
# 无 psutil 时的紧预算，避免退回旧的数 GB 下限。
FALLBACK_BUDGET_BYTES = 64 * 1024 * 1024
# 缓冲区硬顶。预算按「当时可用内存」算时，小机器上会接近 2GB，
# 第一笔落库发生前进程就已经被 OOM 杀掉。
MAX_BUFFER_BYTES = 128 * 1024 * 1024
# 探测不到总内存时，进程 RSS 到这里就先落库。
FALLBACK_RSS_LIMIT_BYTES = 512 * 1024 * 1024


def probe_budget_bytes() -> int:
    """可用内存减去 floor 后再乘 worker 比例。不套用 256MB / 1024MB 下限。"""
    from core.infra.machine_capacity import MachineInfo

    _total, available = MachineInfo.virtual_memory_mb()
    floor = MachineInfo.resolve_memory_floor({})
    if available is None:
        return FALLBACK_BUDGET_BYTES
    usable_mb = max(0.0, float(available) - float(floor))
    budget_mb = usable_mb * MachineInfo.DEFAULT_WORKER_MEMORY_FRACTION
    return max(0, int(budget_mb * 1024 * 1024))


def probe_rss_limit_bytes() -> int:
    """本进程 RSS 达到此值就先落库，给 Apache 和数据库留出内存。"""
    from core.infra.machine_capacity import MachineInfo

    total, _available = MachineInfo.virtual_memory_mb()
    if total is None:
        return FALLBACK_RSS_LIMIT_BYTES
    total_bytes = int(float(total) * 1024 * 1024)
    # 至少留 1.5GB；大机器上本进程不超过总内存的 40%。
    leave = max(1536 * 1024 * 1024, int(total_bytes * 0.60))
    return max(256 * 1024 * 1024, total_bytes - leave)


def _cpu_cap() -> int:
    from core.infra.machine_capacity import MachineInfo

    cpu = max(1, int(MachineInfo.get_cpu_count() or 1))
    reserve = MachineInfo.get_reserve_cores({})
    reserve = max(0, min(int(reserve), cpu - 1))
    return max(1, cpu - reserve)


def _process_rss_bytes() -> int:
    try:
        import psutil
    except ImportError:
        return 0
    try:
        return int(psutil.Process().memory_info().rss)
    except (AttributeError, OSError):
        return 0


class SaveMemoryBudget:
    """同一数据源内按已见过的最大单笔拆分在飞请求数和缓冲区。"""

    def __init__(
        self,
        budget_bytes: Optional[int] = None,
        *,
        write_reserve_bytes: int = WRITE_RESERVE_BYTES,
        cpu_cap: Optional[int] = None,
        rss_limit_bytes: Optional[int] = None,
    ) -> None:
        self.write_reserve_bytes = max(0, int(write_reserve_bytes))
        self.cpu_cap = max(1, int(cpu_cap if cpu_cap is not None else _cpu_cap()))
        self.budget_bytes = max(0, int(budget_bytes if budget_bytes is not None else probe_budget_bytes()))
        if rss_limit_bytes is None:
            # 测试传入预算时不读本机 RSS，避免把测试进程的内存当成压力。
            self.rss_limit_bytes = 0 if budget_bytes is not None else probe_rss_limit_bytes()
        else:
            self.rss_limit_bytes = max(0, int(rss_limit_bytes))
        self.frame_bytes = 0
        self.in_flight = 1
        self.buffer_cap = 0
        self._warned_oversize = False
        self._recompute()
        logger.info(
            "写入预算 %s MB，线程上限 %s，在飞 %s，缓冲区 %s MB",
            round(self.budget_bytes / (1024 * 1024), 1),
            self.cpu_cap,
            self.in_flight,
            round(self.buffer_cap / (1024 * 1024), 1),
        )

    def current_in_flight(self) -> int:
        return self.in_flight

    def observe(self, nbytes: int) -> None:
        size = max(0, int(nbytes))
        if size > self.frame_bytes:
            self.frame_bytes = size
            self._recompute()

    def over_rss(self) -> bool:
        """进程占用已经达到上限。调用方应先把缓冲区落库。"""
        if self.rss_limit_bytes <= 0:
            return False
        rss = _process_rss_bytes()
        return rss > 0 and rss >= self.rss_limit_bytes

    def note_rss(self) -> None:
        rss = _process_rss_bytes()
        if rss <= 0 or rss <= self.budget_bytes:
            return
        overshoot = rss - self.budget_bytes
        floor = self.write_reserve_bytes + self.frame_bytes
        self.budget_bytes = max(floor, self.budget_bytes - overshoot)
        self._recompute()
        logger.info(
            "进程 RSS 超过预算，写入预算降到 %s MB",
            round(self.budget_bytes / (1024 * 1024), 1),
        )

    def warn_if_frame_exceeds(self, nbytes: int) -> None:
        if self._warned_oversize or nbytes <= self.budget_bytes:
            return
        self._warned_oversize = True
        logger.warning(
            "单笔结果 %s MB 超过写入预算 %s MB，将单独写入",
            round(nbytes / (1024 * 1024), 1),
            round(self.budget_bytes / (1024 * 1024), 1),
        )

    def _recompute(self) -> None:
        reserve = self.write_reserve_bytes
        size = self.frame_bytes
        if size <= 0:
            self.in_flight = 1
            self.buffer_cap = max(0, self.budget_bytes - reserve)
        else:
            room = self.budget_bytes - reserve - size
            if room < size:
                self.in_flight = 1
                self.buffer_cap = size
            else:
                self.in_flight = min(self.cpu_cap, max(1, room // size))
                self.buffer_cap = self.budget_bytes - reserve - self.in_flight * size
                if self.buffer_cap < size:
                    self.buffer_cap = size
        if self.buffer_cap > MAX_BUFFER_BYTES:
            self.buffer_cap = MAX_BUFFER_BYTES
