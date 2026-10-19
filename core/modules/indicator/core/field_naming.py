"""指标落盘字段命名与 settings 校验。

规则：
- 单列：有 ``alias`` 用 alias；否则 ``{name}{length}``，无 length 则拼参数。
- 多列：有 ``alias`` 为 ``{alias}_{ta列名小写}``；否则直接用 ta 列名小写。
- ``alias`` 不传入 TA 计算；同一配置内最终占用的名字（含默认名与 alias）不可重复。
"""

from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

ALIAS_KEY = "alias"

_ALIAS_RE = re.compile(r"^[a-z][a-z0-9_]*$")

# 与行情 / 元数据冲突的保留名（勿当指标字段）
RESERVED_FIELD_NAMES = frozenset(
    {
        "date",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "amount",
        "turnover",
        "turnover_rate",
        "turnover_value",
        "pre_close",
        "preclose",
        "change",
        "pct_chg",
        "pct_change",
        "factor",
        "adj_factor",
        "hfq_factor",
        "qfq_factor",
        "code",
        "ts_code",
        "symbol",
        "name",
        "entity_id",
        "stock_id",
    }
)


def read_alias(params: Optional[Dict[str, Any]]) -> Optional[str]:
    """读取并规范化 alias；缺省或空串返回 None。"""
    if not isinstance(params, dict):
        return None
    raw = params.get(ALIAS_KEY)
    if raw is None:
        return None
    text = str(raw).strip().lower()
    return text or None


def compute_params(params: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """去掉 alias，供 TA 计算使用。"""
    if not isinstance(params, dict):
        return {}
    return {k: v for k, v in params.items() if k != ALIAS_KEY}


def auto_series_name(name: str, params: Optional[Dict[str, Any]]) -> str:
    """无 alias 时的单列默认名。"""
    key = str(name or "").lower().strip()
    cfg = compute_params(params)
    length = cfg.get("length")
    if length is not None and isinstance(length, (int, float, str)):
        try:
            return f"{key}{int(length)}"
        except (TypeError, ValueError):
            pass
    parts = [key]
    for param_key in sorted(cfg.keys()):
        value = cfg[param_key]
        if isinstance(value, (int, float, str)):
            parts.append(f"{param_key}{value}")
    return "_".join(parts)


def series_field_name(name: str, params: Optional[Dict[str, Any]]) -> str:
    """单列结果落盘字段名。"""
    alias = read_alias(params)
    if alias is not None:
        return alias
    return auto_series_name(name, params)


def dict_field_name(
    name: str,
    params: Optional[Dict[str, Any]],
    sub_key: str,
) -> str:
    """多列结果中某一通道的落盘字段名。"""
    channel = str(sub_key or "").strip().lower()
    if not channel:
        raise ValueError(f"指标 {name!r} 多列结果缺少列名")
    alias = read_alias(params)
    if alias is not None:
        return f"{alias}_{channel}"
    return channel


def declared_field_names(indicators_cfg: Optional[Dict[str, Any]]) -> List[str]:
    """配置阶段可确定的字段名（单列默认名或 alias；多列无 alias 时不预列）。"""
    cfg = dict(indicators_cfg or {})
    names: List[str] = []
    for name, raw in cfg.items():
        specs = raw if isinstance(raw, list) else [raw]
        for spec in specs:
            if not isinstance(spec, dict):
                continue
            alias = read_alias(spec)
            if alias is not None:
                if alias not in names:
                    names.append(alias)
                continue
            # 仅 length 型单列可在配置期预知；多参数多列留给写入结果发现
            if "length" in compute_params(spec):
                field = auto_series_name(str(name), spec)
                if field and field not in names:
                    names.append(field)
    return names


def validate_indicators_config(indicators_cfg: Optional[Dict[str, Any]]) -> None:
    """校验 alias 格式与字段名占用（alias 与可预知默认名全局唯一）。"""
    claimed: Dict[str, str] = {}

    def claim(field: str, source: str) -> None:
        if field in RESERVED_FIELD_NAMES:
            raise ValueError(f"指标字段名 {field!r} 与行情字段冲突（{source}）")
        prior = claimed.get(field)
        if prior is not None:
            raise ValueError(f"指标字段名重复: {field!r}（{prior} 与 {source}）")
        claimed[field] = source

    for name, raw in dict(indicators_cfg or {}).items():
        specs: Sequence[Any] = raw if isinstance(raw, list) else [raw]
        for idx, spec in enumerate(specs):
            if not isinstance(spec, dict):
                raise ValueError(f"indicators.{name}[{idx}] 须为 dict")
            source = f"{name}[{idx}]"
            alias = read_alias(spec)
            if alias is not None:
                if not _ALIAS_RE.match(alias):
                    raise ValueError(
                        f"indicators.{source}.alias 非法: {alias!r}"
                        "（须小写字母开头，仅含 a-z / 0-9 / _）"
                    )
                claim(alias, f"{source}.alias")
                continue
            params = compute_params(spec)
            if "length" in params:
                claim(auto_series_name(str(name), spec), source)


def apply_batch_to_rows(
    rows: List[Dict[str, Any]],
    batch: Iterable[Tuple[str, Dict[str, Any], Any]],
) -> List[str]:
    """把 compute_batch 结果写入 rows，返回实际写入的字段名。"""
    written: List[str] = []
    seen = set()

    def write_series(field: str, values: List[Any]) -> None:
        if field in seen:
            raise ValueError(f"指标字段名重复: {field!r}")
        for rec, val in zip(rows, values):
            rec[field] = val
        seen.add(field)
        written.append(field)

    for name, cfg, result in batch:
        params = cfg if isinstance(cfg, dict) else {}
        if isinstance(result, list):
            write_series(series_field_name(name, params), result)
            continue
        if isinstance(result, dict):
            for sub_key, series in result.items():
                if not isinstance(series, list):
                    continue
                write_series(dict_field_name(name, params, str(sub_key)), series)
    return written


__all__ = [
    "ALIAS_KEY",
    "RESERVED_FIELD_NAMES",
    "apply_batch_to_rows",
    "auto_series_name",
    "compute_params",
    "declared_field_names",
    "dict_field_name",
    "read_alias",
    "series_field_name",
    "validate_indicators_config",
]
