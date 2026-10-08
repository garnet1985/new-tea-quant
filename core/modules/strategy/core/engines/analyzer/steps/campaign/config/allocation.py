"""组合层资金分配轴。只读 attribution.allocation，不并入共用 inputs。"""
from __future__ import annotations

import copy
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from core.modules.strategy.core.engines.shared.services.strategy_settings.settings_base import (
    SettingsBase,
)
from core.modules.strategy.core.engines.shared.services.strategy_settings.validation_report import (
    ValidationReport,
)

from .inputs import expand_declared_values, value_at

_MODES = ("equal_shares", "equal_capital", "kelly")

# 短名 → settings 路径。只允许这些轴。
_AXES: Dict[str, str] = {
    "mode": "portfolio.allocation.mode",
    "max_portfolio_size": "portfolio.allocation.max_portfolio_size",
    "initial_capital": "portfolio.initial_capital",
    "max_weight_per_stock": "portfolio.allocation.max_weight_per_stock",
    "kelly_fraction": "portfolio.allocation.kelly_fraction",
    "lots_per_trade": "portfolio.allocation.lots_per_trade",
    "opportunity_selection": "portfolio.allocation.opportunity_selection",
}

# 主轴：没写 allocation 时一定尝试生成。伴随轴只在当前 settings 里有值时加入。
_PRIMARY = ("mode", "max_portfolio_size", "initial_capital")
_COMPANION = ("max_weight_per_stock", "kelly_fraction", "lots_per_trade")


def validate_allocation(raw: Mapping[str, Any], report: ValidationReport) -> None:
    """``allocation`` 缺省合法。写了就必须是已知轴 + 非空 values。"""
    if "allocation" not in raw:
        return
    block = raw.get("allocation")
    if block is None:
        return
    if not isinstance(block, Mapping):
        SettingsBase.add_critical(
            report,
            "allocation",
            "attribution.allocation 须为 dict",
            suggested_fix=(
                '{"allocation": {"mode": {"values": '
                '["equal_shares", "equal_capital", "kelly"]}}}'
            ),
        )
        return
    for key, spec in block.items():
        name = str(key or "").strip()
        path = _AXES.get(name)
        if path is None and name in _AXES.values():
            path = name
            name = _name_of(path)
        if path is None:
            SettingsBase.add_critical(
                report,
                f"allocation.{key}",
                f"未知资金分配轴 {key!r}",
                suggested_fix=(
                    "只能写 mode / max_portfolio_size / initial_capital / "
                    "max_weight_per_stock / kelly_fraction / lots_per_trade / "
                    "opportunity_selection"
                ),
            )
            continue
        try:
            values = _read_values(spec, label=f"allocation.{name}.values")
        except ValueError as exc:
            SettingsBase.add_critical(report, f"allocation.{name}", str(exc))
            continue
        if values is None:
            SettingsBase.add_critical(
                report,
                f"allocation.{name}",
                "须为 {\"values\": [...]} 或 "
                "{\"values\": {\"range\": [start, end], \"step\": n}}，且展开后非空",
            )
            continue
        _check_values(report, name, values)


def resolve_allocation_axes(
    raw: Mapping[str, Any],
    snapshot: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Tuple[Any, ...]]:
    """返回要扫的分配轴。未写 allocation 时用当前设置生成默认档。"""
    if not isinstance(raw, Mapping) or "allocation" not in raw:
        return _default_axes(snapshot or {})
    block = raw.get("allocation")
    if not isinstance(block, Mapping) or not block:
        return {}
    out: Dict[str, Tuple[Any, ...]] = {}
    for key, spec in block.items():
        name = str(key or "").strip()
        path = _AXES.get(name)
        if path is None and name in _AXES.values():
            path = name
        if path is None:
            continue
        values = _read_values(spec, label=f"allocation.{name}.values")
        if not values:
            continue
        out[path] = tuple(values)
    return out


def _default_axes(snapshot: Mapping[str, Any]) -> Dict[str, Tuple[Any, ...]]:
    out: Dict[str, Tuple[Any, ...]] = {}
    for name in _PRIMARY + _COMPANION:
        values = _default_values(name, snapshot)
        if not values:
            continue
        if name in _COMPANION and value_at(snapshot, _AXES[name]) is None:
            continue
        out[_AXES[name]] = tuple(values)
    return out


def _default_values(name: str, snapshot: Mapping[str, Any]) -> List[Any]:
    path = _AXES[name]
    cur = value_at(snapshot, path)
    if name == "mode":
        modes: List[Any] = list(_MODES)
        if not _has_kelly_default(snapshot):
            modes = [item for item in modes if item != "kelly"]
        if isinstance(cur, str) and cur.strip() and cur not in modes:
            modes.insert(0, cur.strip())
        return modes
    if name == "max_portfolio_size":
        return _size_ladder(cur)
    if name == "initial_capital":
        return _capital_ladder(cur)
    if name == "max_weight_per_stock":
        return _weight_ladder(cur)
    if name == "kelly_fraction":
        return _fraction_ladder(cur)
    if name == "lots_per_trade":
        return _lots_ladder(cur)
    return []


def _has_kelly_default(snapshot: Mapping[str, Any]) -> bool:
    cash = value_at(snapshot, "portfolio.allocation.default_cash")
    shares = value_at(snapshot, "portfolio.allocation.default_shares")
    return _positive_number(cash) or _positive_number(shares)


def _positive_number(value: Any) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    return float(value) > 0


def _size_ladder(cur: Any) -> List[Any]:
    base = (
        int(cur)
        if isinstance(cur, (int, float)) and not isinstance(cur, bool)
        else 10
    )
    grid = [4, 6, 8, 10, 15, 20]
    if base not in grid:
        grid.append(base)
    grid.sort()
    return _unique(grid)


def _capital_ladder(cur: Any) -> List[Any]:
    if not isinstance(cur, (int, float)) or isinstance(cur, bool) or cur <= 0:
        return []
    base = float(cur)
    values = [base * 0.5, base, base * 2.0]
    if isinstance(cur, int) or float(cur).is_integer():
        return _unique([int(round(item)) for item in values if item > 0])
    return _unique([item for item in values if item > 0])


def _weight_ladder(cur: Any) -> List[Any]:
    if not isinstance(cur, (int, float)) or isinstance(cur, bool):
        return []
    number = float(cur)
    if number > 1.0:
        grid = [10.0, 20.0, 25.0, 33.0, 50.0]
        if all(abs(number - item) > 1e-9 for item in grid):
            grid.append(number)
        grid.sort()
        return _unique(grid)
    grid = [0.10, 0.20, 0.25, 0.33, 0.50]
    if all(abs(number - item) > 1e-9 for item in grid):
        grid.append(number)
    grid.sort()
    return _unique(grid)


def _fraction_ladder(cur: Any) -> List[Any]:
    if not isinstance(cur, (int, float)) or isinstance(cur, bool):
        return []
    grid = [0.25, 0.5, 1.0]
    number = float(cur)
    if all(abs(number - item) > 1e-9 for item in grid):
        grid.append(number)
    grid.sort()
    return _unique(grid)


def _lots_ladder(cur: Any) -> List[Any]:
    if not isinstance(cur, (int, float)) or isinstance(cur, bool) or int(cur) < 1:
        return []
    base = int(cur)
    return _unique([1, base, max(base * 2, 2)])


def _read_values(spec: Any, *, label: str) -> Optional[List[Any]]:
    if isinstance(spec, Mapping):
        values = spec.get("values")
    else:
        values = None
    if isinstance(values, Mapping):
        expanded = expand_declared_values(values, label=label)
        return expanded or None
    if not isinstance(values, Sequence) or isinstance(values, (str, bytes)):
        return None
    if not values:
        return None
    return list(values)


def _check_values(report: ValidationReport, name: str, values: Sequence[Any]) -> None:
    field = f"allocation.{name}"
    if name == "opportunity_selection":
        for item in values:
            message = _selection_value_error(item)
            if message:
                SettingsBase.add_critical(report, field, message)
        return
    if name == "mode":
        for item in values:
            if item not in _MODES:
                SettingsBase.add_critical(
                    report,
                    field,
                    f"mode 只能是 {', '.join(_MODES)}，收到 {item!r}",
                )
        return
    if name in ("max_portfolio_size", "lots_per_trade"):
        for item in values:
            if isinstance(item, bool) or not isinstance(item, int) or item < 1:
                SettingsBase.add_critical(
                    report,
                    field,
                    f"{name} 须为正整数，收到 {item!r}",
                )
        return
    if name == "initial_capital":
        for item in values:
            if (
                isinstance(item, bool)
                or not isinstance(item, (int, float))
                or item <= 0
            ):
                SettingsBase.add_critical(
                    report,
                    field,
                    f"initial_capital 须为正数，收到 {item!r}",
                )
        return
    if name == "kelly_fraction":
        for item in values:
            if (
                isinstance(item, bool)
                or not isinstance(item, (int, float))
                or item <= 0
                or item > 1
            ):
                SettingsBase.add_critical(
                    report,
                    field,
                    f"kelly_fraction 须在 (0, 1]，收到 {item!r}",
                )
        return
    if name == "max_weight_per_stock":
        for item in values:
            if isinstance(item, bool) or not isinstance(item, (int, float)):
                SettingsBase.add_critical(
                    report,
                    field,
                    f"max_weight_per_stock 须为正数，收到 {item!r}",
                )
                continue
            number = float(item)
            if number <= 0 or (number > 1.0 and number > 100.0):
                SettingsBase.add_critical(
                    report,
                    field,
                    f"max_weight_per_stock 须为 (0, 1] 或百分数 (0, 100]，收到 {item!r}",
                )


def _selection_value_error(item: Any) -> str:
    """每个取值是一份选仓列表。``[]`` 表示按到达顺序。"""
    if isinstance(item, (str, bytes)) or not isinstance(item, Sequence):
        return f"opportunity_selection 的取值须为列表，收到 {item!r}"
    from core.modules.strategy.core.engines.shared.services.strategy_settings.portfolio_settings import (
        PortfolioSettings,
    )

    probe = PortfolioSettings(
        raw_settings={
            "portfolio": {
                "initial_capital": 1_000_000,
                "allocation": {"opportunity_selection": list(item)},
            }
        }
    )
    report = probe.validate()
    for error in report.errors:
        path = str(error.get("field_path") or "")
        if "opportunity_selection" in path:
            return str(error.get("message") or "opportunity_selection 不合法")
    return ""


def _name_of(path: str) -> str:
    for name, mapped in _AXES.items():
        if mapped == path:
            return name
    return path


def _unique(values: Sequence[Any]) -> List[Any]:
    out: List[Any] = []
    seen = set()
    for item in values:
        key = repr(item)
        if key in seen:
            continue
        seen.add(key)
        out.append(copy.deepcopy(item))
    return out
