"""
Rate limiter & API 限流相关助手。

职责：
- 提供基于固定时间窗口的 RateLimiter 实现；
- 聚合每个 ApiJob 的限流信息（优先 config，再看 provider，最后默认值）；
- 对外只暴露与 ApiJob / provider 相关的纯函数，不依赖具体执行器。
"""

import threading
import time
from typing import Dict, Any, List

from loguru import logger

from core.modules.data_source.data_class.api_job import ApiJob


class RateLimiter:
    """
    固定窗口限流器（每分钟请求数）。

    设计要点：
    - 窗口对齐到自然分钟（避免时间漂移）；
    - 窗口切换时有 buffer 冷却，避免边界突刺；
    - 使用条件变量 + 计数器，确保多线程下计数正确。
    """

    def __init__(self, max_per_minute: int, api_name: str = "default", wait_buffer_seconds: float = 5.0):
        self.max_per_minute = max_per_minute
        self.api_name = api_name
        self.wait_buffer_seconds = wait_buffer_seconds

        self.lock = threading.Lock()
        self.condition = threading.Condition(self.lock)
        self.window_start = self._current_window()
        self.count = 0
        self.window_cooldown_until = 0.0
        self._instance_id = hex(id(self))[-8:]

    def _current_window(self) -> int:
        """获取当前窗口的起始时间戳（对齐到自然分钟）。"""
        return int(time.time() // 60) * 60

    def acquire(self) -> None:
        """
        获取一次调用许可；如达到限制则阻塞直到下一窗口。
        """
        while True:
            now = time.time()
            current_window = self._current_window()

            with self.lock:
                # 窗口切换：重置计数并设置冷却期
                if current_window != self.window_start:
                    self.window_start = current_window
                    self.count = 0
                    self.window_cooldown_until = now + self.wait_buffer_seconds
                    self.condition.notify_all()

                # 冷却期内，等待 buffer 时间
                if now < self.window_cooldown_until:
                    sleep_time = self.window_cooldown_until - now
                    if sleep_time > 0:
                        logger.debug(f"⏳ {self.api_name}: 窗口冷却中，等待 {sleep_time:.2f}s")
                        self.condition.wait(timeout=sleep_time)
                        continue

                # 达到限制：等待到下一窗口 + buffer
                if self.count >= self.max_per_minute:
                    next_window_start = self.window_start + 60
                    sleep_time = next_window_start - now + self.wait_buffer_seconds
                    if sleep_time > 0:
                        logger.warning(
                            f"⏸️  {self.api_name}: 当前窗口已调用 "
                            f"{self.count}/{self.max_per_minute} 次，等待 {sleep_time:.1f}s 到下一窗口"
                        )
                        self.condition.wait(timeout=sleep_time)
                    else:
                        continue
                else:
                    # 还有配额，计数 +1 返回
                    self.count += 1
                    if self.count >= self.max_per_minute * 0.95:
                        logger.warning(
                            f"⚠️ {self.api_name}: 当前窗口已调用 "
                            f"{self.count}/{self.max_per_minute} 次（接近限制）"
                        )
                    return


_RATE_LIMITERS: Dict[str, RateLimiter] = {}
_RATE_LIMITERS_LOCK = threading.Lock()


def get_rate_limiter(
    provider_name: str,
    api_name: str,
    max_per_minute: int,
    wait_buffer_seconds: float = 5.0,
) -> RateLimiter:
    """
    获取或创建指定 (provider, api) 的 RateLimiter。

    - 使用 "PROVIDER:API" 作为全局 key；
    - 对限流值做 95% 安全折扣，避免逼近硬上限。
    """
    limiter_key = f"{provider_name}:{api_name}"

    # 安全折扣
    buffered_limit = int(max_per_minute * 0.95)
    if buffered_limit <= 0:
        buffered_limit = max_per_minute - 1 if max_per_minute > 1 else 1

    with _RATE_LIMITERS_LOCK:
        if limiter_key not in _RATE_LIMITERS:
            limiter = RateLimiter(
                max_per_minute=buffered_limit,
                api_name=limiter_key,
                wait_buffer_seconds=wait_buffer_seconds,
            )
            _RATE_LIMITERS[limiter_key] = limiter
            logger.info(
                f"🔧 创建 RateLimiter: {limiter_key}, "
                f"限流值: {buffered_limit}/分钟 (原始: {max_per_minute})"
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

