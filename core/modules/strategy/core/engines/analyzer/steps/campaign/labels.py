"""战役中文标签：旋钮 / 层 / 指标。"""
from __future__ import annotations

from typing import Any, Optional

from .contrasts import KnobContrasts

_LAYER_REPORT_TITLE = {
    "enumerate": "枚举归因报告",
    "price_factor": "价格归因报告",
    "portfolio": "组合归因报告",
}

_LAYER_LABELS = {
    "enumerate": "机会",
    "price_factor": "价格",
    "portfolio": "账户",
}

_OUTCOME_LABELS = {
    "total_opportunities": "机会数",
    "trigger_ratio": "触发比例",
    "trigger_stocks": "覆盖票数",
    "avg_per_stock": "每股机会",
    "completed_ratio": "完成比例",
    "cv": "间隔离散度",
    "mean_gap": "平均间隔天数",
    "top_bucket_ratio": "最多机会那只票的占比",
    "stop_loss_ratio": "止损占比",
    "take_profit_ratio": "止盈占比",
    "expire_ratio": "过期占比",
    "win_rate": "胜率",
    "avg_roi": "平均收益",
    "payoff_ratio": "盈亏比",
    "roi_p50": "ROI中位数",
    "top5_trade_profit_share": "前5笔贡献占比",
    "top5_stock_profit_share": "前5只票贡献占比",
    "avg_roi_without_top5": "去掉前5笔后均收益",
    "take_profit_profit_share": "止盈贡献占比",
    "stop_loss_profit_share": "止损贡献占比",
    "expire_profit_share": "到期贡献占比",
    "total_completed_investments": "完成笔数",
    "total_profit": "总盈亏",
    "avg_profit_per_investment": "单笔平均盈亏",
    "total_return": "账户收益",
    "max_drawdown": "最大回撤",
    "capital_utilization_ratio_pct": "资金利用率",
    "opportunity_merge_gap": "近邻间隔阈值",
}

# True = 越大越好；False = 越大越差；缺省 = 只说高低
_OUTCOME_HIGHER_IS_BETTER = {
    "total_opportunities": True,
    "trigger_ratio": True,
    "trigger_stocks": True,
    "take_profit_ratio": True,
    "completed_ratio": True,
    "total_return": True,
    "win_rate": True,
    "avg_roi": True,
    "avg_roi_without_top5": True,
    "payoff_ratio": True,
    "roi_p50": True,
    "total_profit": True,
    "avg_profit_per_investment": True,
    "take_profit_profit_share": True,
    "max_drawdown": False,
    "stop_loss_ratio": False,
    "stop_loss_profit_share": False,
    "expire_ratio": False,
    "expire_profit_share": False,
    "top_bucket_ratio": False,
    "top5_trade_profit_share": False,
    "top5_stock_profit_share": False,
    "cv": False,
}

# 系统级旋钮（goal / portfolio / fees / simulation 等）才翻译。
# settings.core 里是用户自定义名，一律原样显示。
_SYSTEM_KNOB_LABELS = {
    "stop_loss": "止损",
    "take_profit": "止盈",
    "opportunity_merge_gap": "近邻间隔阈值",
    "mode": "分配方式",
    "opportunity_selection": "选仓排序",
    "max_portfolio_size": "组合容量",
    "max_weight_per_stock": "单票权重上限",
    "initial_capital": "初始资金",
    "lots_per_trade": "每笔手数",
    "kelly_fraction": "Kelly系数",
    "skip_trade_when_insufficient": "资金不足时跳过",
    "save_trades": "保存成交",
    "save_equity_curve": "保存资金曲线",
}

# 系统可枚举取值
_ENUM_VALUE_LABELS = {
    "equal_capital": "等权资金",
    "equal_shares": "等股",
    "kelly": "Kelly",
    "custom": "自定义",
}

_RATIO_KEYS = frozenset(
    {
        "total_return",
        "win_rate",
        "avg_roi",
        "roi_p50",
        "max_drawdown",
        "trigger_ratio",
        "completed_ratio",
        "top_bucket_ratio",
        "stop_loss_ratio",
        "take_profit_ratio",
        "expire_ratio",
        "top5_trade_profit_share",
        "top5_stock_profit_share",
        "take_profit_profit_share",
        "stop_loss_profit_share",
        "expire_profit_share",
    }
)

_CROSS_LAYER = {
    "aligned": "机会变多，同号下游账户也变好",
    "finds_not_pays": "机会变多了，但同号下游账户没跟上",
    "pays_not_finds": "机会几乎没变，同号下游账户却变好了",
    "filter": "机会变少，同号下游账户更好（更像过滤）",
    "idle": "机会和下游账户几乎都没动",
    "worse": "机会变少，同号下游账户也变差",
    "hurts": "机会没变，同号下游账户变差",
}


def _format_opportunity_selection(value: Any) -> str:
    if not isinstance(value, list) or not value:
        return "到达顺序"
    parts = []
    for item in value:
        if not isinstance(item, dict):
            continue
        field = next((str(key) for key in item if str(key) != "src"), "")
        if not field:
            continue
        src = str(item.get("src") or "").strip()
        name = f"{src}.{field}" if src else field
        raw = item.get(field)
        if isinstance(raw, str):
            parts.append(f"{name} {raw.upper()}")
        else:
            parts.append(f"{name}×{raw}")
    return "，".join(parts) if parts else "到达顺序"


class CampaignLabels:
    """战役报告用的中文标签和数字格式。"""

    @staticmethod
    def layer_label(layer: Any) -> str:
        text = str(layer or "").strip()
        return _LAYER_LABELS.get(text, text or "这一层")

    @staticmethod
    def report_title(layer: Any) -> str:
        text = str(layer or "").strip()
        return _LAYER_REPORT_TITLE.get(text, "归因报告")

    @staticmethod
    def outcome_label(outcome: Any) -> str:
        text = str(outcome or "").strip()
        return _OUTCOME_LABELS.get(text, text or "这项")

    @staticmethod
    def knob_label(knob: Any) -> str:
        text = str(knob or "").strip()
        if not text:
            return "参数"
        # core.*：用户自定义，不翻译
        if text == "core" or text.startswith("core."):
            return text.split(".")[-1]
        if text in _SYSTEM_KNOB_LABELS:
            return _SYSTEM_KNOB_LABELS[text]
        last = text.split(".")[-1]
        if last in _SYSTEM_KNOB_LABELS:
            return _SYSTEM_KNOB_LABELS[last]
        return last

    @staticmethod
    def is_display_knob(knob: Any, value: Any) -> bool:
        """对照表里不展示布尔开关。"""
        if isinstance(value, bool):
            return False
        last = str(knob or "").split(".")[-1]
        return last != "close_invest"

    @staticmethod
    def format_number(key: Any, value: Any) -> str:
        if value is None or value == "":
            return "-"
        if isinstance(value, bool):
            return "是" if value else "否"
        if isinstance(value, str):
            mapped = _ENUM_VALUE_LABELS.get(value.strip())
            if mapped is not None:
                return mapped
            return value
        text_key = str(key or "")
        last = text_key.split(".")[-1]
        try:
            number = float(value)
        except (TypeError, ValueError):
            return str(value)
        if last in _RATIO_KEYS or last == "ratio" or last in (
            "stop_loss",
            "take_profit",
        ):
            signed = "+" if number > 0 and last in ("total_return", "avg_roi", "total_profit") else ""
            return f"{signed}{number * 100:.1f}%"
        # Tushare / 财报快照的 *_yoy、以及 *_pct，入库已经是百分数，不要再 ×100。
        if last.endswith("_yoy") or last.endswith("_pct"):
            return f"{number:.1f}%"
        if abs(number - round(number)) < 1e-9:
            return str(int(round(number)))
        if abs(number) >= 10:
            return f"{number:.1f}"
        return f"{number:.2f}"

    @classmethod
    def format_knob(cls, key: Any, value: Any) -> str:
        """对照表里的参数取值：None 显示「未使用」。"""
        if str(key or "").split(".")[-1] == "opportunity_selection":
            return _format_opportunity_selection(value)
        if value is None or value == "":
            return "未使用"
        scalar = KnobContrasts.scalar(value)
        if isinstance(value, dict) and scalar is not None:
            return f"使用({cls.format_number(key, scalar)})"
        if isinstance(value, dict):
            return "使用"
        if isinstance(value, str):
            mapped = _ENUM_VALUE_LABELS.get(value.strip())
            if mapped is not None:
                return mapped
        return cls.format_number(key, value)

    @classmethod
    def format_delta(cls, outcome: Any, delta: Any) -> str:
        """相对基准的差分文案。比例类用百分点，避免和水平值混淆。"""
        number = cls.maybe_float(delta)
        if number is None:
            return "-"
        if abs(number) < 1e-12:
            return "没变"
        last = str(outcome or "").split(".")[-1]
        sign = "+" if number > 0 else ""
        if last in _RATIO_KEYS or last == "ratio" or last in (
            "stop_loss",
            "take_profit",
        ):
            if abs(number) * 100 < 0.05:
                return "没变"
            return f"{sign}{number * 100:.1f}%"
        if last.endswith("_yoy") or last.endswith("_pct"):
            if abs(number) < 0.05:
                return "没变"
            return f"{sign}{number:.1f}%"
        if abs(number - round(number)) < 1e-9:
            return f"{sign}{int(round(number))}"
        if abs(number) >= 10:
            return f"{sign}{number:.1f}"
        return f"{sign}{number:.2f}"

    @staticmethod
    def higher_is_better(outcome: Any) -> Optional[bool]:
        """指标是否越大越好；未知则 None。"""
        text = str(outcome or "").strip()
        last = text.split(".")[-1]
        if last in _OUTCOME_HIGHER_IS_BETTER:
            return _OUTCOME_HIGHER_IS_BETTER[last]
        return _OUTCOME_HIGHER_IS_BETTER.get(text)

    @staticmethod
    def direction_phrase(outcome: str, rho: float) -> str:
        """参数越大时，这项怎么变。"""
        higher = CampaignLabels.higher_is_better(outcome)
        up = rho > 0
        if higher is True:
            return "往往越好" if up else "往往越差"
        if higher is False:
            return "往往越差" if up else "往往越好"
        return "往往越高" if up else "往往越低"

    @staticmethod
    def cross_layer_phrase(verdict: Any) -> str:
        return _CROSS_LAYER.get(str(verdict or "").strip(), "方向不清楚")

    @staticmethod
    def maybe_float(value: Any) -> Optional[float]:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
