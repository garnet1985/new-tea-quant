"""工作台列表与表单选项：策略分页、版本下拉（V2-02/03）、静态枚举（V2-04）。"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from core.infra.project_context import ProjectContext

from core.modules.data_manager import DataManager
from core.modules.market_profile.constants import MARKETS_CONFIG_DIR
from core.modules.strategy.engines.shared.data_classes.discovered_strategy import DiscoveredStrategy
from core.modules.strategy.engines.shared.data_classes.strategy_settings.sampling_settings import (
    KNOWN_STRATEGIES,
)
from core.modules.strategy.engines.shared.data_classes.strategy_settings.simulation_settings import (
    KNOWN_SIMULATION_TEMPLATES,
    simulation_template_defaults_payload,
)
from core.modules.strategy.engines.shared.helpers.skip_investment_when import (
    KNOWN_SKIP_INVESTMENT_TAGS,
)
from core.modules.strategy.engines.simulator.capital_allocation.data_classes.settings import (
    _VALID_MODES,
)
from core.modules.strategy.engines.shared.data_classes.strategy_settings.meta_settings import (
    _coerce_meta_text,
)
from core.modules.strategy.services.discovery import StrategyDiscoveryHelper

# 与 ``API.md`` V2-03：固定至多 10 条，不分页。
DROPDOWN_LIMIT = 10


def _summary(ds: DiscoveredStrategy) -> Dict[str, Any]:
    meta = ds.settings.meta
    desc = _coerce_meta_text(meta.description)
    keywords = list(meta.keywords or [])
    details = None
    if meta.details is not None and meta.details.entry:
        details = {"entry": list(meta.details.entry)}
    return {
        "name": ds.name,
        "display_name": str(meta.display_name or "").strip(),
        "is_enabled": bool(ds.is_enabled),
        "worker_class_name": ds.worker_class_name,
        "folder": str(ds.folder),
        "description": desc,
        "keywords": keywords,
        "details": details,
    }


def fetch_discovered_strategies_page(page: int, limit: int) -> Tuple[List[Dict[str, Any]], int]:
    """
    分页返回 userspace 发现到的策略摘要；``page`` 为 1-based，按 ``name`` 排序。
    """
    discovered = StrategyDiscoveryHelper.discover_strategies()
    ordered = sorted(discovered.values(), key=lambda d: d.name)
    total = len(ordered)
    if total == 0:
        return [], 0
    page = max(1, int(page))
    limit = max(1, int(limit))
    start = (page - 1) * limit
    chunk = ordered[start : start + limit]
    return [_summary(ds) for ds in chunk], total


def _iso(dt: Any) -> Optional[str]:
    if dt is None:
        return None
    if isinstance(dt, datetime):
        return dt.isoformat(sep=" ", timespec="seconds")
    return str(dt)


def fetch_strategy_versions_dropdown(strategy_name: str) -> List[Dict[str, Any]]:
    """
    某策略工作台快照版本（最多 ``DROPDOWN_LIMIT`` 条，从新到旧）；无表或无行时 ``[]``。
    """
    name = str(strategy_name or "").strip()
    if not name:
        return []

    model = DataManager().get_table("sys_strategy_workbench_snapshot")
    if model is None:
        return []

    rows = model.list_by_strategy(name, limit=DROPDOWN_LIMIT)
    items: List[Dict[str, Any]] = []
    for row in rows:
        sid = int(row.get("version") or 0)
        if sid <= 0:
            continue
        items.append(
            {
                "version_id": f"v{sid}",
                "version": sid,
                "updated_at": _iso(row.get("updated_at")),
                "created_at": _iso(row.get("created_at")),
            }
        )
    return items


# --- V2-04 静态选项（与校验层合法取值一致） ---

_CAPITAL_ALLOCATION_META: Dict[str, tuple] = {
    "equal_capital": (
        "等额资金",
        "每个新开仓机会分配相近的现金额度（总资金 ÷ 最大持股数），股数随价格浮动。",
    ),
    "equal_shares": (
        "等额股数",
        "每个机会买入相同手数（由「每次买入手数」与市场最小交易单位决定）。",
    ),
    "kelly": (
        "凯莉公式",
        "按凯莉公式估算建议仓位，再乘以「凯莉折扣系数」做保守缩放；需策略提供胜率/赔率等输入。",
    ),
    "custom": (
        "自定义",
        "使用策略或引擎扩展的自定义分配逻辑（高级用法）。",
    ),
}

_SAMPLING_STRATEGY_META: Dict[str, tuple] = {
    "continuous": ("连续采样", "从某一位置起连续顺序抽样。比如，从第1个开始连续抽取5个股票"),
    "uniform": ("均匀采样", "对所有集合进行等间距抽样。比如一共100个股票，抽取10个，那么就是每隔10个抽取一个。"),
    "stratified": ("分层采样", "按分层规则抽样（如行业、市值桶），需配置随机种子以便复现。比如，深市沪市各抽取5个。"),
    "random": ("随机采样", "在集合中随机抽样；可设种子固定随机结果。"),
    "pool": ("股票池", "在指定的列表内回测。"),
    "blacklist": ("黑名单", "抽取所有的集合，再排除黑名单列表后的样本。"),
}

_SKIP_INVESTMENT_WHEN_META: Dict[str, tuple] = {
    "st": (
        "ST",
        "触发日处于 ST（含 SST）时，价格/资金回测跳过该笔投资；枚举机会仍保留。",
    ),
    "star_st": (
        "*ST",
        "触发日处于 *ST（含 S*ST）时，价格/资金回测跳过该笔投资；枚举机会仍保留。",
    ),
}

_SIMULATION_TEMPLATE_META: Dict[str, tuple] = {
    "standard": (
        "标准",
        "日常回测默认；常见成交节奏，涨跌停不成交。不知道选什么就用这个。",
    ),
    "strict": (
        "严格",
        "更贴近 A 股现实；在标准基础上，触发日 ST/*ST 不参与 price/capital 模拟。",
    ),
    "ideal": (
        "理想",
        "少市场摩擦的对照组；与「标准」对比，看策略信号本身好不好。",
    ),
    "extreme": (
        "极值压力",
        "压力测试；盯盘与成交按极值取价，结果通常更差。",
    ),
    "custom": (
        "自定义",
        "自行配置价模型、涨跌停、ST 跳过等；熟悉执行假设时使用。",
    ),
}


def items_capital_allocation_strategies() -> List[Dict[str, Any]]:
    """``capital_simulator.allocation.mode`` 可选值。"""
    ordered = ("equal_capital", "equal_shares", "kelly", "custom")
    modes = [m for m in ordered if m in _VALID_MODES]
    rest = sorted(m for m in _VALID_MODES if m not in modes)
    out: List[Dict[str, Any]] = []
    for m in modes + rest:
        meta = _CAPITAL_ALLOCATION_META.get(m)
        if meta:
            label, tooltip = meta
            out.append({"value": m, "label": label, "tooltip": tooltip})
        else:
            out.append({"value": m, "label": m})
    return out


def items_sampling_strategies() -> List[Dict[str, Any]]:
    """根级 ``sampling.strategy`` 可选值。"""
    ordered = ("continuous", "uniform", "stratified", "random", "pool", "blacklist")
    keys = [k for k in ordered if k in KNOWN_STRATEGIES]
    rest = sorted(k for k in KNOWN_STRATEGIES if k not in keys)
    out: List[Dict[str, Any]] = []
    for k in keys + rest:
        meta = _SAMPLING_STRATEGY_META.get(k)
        if meta:
            label, tooltip = meta
            out.append({"value": k, "label": label, "tooltip": tooltip})
        else:
            out.append({"value": k, "label": k})
    return out


def items_skip_investment_when() -> List[Dict[str, Any]]:
    """根级 ``simulation.skip_investment_when`` 可选标签（与 ``KNOWN_SKIP_INVESTMENT_TAGS`` 一致）。"""
    ordered = ("st", "star_st")
    keys = [k for k in ordered if k in KNOWN_SKIP_INVESTMENT_TAGS]
    rest = sorted(k for k in KNOWN_SKIP_INVESTMENT_TAGS if k not in keys)
    out: List[Dict[str, Any]] = []
    for k in keys + rest:
        meta = _SKIP_INVESTMENT_WHEN_META.get(k)
        if meta:
            label, tooltip = meta
            out.append({"value": k, "label": label, "tooltip": tooltip})
        else:
            out.append({"value": k, "label": k})
    return out


def items_simulation_templates() -> List[Dict[str, Any]]:
    """根级 ``simulation.template`` 可选值（含 ``defaults`` 供工作台只读展示）。"""
    ordered = ("standard", "strict", "ideal", "extreme", "custom")
    keys = [k for k in ordered if k in KNOWN_SIMULATION_TEMPLATES]
    rest = sorted(k for k in KNOWN_SIMULATION_TEMPLATES if k not in keys)
    out: List[Dict[str, Any]] = []
    for k in keys + rest:
        meta = _SIMULATION_TEMPLATE_META.get(k)
        if meta:
            label, tooltip = meta
            row: Dict[str, Any] = {"value": k, "label": label, "tooltip": tooltip}
        else:
            row = {"value": k, "label": k}
        if k != "custom":
            row["defaults"] = simulation_template_defaults_payload(k)
        else:
            row["defaults"] = simulation_template_defaults_payload("standard")
        out.append(row)
    return out


def items_market_profiles() -> List[Dict[str, Any]]:
    """根级 ``market_profile`` 可选值（扫描 markets 配置目录）。"""
    known = ProjectContext.discovery.discover_configs(MARKETS_CONFIG_DIR)
    out: List[Dict[str, Any]] = []
    for pid in known:
        label = pid
        try:
            raw = ProjectContext.discovery.load_overridable_config(MARKETS_CONFIG_DIR, pid)
            if isinstance(raw, dict):
                desc = str(raw.get("description") or "").strip()
                if desc:
                    label = desc
        except Exception:
            pass
        out.append({"value": pid, "label": label})
    return out
