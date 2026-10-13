"""用户钩子里全程一样的 ctx：身份、样本、跨日状态、归因。

当日 K 线、横截面和机会列表不在这里，它们是钩子入参。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Sequence, Tuple

from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import (
    StrategySettings,
)


@dataclass(frozen=True)
class StrategyInfo:
    """策略身份。"""

    key: str
    path: str = ""


@dataclass
class StrategyContext:
    """开跑后相对稳定的上下文。"""

    info: StrategyInfo
    effective_settings: StrategySettings
    sample_list: Tuple[str, ...] = ()
    mode: str = ""
    state: Dict[str, Any] = field(default_factory=dict)
    _cached_settings_dict: Optional[Dict[str, Any]] = field(
        default=None,
        init=False,
        repr=False,
        compare=False,
    )
    _captures: Dict[str, Any] = field(
        default_factory=dict,
        init=False,
        repr=False,
        compare=False,
    )

    @property
    def base_data_key(self) -> str:
        return self.effective_settings.data.base_data_key

    def effective_settings_dict(self) -> Dict[str, Any]:
        """settings 的 dict 视图。同一 ctx 上缓存。"""
        cached = self._cached_settings_dict
        if cached is None:
            cached = self.effective_settings.to_dict()
            self._cached_settings_dict = cached
        return cached

    def capture(self, key: str, value: Any) -> None:
        """记下本笔命中的归因输入。"""
        self._captures[str(key)] = value

    def clear_captures(self) -> None:
        """引擎：每次机会判定前清空归因袋。"""
        self._captures.clear()

    def take_captures(self) -> Dict[str, Any]:
        """引擎：取出并清空归因袋。"""
        out = dict(self._captures)
        self._captures.clear()
        return out


def open_context(
    *,
    strategy_key: str,
    settings: StrategySettings,
    sample_list: Optional[Sequence[str]] = None,
    strategy_path: str = "",
    state: Optional[Dict[str, Any]] = None,
) -> StrategyContext:
    """引擎开一个回测 ctx。``state`` 传入同一 dict 时跨调用共享。"""
    ids = tuple(str(item).strip() for item in (sample_list or []) if str(item).strip())
    try:
        mode = str(getattr(settings, "execution_mode", "") or "").strip()
    except Exception:
        mode = ""
    return StrategyContext(
        info=StrategyInfo(
            key=str(strategy_key or "").strip(),
            path=str(strategy_path or "").strip(),
        ),
        effective_settings=settings,
        sample_list=ids,
        mode=mode,
        state=state if state is not None else {},
    )


__all__ = ["StrategyContext", "StrategyInfo", "open_context"]
