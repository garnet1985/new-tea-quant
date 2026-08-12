"""UI labels / tooltips for strategy settings option catalogs."""

from __future__ import annotations

from typing import Dict

PORTFOLIO_ALLOCATION_META: Dict[str, tuple] = {
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

SAMPLING_META: Dict[str, tuple] = {
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

RISK_CONTROL_META: Dict[str, tuple] = {
    "st": (
        "ST",
        "触发日处于 ST（含 SST）时，价格/资金回测跳过进场；枚举机会仍保留。",
    ),
    "star_st": (
        "*ST",
        "触发日处于 *ST（含 S*ST）时，价格/资金回测跳过进场；枚举机会仍保留。",
    ),
}

SIMULATION_TEMPLATE_META: Dict[str, tuple] = {
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
    "custom": (
        "自定义",
        "自行配置盯价 / 进出价 / 滑点 / 贴板等；熟悉成交假设时使用。",
    ),
}

MARKET_RULES_LABELS: Dict[str, str] = {
    "china_a_stock": "中国 A 股",
    "hong_kong": "港股(未实现)",
    "us_stock": "美股(未实现)",
    "commodity_future": "商品期货(未实现)",
    "forex": "外汇(未实现)",
    "crypto": "加密货币(未实现)",
}

__all__ = [
    "PORTFOLIO_ALLOCATION_META",
    "SAMPLING_META",
    "RISK_CONTROL_META",
    "SIMULATION_TEMPLATE_META",
    "MARKET_RULES_LABELS",
]
