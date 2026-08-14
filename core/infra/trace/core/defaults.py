"""Trace 模块内置默认值（唯一源）。

改内置上报地址：改本文件 ``TraceDefaults.TARGET_URL``。

运行时覆盖（优先级从高到低）::

1. 环境变量 ``NTQ_TRACE_ENDPOINT`` / ``NTQ_TRACE_TIMEOUT`` 等
2. ``userspace/system/config/trace.json``（可选，仅 tunables，不含同意开关）
3. 本文件默认值

同意开关仍只走 ``trace_consent.json`` + ``NTQ_TRACE_ENABLED`` / ``NTQ_TRACE_SKIP``。
"""

from __future__ import annotations

from typing import Any, Dict


class TraceDefaults:
    """内置默认；勿在别处再硬编码同一套数字 / URL。"""

    TARGET_URL: str = "https://www.new-tea.cn/api/v1/traces"
    TIMEOUT_SEC: float = 2.0
    QUEUE_MAX: int = 100
    EXTREME_DEPTH: int = 20
    MAX_ATTEMPTS: int = 10
    BODY_MAX_BYTES: int = 4096
    BFF_DRAIN_INTERVAL_SEC: int = 60

    # userspace/system/config/trace.json 允许覆盖的键
    USERSPACE_OVERRIDE_KEYS = frozenset(
        {
            "target_url",
            "timeout_sec",
            "queue_max",
            "extreme_depth",
            "max_attempts",
            "body_max_bytes",
            "bff_drain_interval_sec",
        }
    )

    @classmethod
    def as_dict(cls) -> Dict[str, Any]:
        return {
            "target_url": cls.TARGET_URL,
            "timeout_sec": cls.TIMEOUT_SEC,
            "queue_max": cls.QUEUE_MAX,
            "extreme_depth": cls.EXTREME_DEPTH,
            "max_attempts": cls.MAX_ATTEMPTS,
            "body_max_bytes": cls.BODY_MAX_BYTES,
            "bff_drain_interval_sec": cls.BFF_DRAIN_INTERVAL_SEC,
        }


__all__ = ["TraceDefaults"]
