"""Strategy settings option catalogs for UI (V2-04).

Consumers: ``core.ui.bff.APIs.strategy_workbench.strategy_stack``

Option values and template defaults come from the new strategy settings
model (``portfolio`` / ``sampling`` / ``assumption`` / ``risk_control``).
"""

from __future__ import annotations

from typing import Any, Dict, List

from core.modules.market_profile.core.markets import get_available_markets
from core.modules.strategy.core.engines.shared.services.strategy_settings.portfolio_settings import (
    _VALID_MODES,
)
from core.modules.strategy.core.engines.shared.services.strategy_settings.sampling_settings import (
    _KNOWN_STRATEGIES,
)
from core.modules.strategy.core.engines.shared.services.strategy_settings.simulation_settings.assumption_templates import (
    AssumptionTemplate,
)
from core.modules.strategy.core.engines.shared.services.strategy_settings.simulation_settings.risk_control import (
    StatusTagPolicy,
)


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
    "continuous": (
        "连续采样",
        "从某一位置起连续顺序抽样。比如，从第1个开始连续抽取5个股票",
    ),
    "uniform": (
        "均匀采样",
        "对所有集合进行等间距抽样。比如一共100个股票，抽取10个，那么就是每隔10个抽取一个。",
    ),
    "stratified": (
        "分层采样",
        "按分层规则抽样（如行业、市值桶），需配置随机种子以便复现。比如，深市沪市各抽取5个。",
    ),
    "random": ("随机采样", "在集合中随机抽样；可设种子固定随机结果。"),
    "weighted": ("加权采样", "按权重抽取样本；需提供权重配置。"),
    "pool": ("股票池", "在指定的列表内回测。"),
    "blacklist": ("黑名单", "抽取所有的集合，再排除黑名单列表后的样本。"),
}

_SKIP_ENTER_WHEN_META: Dict[str, tuple] = {
    "st": (
        "ST",
        "触发日处于 ST（含 SST）时，价格/资金回测跳过进场；枚举机会仍保留。",
    ),
    "star_st": (
        "*ST",
        "触发日处于 *ST（含 S*ST）时，价格/资金回测跳过进场；枚举机会仍保留。",
    ),
}

_SIMULATION_TEMPLATE_META: Dict[str, tuple] = {
    "standard": (
        "标准",
        "日常回测默认；touch 进场、常见贴板限制。不知道选什么就用这个。",
    ),
    "strict": (
        "严格",
        "更贴近现实；在标准基础上，超参与率时整笔跳过。",
    ),
    "ideal": (
        "理想",
        "少市场摩擦的对照组；允许涨跌停成交。",
    ),
    "extreme": (
        "极值压力",
        "压力测试；进场用次日开盘等更乐观口径，结果通常更差。",
    ),
    "none": (
        "无预设",
        "不使用命名预设，完全按下方显式 tradability 配置。",
    ),
    "custom": (
        "自定义",
        "自行配置盯价 / 进出价 / 滑点 / 贴板等；熟悉成交假设时使用。",
    ),
}

_MARKET_PROFILE_LABELS: Dict[str, str] = {
    "china_a_stock": "中国 A 股",
    "hong_kong": "港股",
    "us_stock": "美股",
    "commodity_future": "商品期货",
    "forex": "外汇",
    "crypto": "加密货币",
}


class StrategySettingsOptions:
    """V2-04 option lists aligned with the new strategy settings model."""

    @classmethod
    def items_capital_allocation_strategies(cls) -> List[Dict[str, Any]]:
        """``portfolio.allocation.mode`` 可选值。"""
        ordered = ("equal_capital", "equal_shares", "kelly", "custom")
        modes = [m for m in ordered if m in _VALID_MODES]
        rest = sorted(m for m in _VALID_MODES if m not in modes)
        return cls._labeled_items(modes + rest, _CAPITAL_ALLOCATION_META)

    @classmethod
    def items_sampling_strategies(cls) -> List[Dict[str, Any]]:
        """根级 ``sampling.strategy`` 可选值。"""
        ordered = (
            "continuous",
            "uniform",
            "stratified",
            "random",
            "weighted",
            "pool",
            "blacklist",
        )
        keys = [k for k in ordered if k in _KNOWN_STRATEGIES]
        rest = sorted(k for k in _KNOWN_STRATEGIES if k not in keys)
        return cls._labeled_items(keys + rest, _SAMPLING_STRATEGY_META)

    @classmethod
    def items_skip_enter_when(cls) -> List[Dict[str, Any]]:
        """``simulation.risk_control.skip_enter_when`` 可选标签。

        HTTP path remains ``/settings/skip-investment-when`` for URL compatibility.
        """
        known = StatusTagPolicy.KNOWN_TAGS
        ordered = ("st", "star_st")
        keys = [k for k in ordered if k in known]
        rest = sorted(k for k in known if k not in keys)
        return cls._labeled_items(keys + rest, _SKIP_ENTER_WHEN_META)

    # Compat alias used by existing BFF stack attribute name.
    items_skip_investment_when = items_skip_enter_when

    @classmethod
    def items_simulation_templates(cls) -> List[Dict[str, Any]]:
        """``simulation.assumption.template`` 可选值；``defaults`` 为嵌套 tradability。"""
        ordered = ("standard", "strict", "ideal", "extreme", "none", "custom")
        keys = [k for k in ordered if k in AssumptionTemplate.KNOWN]
        rest = sorted(k for k in AssumptionTemplate.KNOWN if k not in keys)
        out: List[Dict[str, Any]] = []
        for key in keys + rest:
            meta = _SIMULATION_TEMPLATE_META.get(key)
            if meta:
                label, tooltip = meta
                row: Dict[str, Any] = {
                    "value": key,
                    "label": label,
                    "tooltip": tooltip,
                }
            else:
                row = {"value": key, "label": key}
            row["defaults"] = cls._template_defaults_payload(key)
            out.append(row)
        return out

    @classmethod
    def items_market_profiles(cls) -> List[Dict[str, Any]]:
        """根级 ``market_profile`` 可选值。"""
        out: List[Dict[str, Any]] = []
        for pid in get_available_markets():
            out.append(
                {
                    "value": pid,
                    "label": _MARKET_PROFILE_LABELS.get(pid, pid),
                }
            )
        return out

    @classmethod
    def _template_defaults_payload(cls, template: str) -> Dict[str, Any]:
        """Nested defaults for FED merge under ``simulation.assumption``.

        Named presets → ``{"tradability": {...}}``.
        ``none`` / ``custom`` → empty (explicit tradability from user).
        """
        try:
            key = AssumptionTemplate.canonicalize(template)
        except ValueError:
            return {}
        if key not in AssumptionTemplate.NAMED:
            return {}
        return {"tradability": AssumptionTemplate.tradability_dict(key)}

    @staticmethod
    def _labeled_items(
        keys: List[str],
        meta_map: Dict[str, tuple],
    ) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for key in keys:
            meta = meta_map.get(key)
            if meta:
                label, tooltip = meta
                out.append({"value": key, "label": label, "tooltip": tooltip})
            else:
                out.append({"value": key, "label": key})
        return out


__all__ = ["StrategySettingsOptions"]
