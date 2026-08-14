"""K 线 bar 安全取值（缺/坏字段不中断 pipeline）。

消费者: scanner, enumerator, price_factor
其它: Investment tick

本文件:
- SafeBarValue: 从 bar / bar[\"raw\"] 读 float；失败时用 default 并 warning
  边界: 只负责安全取值；不负责成交、贴板业务或 DataManager 装载
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class SafeBarValue:
    """从 K 线 dict 安全取数。

    约定: 顶层为前复权；``bar[\"raw\"]`` 为不复权。
    职责: 缺字段 / 坏类型时给 default（或 ``None``）并打 warning，避免挂掉 tick/pipeline。
    """

    @classmethod
    def float(
        cls,
        bar: Any,
        key: str,
        *,
        use_raw: bool = False,
        default: float = 0.0,
    ) -> float:
        """必取浮点；失败返回 ``default`` 并 warning。"""
        source, src_err = cls._source(bar, use_raw=use_raw)
        if source is None:
            cls._warn(key, use_raw=use_raw, reason=src_err or "no source", default=default)
            return float(default)
        if key not in source or source.get(key) in (None, ""):
            cls._warn(key, use_raw=use_raw, reason="missing", default=default)
            return float(default)
        try:
            return float(source[key])
        except (TypeError, ValueError):
            cls._warn(
                key,
                use_raw=use_raw,
                reason=f"not numeric: {source.get(key)!r}",
                default=default,
            )
            return float(default)

    @classmethod
    def optional_float(
        cls,
        bar: Any,
        key: str,
        *,
        use_raw: bool = False,
    ) -> Optional[float]:
        """可选浮点；缺失返回 ``None``（不 warning）；坏类型 warning 后返回 ``None``。"""
        source, src_err = cls._source(bar, use_raw=use_raw)
        if source is None:
            if src_err:
                cls._warn(key, use_raw=use_raw, reason=src_err, default=None)
            return None
        if key not in source or source.get(key) in (None, ""):
            return None
        try:
            return float(source[key])
        except (TypeError, ValueError):
            cls._warn(
                key,
                use_raw=use_raw,
                reason=f"not numeric: {source.get(key)!r}",
                default=None,
            )
            return None

    @classmethod
    def volume(cls, bar: Any) -> Optional[float]:
        """成交量（股）；缺失/非正 → ``None``（缺失不 warning）。"""
        vol = cls.optional_float(bar, "volume", use_raw=False)
        if vol is None or vol <= 0:
            return None
        return vol

    @classmethod
    def price_for_model(
        cls,
        bar: Any,
        model: str,
        *,
        use_raw: bool = False,
        default: float = 0.0,
    ) -> float:
        """按 tradability 价模型取价；``next_open`` → 本根 ``open``。

        未知 model：warning 后回退 ``close``。
        """
        key = str(model or "close").strip().lower() or "close"
        if key == "next_open":
            key = "open"
        if key not in {"open", "high", "low", "close", "pre_close"}:
            cls._warn(
                key,
                use_raw=use_raw,
                reason=f"unsupported price model {model!r}; fallback close",
                default=default,
            )
            key = "close"
        return cls.float(bar, key, use_raw=use_raw, default=default)

    @classmethod
    def _source(
        cls, bar: Any, *, use_raw: bool
    ) -> tuple[Optional[Dict[str, Any]], Optional[str]]:
        if not isinstance(bar, dict):
            return None, f"bar is not dict: {type(bar).__name__}"
        if not use_raw:
            return bar, None
        raw = bar.get("raw")
        if not isinstance(raw, dict):
            return None, "bar['raw'] missing or not dict"
        return raw, None

    @classmethod
    def _warn(
        cls,
        key: str,
        *,
        use_raw: bool,
        reason: str,
        default: Any,
    ) -> None:
        layer = "raw" if use_raw else "qfq"
        logger.warning(
            "SafeBarValue: key=%s layer=%s reason=%s → default=%r",
            key,
            layer,
            reason,
            default,
        )


__all__ = ["SafeBarValue"]
