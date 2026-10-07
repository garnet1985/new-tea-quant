"""战役共用 ``inputs``：校验、短名解析、oaat / cross 展成 overlay 树。

各层块 / 顶层 ``inputs`` 合并为同一套副本身份（见 ATTRIBUTION_CAMPAIGN §0）。
"""
from __future__ import annotations

import copy
import itertools
from decimal import Decimal
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

_LAYER_KEYS = ("enumerate", "price_factor", "portfolio")

# 短名全局唯一；展格不按 CLI 层拆分。
_SHORT_NAMES: Dict[str, str] = {
    "stop_loss": "goal.stop_loss",
    "take_profit": "goal.take_profit",
    "max_pe_percentile": "core.max_pe_percentile",
    "rsi_oversold_threshold": "core.rsi_oversold_threshold",
    "min_netprofit_yoy": "core.min_netprofit_yoy",
    "min_pe_history_days": "core.min_pe_history_days",
    "pe_metric": "core.pe_metric",
    "opportunity_merge_gap": "simulation.price.opportunity_merge_gap",
    "max_portfolio_size": "portfolio.allocation.max_portfolio_size",
    "max_weight_per_stock": "portfolio.allocation.max_weight_per_stock",
    "mode": "portfolio.allocation.mode",
}

_GOAL_STRUCT_PATHS = frozenset({"goal.stop_loss", "goal.take_profit"})
_DEFAULT_UNIVERSE = 5000
_SOFT_BARS_COST = 50_000_000
_HARD_BARS_COST = 200_000_000
_SOFT_CELLS = 20


def resolve_path(key: str, layer: str = "") -> str:
    """短名 → settings 路径。``layer`` 仅兼容未知裸名时回落到 ``core.*``。"""
    text = str(key or "").strip()
    if not text:
        raise ValueError("inputs 轴名不能为空")
    if "." in text:
        return text
    mapped = _SHORT_NAMES.get(text)
    if mapped:
        return mapped
    # 未登记裸名：想法侧常见 core 标量
    focus = str(layer or "").strip()
    if focus in ("", "enumerate", "campaign"):
        return f"core.{text}"
    raise ValueError(f"未知短名 {text!r}；请写点号路径或登记短名")


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


def expand_declared_values(values: Any, *, label: str) -> List[Any]:
    """把 values 列表或 ``{range, step}`` 展开成取值列表。"""
    if isinstance(values, Mapping):
        return _expand_range(values, label=label)
    if isinstance(values, Sequence) and not isinstance(values, (str, bytes)):
        return list(values)
    raise ValueError(
        f"{label} 须为非空 list，或 {{'range': [start, end], 'step': n}}"
    )


def _canonical_axis_spec(spec: Any) -> Any:
    """能展开时把 values 收成列表，便于列表和 range 对照是否同一组取值。"""
    if not isinstance(spec, Mapping):
        return spec
    try:
        values = expand_declared_values(spec.get("values"), label="values")
    except ValueError:
        return spec
    stored = dict(spec)
    stored["values"] = values
    return stored


def _expand_range(spec: Mapping[str, Any], *, label: str) -> List[Any]:
    extra = set(spec) - {"range", "step"}
    if extra:
        raise ValueError(f"{label} 只能含 range 和 step，不能写 {sorted(extra)}")
    if "range" not in spec or "step" not in spec:
        raise ValueError(f"{label} 须同时写 range 和 step")
    span = spec.get("range")
    if (
        not isinstance(span, Sequence)
        or isinstance(span, (str, bytes))
        or len(span) != 2
    ):
        raise ValueError(f"{label}.range 须为 [start, end]")
    start_raw, end_raw = span[0], span[1]
    step_raw = spec.get("step")
    start = _as_decimal(start_raw, f"{label}.range[0]")
    end = _as_decimal(end_raw, f"{label}.range[1]")
    step = _as_decimal(step_raw, f"{label}.step")
    if step <= 0:
        raise ValueError(f"{label}.step 须为正数，收到 {step_raw!r}")
    if end < start:
        raise ValueError(f"{label}.range 须升序，收到 [{start_raw!r}, {end_raw!r}]")
    steps = (end - start) / step
    if steps != steps.to_integral_value():
        raise ValueError(
            f"{label} 的终点 {end_raw!r} 不在 step {step_raw!r} 的网格上"
        )
    count = int(steps) + 1
    if count > MAX_CELLS:
        raise ValueError(f"{label} 展开为 {count} 个取值，超过上限 {MAX_CELLS}")
    as_int = _is_int(start_raw) and _is_int(end_raw) and _is_int(step_raw)
    out: List[Any] = []
    for index in range(count):
        number = start + step * index
        if as_int or number == number.to_integral_value():
            out.append(int(number))
        else:
            out.append(float(number))
    return out


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _as_decimal(value: Any, label: str) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} 须为数字，收到 {value!r}")
    if isinstance(value, int):
        return Decimal(value)
    return Decimal(str(value))


def parse_axes(
    layer: str,
    inputs: Mapping[str, Any],
    *,
    snapshot: Optional[Mapping[str, Any]] = None,
    normalize: bool = True,
) -> List[Tuple[str, Tuple[Any, ...]]]:
    """``layer`` 仅用于解析未登记裸名；轴集合本身是战役共用的。"""
    snap = snapshot if isinstance(snapshot, Mapping) else {}
    axes: List[Tuple[str, Tuple[Any, ...]]] = []
    for raw_key, spec in inputs.items():
        path = resolve_path(str(raw_key), layer=layer)
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
        values = expand_declared_values(
            spec.get("values"), label=f"inputs.{raw_key}.values"
        )
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


def collect_campaign_user_inputs(
    raw: Mapping[str, Any],
) -> Tuple[Dict[str, Any], bool]:
    """合并顶层 ``inputs`` 与各层块 ``inputs`` → 路径键 specs + cross。

    同一路径多处声明且 values 不一致则报错；``cross`` 多处不一致则报错。
    """
    if not isinstance(raw, Mapping):
        return {}, False

    merged: Dict[str, Any] = {}
    cross_flags: List[bool] = []

    if "cross" in raw and raw.get("cross") is not None:
        cross_flags.append(bool(raw.get("cross")))

    top = raw.get("inputs")
    if isinstance(top, Mapping):
        _merge_input_block(merged, top, layer="campaign")

    for layer in _LAYER_KEYS:
        block = raw.get(layer)
        if not isinstance(block, Mapping):
            continue
        if "cross" in block and block.get("cross") is not None:
            cross_flags.append(bool(block.get("cross")))
        nested = block.get("inputs")
        if isinstance(nested, Mapping):
            _merge_input_block(merged, nested, layer=layer)

    if len(set(cross_flags)) > 1:
        raise ValueError(
            "attribution.cross 在多处声明且不一致；请只在一处写 cross"
        )
    cross = cross_flags[0] if cross_flags else False
    return merged, cross


def collect_joint_sweep(raw: Mapping[str, Any]) -> List[Tuple[str, ...]]:
    """解析 ``joint_sweep``：轴子集笛卡尔；与全轴 ``cross`` 不同。"""
    if not isinstance(raw, Mapping):
        return []
    raw_groups = raw.get("joint_sweep")
    if raw_groups is None:
        return []
    if not isinstance(raw_groups, Sequence) or isinstance(raw_groups, (str, bytes)):
        raise ValueError(
            "joint_sweep 须为列表，如 [[\"stop_loss\", \"take_profit\"]]"
        )
    groups: List[Tuple[str, ...]] = []
    for i, group in enumerate(raw_groups):
        if not isinstance(group, Sequence) or isinstance(group, (str, bytes)):
            raise ValueError(f"joint_sweep[{i}] 须为轴名列表")
        paths: List[str] = []
        seen: set = set()
        for j, name in enumerate(group):
            path = resolve_path(str(name), layer="campaign")
            if path in seen:
                continue
            seen.add(path)
            paths.append(path)
        if len(paths) < 2:
            raise ValueError(
                f"joint_sweep[{i}] 至少需要 2 个不同轴（当前 {len(paths)}）"
            )
        if len(paths) > 3:
            raise ValueError(
                f"joint_sweep[{i}] 最多 3 个轴（避免组合爆炸）"
            )
        groups.append(tuple(paths))
    return groups


def expand_joint_groups(
    axes: Sequence[Tuple[str, Tuple[Any, ...]]],
    groups: Sequence[Sequence[str]],
) -> Tuple[Dict[str, Any], ...]:
    """对每个联合组做笛卡尔积；其余轴不进这些格子。"""
    by_path = {path: levels for path, levels in axes}
    rows: List[Dict[str, Any]] = []
    for group in groups:
        selected: List[Tuple[str, Tuple[Any, ...]]] = []
        for path in group:
            levels = by_path.get(path)
            if levels is None:
                raise ValueError(
                    f"joint_sweep 轴 {path} 不在 inputs 中；请先声明 values"
                )
            selected.append((path, levels))
        rows.extend(expand_axes(selected, cross=True))
    return tuple(rows)


def joint_cell_count(
    axes: Sequence[Tuple[str, Tuple[Any, ...]]],
    groups: Sequence[Sequence[str]],
) -> int:
    by_path = {path: levels for path, levels in axes}
    total = 0
    for group in groups:
        n = 1
        for path in group:
            levels = by_path.get(path) or ()
            n *= max(len(levels), 1)
        total += n
    return total


def _merge_input_block(
    merged: Dict[str, Any],
    block: Mapping[str, Any],
    *,
    layer: str,
) -> None:
    for raw_key, spec in block.items():
        path = resolve_path(str(raw_key), layer=layer)
        stored = _canonical_axis_spec(spec)
        if path in merged and merged[path] != stored:
            raise ValueError(
                f"inputs 路径 {path} 在多处声明且 values 不一致"
            )
        merged[path] = stored


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
    """单层建议默认轴（合并进共用展格时用）。"""
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
            out[path] = {"values": _goal_ratio_ladder(name, cur)}
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
                    out[path] = {"values": _threshold_ladder(cur)}
                else:
                    out[path] = {"values": _scalar_ladder(cur)}
    elif focus == "price_factor":
        path = "simulation.price.opportunity_merge_gap"
        cur = value_at(snapshot, path)
        if isinstance(cur, (int, float)) and not isinstance(cur, bool):
            base = int(cur)
            out[path] = {
                "values": _unique_keep(
                    [0, max(base - 1, 0), base, max(base + 2, 1), max(base + 4, 3)]
                )
            }
    elif focus == "portfolio":
        path_size = "portfolio.allocation.max_portfolio_size"
        cur = value_at(snapshot, path_size)
        if isinstance(cur, (int, float)) and not isinstance(cur, bool):
            out[path_size] = {"values": _portfolio_size_ladder(cur)}
        path_w = "portfolio.allocation.max_weight_per_stock"
        cur_w = value_at(snapshot, path_w)
        if isinstance(cur_w, (int, float)) and not isinstance(cur_w, bool):
            out[path_w] = {"values": _weight_ladder(cur_w)}
        mode = value_at(snapshot, "portfolio.allocation.mode")
        if isinstance(mode, str) and mode.strip():
            alt = "kelly" if mode != "kelly" else "equal_capital"
            out["portfolio.allocation.mode"] = {"values": [mode, alt]}
    return out


def default_axes_shared(
    snapshot: Mapping[str, Any],
) -> Dict[str, Dict[str, List[Any]]]:
    """无用户 inputs 时：合并枚举 / 价格默认轴为共用展格。

    资金分配不进这套副本，走 ``attribution.allocation``。
    """
    out: Dict[str, Dict[str, List[Any]]] = {}
    for layer in _LAYER_KEYS:
        if layer == "portfolio":
            continue
        for path, spec in default_axes_for_layer(layer, snapshot).items():
            out.setdefault(path, spec)
    return out


def merge_user_and_defaults(
    layer: str,
    user_inputs: Mapping[str, Any],
    snapshot: Mapping[str, Any],
) -> Dict[str, Dict[str, List[Any]]]:
    """有用户 ``inputs`` 时只扫声明轴；未声明时用**共用**默认轴。

    ``layer`` 仅用于解析裸名；不再表示「只展这一层的轴」。
    """
    if user_inputs:
        merged: Dict[str, Dict[str, List[Any]]] = {}
        for raw_key, spec in user_inputs.items():
            path = resolve_path(str(raw_key), layer=layer)
            if not isinstance(spec, Mapping):
                continue
            values = expand_declared_values(
                spec.get("values"), label=f"inputs.{raw_key}.values"
            )
            if not values:
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
    return default_axes_shared(snapshot)


def _nearby_scalar(value: Any) -> Any:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value + 5 if value < 50 else max(value - 5, 0)
    if isinstance(value, float):
        return value * 1.25 if abs(value) > 1e-9 else 1.0
    return None


def _unique_keep(values: Sequence[Any]) -> List[Any]:
    out: List[Any] = []
    seen: set = set()
    for item in values:
        key = repr(item)
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def _goal_ratio_ladder(name: str, cur: Mapping[str, Any]) -> List[Any]:
    """止损/止盈多档：裸 ratio + 关闭；单段才可扫。"""
    stages = cur.get("stages")
    ratio = None
    if isinstance(stages, list) and len(stages) == 1 and isinstance(stages[0], Mapping):
        raw = stages[0].get("ratio")
        if isinstance(raw, (int, float)) and not isinstance(raw, bool):
            ratio = float(raw)
    if name == "stop_loss":
        grid = [-0.10, -0.15, -0.20, -0.25]
    else:
        grid = [0.10, 0.15, 0.20, 0.25]
    values: List[Any] = list(grid)
    if ratio is not None and all(abs(ratio - float(item)) > 1e-9 for item in grid):
        values.insert(0, ratio)
    values.append(None)
    return _unique_keep(values)


def _threshold_ladder(cur: Any) -> List[Any]:
    if not isinstance(cur, (int, float)) or isinstance(cur, bool):
        return [cur, None]
    if isinstance(cur, int):
        lo = max(int(cur) - 10, 0)
        mid = max(int(cur) - 5, 0)
        hi = int(cur) + 5
        return _unique_keep([None, lo, mid, int(cur), hi])
    return _unique_keep([None, float(cur) * 0.75, float(cur), float(cur) * 1.25])


def _scalar_ladder(cur: Any) -> List[Any]:
    if isinstance(cur, bool):
        return [cur]
    if isinstance(cur, int):
        step = 5 if abs(cur) < 50 else max(int(abs(cur) * 0.1), 1)
        return _unique_keep(
            [max(cur - step, 0), cur, cur + step, cur + 2 * step]
        )
    if isinstance(cur, float):
        return _unique_keep(
            [cur * 0.75, cur, cur * 1.25, cur * 1.5]
            if abs(cur) > 1e-9
            else [0.0, 1.0]
        )
    nearby = _nearby_scalar(cur)
    return [cur] if nearby is None else [cur, nearby]


def _portfolio_size_ladder(cur: Any) -> List[Any]:
    base = int(cur) if isinstance(cur, (int, float)) and not isinstance(cur, bool) else 10
    grid = [4, 6, 8, 10, 15, 20]
    values = list(grid)
    if base not in grid:
        values.append(base)
    values.sort()
    return _unique_keep(values)


def _weight_ladder(cur: Any) -> List[Any]:
    if not isinstance(cur, (int, float)) or isinstance(cur, bool):
        return [cur]
    number = float(cur)
    if number > 1.0:
        # 百分比写法
        grid = [10.0, 15.0, 20.0, 25.0, 33.0]
        values = list(grid)
        if all(abs(number - item) > 1e-9 for item in grid):
            values.append(number)
        values.sort()
        return _unique_keep([type(cur)(item) for item in values])
    grid = [0.10, 0.15, 0.20, 0.25, 0.33]
    values = list(grid)
    if all(abs(number - item) > 1e-9 for item in grid):
        values.append(number)
    values.sort()
    return _unique_keep([type(cur)(item) for item in values])


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
    "collect_campaign_user_inputs",
    "collect_joint_sweep",
    "cost_gate_message",
    "default_axes_for_layer",
    "default_axes_shared",
    "estimate_bars_cost",
    "expand_axes",
    "expand_declared_values",
    "expand_joint_groups",
    "goal_path_is_hook",
    "joint_cell_count",
    "merge_user_and_defaults",
    "normalize_goal_value",
    "parse_axes",
    "resolve_path",
    "validate_layer_inputs",
    "value_at",
]
