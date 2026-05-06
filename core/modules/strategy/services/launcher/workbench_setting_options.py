"""工作台表单静态选项（与校验层合法取值一致）。"""

from __future__ import annotations

from typing import Any, Dict, List

from core.modules.strategy.engines.shared.data_classes.strategy_settings.sampling_settings import (
    KNOWN_STRATEGIES,
)
from core.modules.strategy.engines.simulator.capital_allocation.data_classes.settings import (
    _VALID_MODES,
)

_CAPITAL_LABELS: Dict[str, str] = {
    "equal_capital": "等额资金",
    "equal_shares": "等额股数",
    "kelly": "Kelly",
    "custom": "自定义",
}

_SAMPLING_LABELS: Dict[str, str] = {
    "uniform": "均匀采样",
    "stratified": "分层采样",
    "random": "随机采样",
    "continuous": "连续采样",
    "pool": "股票池",
    "blacklist": "黑名单",
}


def items_capital_allocation_strategies() -> List[Dict[str, Any]]:
    """``capital_simulator.allocation.mode`` 可选值（与 ``StrategyCapitalSimulatorSettings`` 校验一致）。"""
    ordered = ("equal_capital", "equal_shares", "kelly", "custom")
    modes = [m for m in ordered if m in _VALID_MODES]
    rest = sorted(m for m in _VALID_MODES if m not in modes)
    out: List[Dict[str, Any]] = []
    for m in modes + rest:
        label = _CAPITAL_LABELS.get(m, m)
        out.append({"value": m, "label": label})
    return out


def items_sampling_strategies() -> List[Dict[str, Any]]:
    """根级 ``sampling.strategy`` 可选值（与 ``StrategySamplingSettings`` / ``KNOWN_STRATEGIES`` 一致）。"""
    ordered = ("continuous", "uniform", "stratified", "random", "pool", "blacklist")
    keys = [k for k in ordered if k in KNOWN_STRATEGIES]
    rest = sorted(k for k in KNOWN_STRATEGIES if k not in keys)
    out: List[Dict[str, Any]] = []
    for k in keys + rest:
        out.append({"value": k, "label": _SAMPLING_LABELS.get(k, k)})
    return out
