"""
Rate limiter & API 限流相关助手。

职责：
- 提供基于滑动时间窗口的 RateLimiter 实现（与 Tushare 等接口的滚动窗口一致）；
- 聚合每个 ApiJob 的限流信息（优先 config，再看 provider，最后默认值）；
- 对外只暴露与 ApiJob / provider 相关的纯函数，不依赖具体执行器。
"""

import threading
import time
from collections import deque
from typing import Dict, Any, List, Optional

from loguru import logger

from core.modules.data_source.data_class.api_job import ApiJob


class RateLimiter:
    """
    滑动窗口限流器（每分钟请求数）。

    设计要点：
    - 使用滑动 60 秒窗口，与 Tushare 等接口的滚动窗口一致，避免固定窗口在边界处的突刺；
    - 维护最近 60 秒内的请求时间戳，任意时刻「过去 60 秒内的请求数」不超过 max_per_minute；
    - 使用条件变量 + deque，确保多线程下计数正确。
    """

    def __init__(self, max_per_minute: int, api_name: str = "default", wait_buffer_seconds: float = 5.0):
        self.max_per_minute = max_per_minute
        self.api_name = api_name
        self.wait_buffer_seconds = wait_buffer_seconds

        self.lock = threading.Lock()
        self.condition = threading.Condition(self.lock)
        self._timestamps: deque = deque()  # 最近 60 秒内的请求时间戳
        self._block_logged_recently = 0.0  # 上次打「达到限制」日志的时间

    def _prune_old(self, now: float) -> None:
        """移除 60 秒前的时间戳。"""
        cutoff = now - 60.0
        while self._timestamps and self._timestamps[0] <= cutoff:
            self._timestamps.popleft()

    def acquire(self) -> None:
        """
        获取一次调用许可；如达到限制则阻塞直到滑动窗口内有空位。
        """
        while True:
            now = time.time()

            with self.lock:
                self._prune_old(now)

                if len(self._timestamps) >= self.max_per_minute:
                    # 必须等待：最早的时间戳离开 60 秒窗口
                    sleep_time = self._timestamps[0] + 60.0 - now + 0.01  # 额外 10ms 避免边界
                    if sleep_time > 0:
                        if now - self._block_logged_recently > 30:
                            self._block_logged_recently = now
                            logger.info(
                                f"⏸️  {self.api_name}: 滑动窗口内已达 {len(self._timestamps)}/{self.max_per_minute}，"
                                f"等待 {sleep_time:.1f}s"
                            )
                        self.condition.wait(timeout=min(sleep_time, 5.0))
                    continue

                self._timestamps.append(now)
                if len(self._timestamps) % 200 == 0:
                    logger.debug(f"RateLimiter {self.api_name}: 滑动窗口内已 {len(self._timestamps)}/{self.max_per_minute}")
                return


_RATE_LIMITERS: Dict[str, RateLimiter] = {}
_RATE_LIMITERS_LOCK = threading.Lock()


def get_rate_limiter(
    provider_name: str,
    api_name: str,
    max_per_minute: int,
    wait_buffer_seconds: float = 5.0,
    provider_rate_limit: Optional[int] = None,
) -> RateLimiter:
    """
    获取或创建指定 (provider, api) 的 RateLimiter。

    如果提供了 provider_rate_limit，则使用 provider 级别限流（所有 API 共享同一个限流器）。
    否则，使用 "PROVIDER:API" 作为 key，按 API 分别限流。

    - 对限流值做 95% 安全折扣，避免逼近硬上限。
    
    Args:
        provider_name: Provider 名称
        api_name: API 名称
        max_per_minute: API 级别的限流值
        wait_buffer_seconds: 等待缓冲时间（秒）
        provider_rate_limit: Provider 级别总体限流（如果提供，则所有 API 共享此限流器）
    """
    # 如果提供了 provider_rate_limit，使用 provider 级别限流
    if provider_rate_limit is not None:
        limiter_key = provider_name  # 使用 provider 名称作为 key
        effective_limit = provider_rate_limit
    else:
        limiter_key = f"{provider_name}:{api_name}"  # 使用 provider:api 作为 key
        effective_limit = max_per_minute

    # 安全折扣
    buffered_limit = int(effective_limit * 0.95)
    if buffered_limit <= 0:
        buffered_limit = effective_limit - 1 if effective_limit > 1 else 1

    with _RATE_LIMITERS_LOCK:
        if limiter_key not in _RATE_LIMITERS:
            limiter = RateLimiter(
                max_per_minute=buffered_limit,
                api_name=limiter_key,
                wait_buffer_seconds=wait_buffer_seconds,
            )
            _RATE_LIMITERS[limiter_key] = limiter
            logger.debug(
                f"RateLimiter: {limiter_key}, "
                f"{buffered_limit}/分钟"
                + (f" [Provider级别]" if provider_rate_limit is not None else "")
            )
        else:
            existing = _RATE_LIMITERS[limiter_key]
            if existing.max_per_minute != buffered_limit:
                logger.warning(
                    f"⚠️ RateLimiter {limiter_key} 已存在但限流值不一致: "
                    f"现有={existing.max_per_minute}, 请求={buffered_limit}"
                )

        return _RATE_LIMITERS[limiter_key]


def collect_api_limits(
    api_jobs: List[ApiJob],
    providers: Dict[str, Any],
    default_limit: int = 60,
) -> Dict[str, int]:
    """
    聚合每个 ApiJob 的限流信息。

    优先级：
    1. ApiJob.rate_limit（来自 handler config 的 max_per_minute，用户显式配置）；
    2. Provider.get_api_limit(api_name)（Provider 声明的官方硬限流，作为兜底）；
    3. 默认限流：default_limit（保守默认值）。
    """
    api_limits: Dict[str, int] = {}

    for job in api_jobs:
        job_id = job.job_id or job.api_name or job.method
        limit: int = 0

        # 1. 优先使用 ApiJob 自身的 rate_limit
        if getattr(job, "rate_limit", None):
            try:
                limit = int(job.rate_limit)
            except (TypeError, ValueError):
                limit = 0

        # 2. 其次尝试从 Provider 元数据中获取硬限流
        if not limit:
            provider = providers.get(job.provider_name)
            if provider and hasattr(provider, "get_api_limit"):
                api_name = job.api_name or job.method
                provider_limit = provider.get_api_limit(api_name)
                if provider_limit:
                    try:
                        limit = int(provider_limit)
                    except (TypeError, ValueError):
                        limit = 0

        # 3. 最后使用默认值
        if not limit:
            limit = default_limit

        api_limits[job_id] = limit

    return api_limits

