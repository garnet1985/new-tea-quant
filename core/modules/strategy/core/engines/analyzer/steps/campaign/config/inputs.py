"""按层 ``inputs``：校验、短名解析、oaat / cross 展成 overlay 树。

替换原 ``overlays`` 列表与 ``matrix`` 笛卡尔配置。
"""
from __future__ import annotations

import copy
import itertools
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from core.modules.strategy.core.engines.shared.services.strategy_settings.execute_fp_whitelist import (
    EXECUTE_SETTINGS_FIELDS,
)
from core.modules.strategy.core.engines.shared.services.strategy_settings.settings_base import (
    SettingsBase,
)
from core.modules.strategy.core.engines.shared.services.strategy_settings.validation_report import (
    ValidationReport,
)

from .overlay import SettingsOverlay

MAX_CELLS = 128

_SHORT_NAMES: Dict[str, Dict[str, str]] = {
    "enumerate": {
        "stop_loss": "goal.stop_loss",
        "take_profit": "goal.take_profit",
        "max_pe_percentile": "core.max_pe_percentile",
        "rsi_oversold_threshold": "core.rsi_oversold_threshold",
        "min_netprofit_yoy": "core.min_netprofit_yoy",
        "min_pe_history_days": "core.min_pe_history_days",
        "pe_metric": "core.pe_metric",
    },
    "price_factor": {
        "opportunity_merge_gap": "simulation.price.opportunity_merge_gap",
    },
    "portfolio": {
        "max_portfolio_size": "portfolio.allocation.max_portfolio_size",
        "max_weight_per_stock": "portfolio.allocation.max_weight_per_stock",
        "mode": "portfolio.allocation.mode",
    },
}

_GOAL_STRUCT_PATHS = frozenset({"goal.stop_loss", "goal.take_profit"})
_DEFAULT_UNIVERSE = 5000
_SOFT_BARS_COST = 50_000_000
_HARD_BARS_COST = 200_000_000
_SOFT_CELLS = 20


def resolve_path(layer: str, key: str) -> str:
    text = str(key or "").strip()
    if not text:
        raise ValueError("inputs 轴名不能为空")
    if "." in text:
        return text
    mapped = _SHORT_NAMES.get(str(layer or "").strip(), {}).get(text)
    if mapped:
        return mapped
    if str(layer or "").strip() == "enumerate":
        return f"core.{text}"
    raise ValueError(
        f"未知短名 {text!r}（层 {layer}）；请写点号路径或登记短名"
    )


def root_section(path: str) -> str:
    return str(path or "").split(".", 1)[0]


def assign_path(tree: Dict[str, Any], path: str, value: Any) -> None:
    parts = [part for part in str(path).split(".") if part]
    if not parts:
        return
    cur: Dict[str, Any] = tree
    for part in parts[:-1]:
        nxt = cur.get(part)
        if not isinstance(nxt, dict):
            nxt = {}
            cur[part] = nxt
        cur = nxt
    cur[parts[-1]] = value


def value_at(mapping: Mapping[str, Any], path: str) -> Any:
    cur: Any = mapping
    for part in str(path).split("."):
        if not part:
            continue
        if not isinstance(cur, Mapping) or part not in cur:
            return None
        cur = cur[part]
    return cur


def normalize_goal_value(
    path: str, value: Any, snapshot: Mapping[str, Any]
) -> Any:
    if path not in _GOAL_STRUCT_PATHS:
        return value
    if value is None or isinstance(value, Mapping):
        return value
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(
            f"{path} 的 values 须为 None、整段结构，或单段时的 ratio 数字"
        )
    current = value_at(snapshot, path)
    if not isinstance(current, Mapping):
        raise ValueError(f"{path} 当前不是可扫结构，不能写裸数字")
    stages = current.get("stages")
    if not isinstance(stages, list) or len(stages) != 1:
        raise ValueError(f"{path} 为多段或无 stages，禁止裸数字 ratio")
    stage0 = stages[0]
    if not isinstance(stage0, Mapping) or "ratio" not in stage0:
        raise ValueError(f"{path} 单段缺少 ratio，禁止裸数字")
    wrapped = copy.deepcopy(current)
    wrapped_stages = list(wrapped.get("stages") or [])
    first = dict(wrapped_stages[0])
    first["ratio"] = value
    wrapped_stages[0] = first
    wrapped["stages"] = wrapped_stages
    return wrapped


def parse_axes(
    layer: str,
    inputs: Mapping[str, Any],
    *,
    snapshot: Optional[Mapping[str, Any]] = None,
    normalize: bool = True,
) -> List[Tuple[str, Tuple[Any, ...]]]:
    snap = snapshot if isinstance(snapshot, Mapping) else {}
    axes: List[Tuple[str, Tuple[Any, ...]]] = []
    for raw_key, spec in inputs.items():
        path = resolve_path(layer, str(raw_key))
        if root_section(path) not in EXECUTE_SETTINGS_FIELDS:
            raise ValueError(
                f"inputs.{raw_key} 路径 {path} 不在 execute_fp 白名单"
            )
        if not isinstance(spec, Mapping):
            raise ValueError(f"inputs.{raw_key} 须为 {{'values': [...]}}")
        extra = set(spec) - {"values"}
        if extra:
            raise ValueError(
                f"inputs.{raw_key} 只能含 values，不能写 {sorted(extra)}"
            )
        values = spec.get("values")
        if not isinstance(values, Sequence) or isinstance(values, (str, bytes)):
            raise ValueError(f"inputs.{raw_key}.values 须为非空 list")
        if not values:
            raise ValueError(f"inputs.{raw_key}.values 不能为空")
        if normalize:
            normalized = [
                normalize_goal_value(path, item, snap) for item in values
            ]
        else:
            normalized = list(values)
        axes.append((path, tuple(normalized)))
    return axes


def expand_axes(
    axes: Sequence[Tuple[str, Tuple[Any, ...]]],
    *,
    cross: bool,
) -> Tuple[Dict[str, Any], ...]:
    if not axes:
        return ()
    if cross:
        paths = [path for path, _ in axes]
        pools = [levels for _, levels in axes]
        rows: List[Dict[str, Any]] = []
        for combo in itertools.product(*pools):
            tree: Dict[str, Any] = {}
            for path, value in zip(paths, combo):
                assign_path(tree, path, value)
            rows.append(tree)
        return tuple(rows)
    rows: List[Dict[str, Any]] = []
    for path, levels in axes:
        for value in levels:
            tree: Dict[str, Any] = {}
            assign_path(tree, path, value)
            rows.append(tree)
    return tuple(rows)


def cell_count(
    axes: Sequence[Tuple[str, Tuple[Any, ...]]], *, cross: bool
) -> int:
    if not axes:
        return 1
    if cross:
        n = 1
        for _path, levels in axes:
            n *= max(len(levels), 1)
        return n
    return 1 + sum(len(levels) for _path, levels in axes)


def validate_layer_inputs(
    layer: str,
    block: Any,
    report: ValidationReport,
    *,
    field_prefix: str,
) -> None:
    if block is None:
        return
    if not isinstance(block, Mapping):
        SettingsBase.add_critical(
            report,
            field_prefix,
            f"{field_prefix} 须为 dict",
            suggested_fix=(
                '{"inputs": {"max_pe_percentile": {"values": [None, 30]}}}'
            ),
        )
        return
    extra = set(block) - {"inputs", "cross"}
    if extra:
        SettingsBase.add_critical(
            report,
            field_prefix,
            f"{field_prefix} 不能写 {sorted(extra)}",
            suggested_fix="只允许 inputs / cross",
        )
    raw_inputs = block.get("inputs")
    if raw_inputs is None:
        raw_inputs = {}
    if not isinstance(raw_inputs, Mapping):
        SettingsBase.add_critical(
            report,
            f"{field_prefix}.inputs",
            "inputs 须为 dict",
        )
        return
    cross = bool(block.get("cross", False))
    try:
        axes = parse_axes(layer, raw_inputs, snapshot={}, normalize=False)
    except ValueError as exc:
        SettingsBase.add_critical(
            report,
            f"{field_prefix}.inputs",
            str(exc),
        )
        return
    for path, levels in axes:
        probe: Dict[str, Any] = {}
        assign_path(probe, path, levels[0])
        overlay_report = SettingsOverlay.from_dict(probe).validate()
        for err in overlay_report.errors:
            err = dict(err)
            err["field_path"] = (
                f"{field_prefix}.inputs.{path}.{err.get('field_path') or ''}"
            ).rstrip(".")
            report.errors.append(err)
            report.is_valid = False
    n = cell_count(axes, cross=cross)
    if n > MAX_CELLS:
        SettingsBase.add_critical(
            report,
            f"{field_prefix}.inputs",
            f"展开约 {n} 格超过上限 {MAX_CELLS}",
            suggested_fix="减少 values，或关闭 cross",
        )
def goal_path_is_hook(snapshot: Mapping[str, Any], path: str) -> bool:
    """stages 含 custom（钩子判定）时不可按 ratio 扫。"""
    cur = value_at(snapshot, path)
    if not isinstance(cur, Mapping):
        return False
    stages = cur.get("stages")
    if not isinstance(stages, list) or not stages:
        return False
    for stage in stages:
        if isinstance(stage, Mapping) and str(stage.get("custom") or "").strip():
            return True
    return False


def default_axes_for_layer(
    layer: str, snapshot: Mapping[str, Any]
) -> Dict[str, Dict[str, List[Any]]]:
    focus = str(layer or "").strip()
    out: Dict[str, Dict[str, List[Any]]] = {}
    if focus == "enumerate":
        for name in ("stop_loss", "take_profit"):
            path = f"goal.{name}"
            cur = value_at(snapshot, path)
            if not isinstance(cur, Mapping) or not cur.get("stages"):
                continue
            if goal_path_is_hook(snapshot, path):
                continue
            out[path] = {"values": [copy.deepcopy(cur), None]}
        core = snapshot.get("core")
        if isinstance(core, Mapping):
            for key, cur in core.items():
                if isinstance(cur, (Mapping, list)):
                    continue
                path = f"core.{key}"
                key_l = str(key).lower()
                if any(
                    token in key_l
                    for token in ("percentile", "min_", "max_", "threshold")
                ):
                    out[path] = {"values": [cur, None]}
                else:
                    nearby = _nearby_scalar(cur)
                    values = [cur] if nearby is None else [cur, nearby]
                    out[path] = {"values": values}
    elif focus == "price_factor":
        path = "simulation.price.opportunity_merge_gap"
        cur = value_at(snapshot, path)
        if isinstance(cur, (int, float)) and not isinstance(cur, bool):
            wider = max(int(cur) + 2, 1)
            narrower = max(int(cur) - 1, 0)
            out[path] = {"values": [int(cur), wider, narrower]}
    elif focus == "portfolio":
        path_size = "portfolio.allocation.max_portfolio_size"
        cur = value_at(snapshot, path_size)
        if isinstance(cur, (int, float)) and not isinstance(cur, bool):
            bigger = type(cur)(cur * 2) if cur else cur
            out[path_size] = {"values": [cur, bigger]}
        path_w = "portfolio.allocation.max_weight_per_stock"
        cur_w = value_at(snapshot, path_w)
        if isinstance(cur_w, (int, float)) and not isinstance(cur_w, bool):
            out[path_w] = {"values": [cur_w]}
        mode = value_at(snapshot, "portfolio.allocation.mode")
        if isinstance(mode, str) and mode.strip():
            alt = "kelly" if mode != "kelly" else "equal_capital"
            out["portfolio.allocation.mode"] = {"values": [mode, alt]}
    return out


def merge_user_and_defaults(
    layer: str,
    user_inputs: Mapping[str, Any],
    snapshot: Mapping[str, Any],
) -> Dict[str, Dict[str, List[Any]]]:
    """有用户 ``inputs`` 时只扫声明轴；未声明时用层默认轴。"""
    if user_inputs:
        merged: Dict[str, Dict[str, List[Any]]] = {}
        for raw_key, spec in user_inputs.items():
            path = resolve_path(layer, str(raw_key))
            if not isinstance(spec, Mapping):
                continue
            values = spec.get("values")
            if not isinstance(values, Sequence) or isinstance(
                values, (str, bytes)
            ):
                continue
            if path in _GOAL_STRUCT_PATHS and goal_path_is_hook(snapshot, path):
                if any(
                    isinstance(item, (int, float)) and not isinstance(item, bool)
                    for item in values
                ):
                    raise ValueError(
                        f"{path} 当前为钩子（custom）止损/止盈，"
                        "不能写裸数字 ratio；请给整段结构或 None，或去掉该轴"
                    )
            normalized = [
                normalize_goal_value(path, item, snapshot) for item in values
            ]
            merged[path] = {"values": list(normalized)}
        return merged
    return default_axes_for_layer(layer, snapshot)


def _nearby_scalar(value: Any) -> Any:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value + 5 if value < 50 else max(value - 5, 0)
    if isinstance(value, float):
        return value * 1.25 if abs(value) > 1e-9 else 1.0
    return None


def estimate_bars_cost(
    pending_cells: int,
    snapshot: Mapping[str, Any],
) -> Tuple[int, int, int]:
    n = max(int(pending_cells), 0)
    start, end = _period_bounds(snapshot)
    trading_days = max(_approx_trading_days(start, end), 1)
    universe = _approx_universe(snapshot)
    per_run = trading_days * universe
    return n, per_run, n * per_run


def cost_gate_message(
    pending_cells: int,
    snapshot: Mapping[str, Any],
    *,
    cross: bool,
) -> Optional[str]:
    n, per_run, cost = estimate_bars_cost(pending_cells, snapshot)
    if n > MAX_CELLS:
        return f"待跑 {n} 格超过上限 {MAX_CELLS}"
    if cost > _HARD_BARS_COST:
        hint = " 或关闭 cross" if cross else ""
        return (
            f"粗算工作量过大（约 {n} 格 × {per_run} bars/格 = {cost}），"
            f"当前战役串行执行；请减少 values{hint}"
        )
    if n >= _SOFT_CELLS or cost >= _SOFT_BARS_COST:
        return (
            f"WARNING: 将串行跑约 {n} 次回测（粗算 bars×格={cost}）；"
            "确认 values / cross 是否必要"
        )
    return None


def _period_bounds(snapshot: Mapping[str, Any]) -> Tuple[str, str]:
    sim = snapshot.get("simulation")
    if not isinstance(sim, Mapping):
        return "", ""
    execution = sim.get("execution")
    if not isinstance(execution, Mapping):
        return "", ""
    return (
        str(execution.get("start_date") or "").strip(),
        str(execution.get("end_date") or "").strip(),
    )


def _approx_trading_days(start: str, end: str) -> int:
    s = start.replace("-", "")[:8]
    e = end.replace("-", "")[:8]
    if len(s) == 8 and len(e) == 8 and s.isdigit() and e.isdigit():
        try:
            from datetime import datetime

            d0 = datetime.strptime(s, "%Y%m%d")
            d1 = datetime.strptime(e, "%Y%m%d")
            calendar = max((d1 - d0).days, 0) + 1
            return max(int(calendar * 0.7), 1)
        except ValueError:
            pass
    return 252


def _approx_universe(snapshot: Mapping[str, Any]) -> int:
    scanner = snapshot.get("scanner")
    if isinstance(scanner, Mapping):
        watch = str(scanner.get("watch_list") or "").strip()
        if watch:
            parts = [
                p for p in watch.replace(";", ",").split(",") if p.strip()
            ]
            if parts:
                return max(len(parts), 1)
    return _DEFAULT_UNIVERSE


__all__ = [
    "MAX_CELLS",
    "assign_path",
    "cell_count",
    "cost_gate_message",
    "default_axes_for_layer",
    "estimate_bars_cost",
    "expand_axes",
    "goal_path_is_hook",
    "merge_user_and_defaults",
    "normalize_goal_value",
    "parse_axes",
    "resolve_path",
    "validate_layer_inputs",
    "value_at",
]
