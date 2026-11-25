"""Trace 引擎的默认值。上报地址不在这里。

地址由外部模块登记。运行时覆盖（优先级从高到低）::

1. 环境变量 ``NTQ_TRACE_ENDPOINT`` / ``NTQ_TRACE_TIMEOUT`` 等
2. ``userspace/system/config/trace.json``（可选，仅 tunables，不含同意开关）
3. 已登记的发送端；没有登记就不发送

同意开关仍只走 ``trace_consent.json`` + ``NTQ_TRACE_ENABLED`` / ``NTQ_TRACE_SKIP``。
安装事件是否跳过同意，由登记发送端时的标志决定。
"""

from __future__ import annotations

from typing import Any, Dict


class TraceDefaults:
    """内置默认；勿在别处再硬编码同一套数字 / URL。"""

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
            "timeout_sec": cls.TIMEOUT_SEC,
            "queue_max": cls.QUEUE_MAX,
            "extreme_depth": cls.EXTREME_DEPTH,
            "max_attempts": cls.MAX_ATTEMPTS,
            "body_max_bytes": cls.BODY_MAX_BYTES,
            "bff_drain_interval_sec": cls.BFF_DRAIN_INTERVAL_SEC,
        }


__all__ = ["TraceDefaults"]
