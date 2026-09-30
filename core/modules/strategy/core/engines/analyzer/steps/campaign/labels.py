"""战役中文标签：旋钮 / 层 / 指标。"""
from __future__ import annotations

from typing import Any, Optional

_LAYER_LABELS = {
    "enumerate": "机会",
    "price_factor": "价格",
    "portfolio": "账户",
}

_OUTCOME_LABELS = {
    "total_opportunities": "机会数",
    "trigger_ratio": "触发比例",
    "avg_per_stock": "每股机会",
    "completed_ratio": "完成比例",
    "win_rate": "胜率",
    "avg_roi": "平均收益",
    "total_completed_investments": "完成笔数",
    "total_profit": "总盈亏",
    "total_return": "账户收益",
    "max_drawdown": "最大回撤",
    "capital_utilization_ratio_pct": "资金利用率",
}

# True = 越大越好；False = 越大越差；None = 只说高低
_OUTCOME_HIGHER_IS_BETTER = {
    "total_return": True,
    "win_rate": True,
    "avg_roi": True,
    "total_profit": True,
    "completed_ratio": True,
    "max_drawdown": False,
}

_KNOB_LAST = {
    "rsi_oversold_threshold": "RSI超卖阈值",
    "rsi_length": "RSI周期",
    "max_pe_percentile": "PE分位上限",
    "min_netprofit_yoy": "净利同比门槛",
    "min_pe_history_days": "PE最短历史",
    "pe_metric": "PE口径",
}

_RATIO_KEYS = frozenset(
    {
        "total_return",
        "win_rate",
        "avg_roi",
        "max_drawdown",
        "trigger_ratio",
        "completed_ratio",
    }
)

_CROSS_LAYER = {
    "aligned": "机会和账户一起变好",
    "finds_not_pays": "机会多了，账户没跟上",
    "pays_not_finds": "机会几乎没变，账户变好了",
    "filter": "机会少了，账户更好（更像过滤）",
    "idle": "几乎没作用",
    "worse": "机会和账户一起变差",
    "hurts": "机会没变，账户变差",
}


class CampaignLabels:
    """战役报告用的中文标签和数字格式。"""

    @staticmethod
    def layer_label(layer: Any) -> str:
        text = str(layer or "").strip()
        return _LAYER_LABELS.get(text, text or "这一层")

    @staticmethod
    def outcome_label(outcome: Any) -> str:
        text = str(outcome or "").strip()
        return _OUTCOME_LABELS.get(text, text or "这项")

    @staticmethod
    def knob_label(knob: Any) -> str:
        text = str(knob or "").strip()
        if not text:
            return "旋钮"
        last = text.split(".")[-1]
        if last in _KNOB_LAST:
            return _KNOB_LAST[last]
        if "stop_loss" in text and last == "ratio":
            return "止损"
        if "take_profit" in text and last == "ratio":
            return "止盈"
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
        text_key = str(key or "")
        last = text_key.split(".")[-1]
        try:
            number = float(value)
        except (TypeError, ValueError):
            return str(value)
        if last in _RATIO_KEYS or last == "ratio" or last.endswith("_yoy"):
            signed = "+" if number > 0 and last in ("total_return", "avg_roi", "total_profit") else ""
            return f"{signed}{number * 100:.1f}%"
        if last.endswith("_pct"):
            return f"{number:.1f}%"
        if abs(number - round(number)) < 1e-9:
            return str(int(round(number)))
        if abs(number) >= 10:
            return f"{number:.1f}"
        return f"{number:.2f}"

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
        if last in _RATIO_KEYS or last == "ratio" or last.endswith("_yoy"):
            if abs(number) * 100 < 0.05:
                return "没变"
            return f"{sign}{number * 100:.1f}个百分点"
        if last.endswith("_pct"):
            return f"{sign}{number:.1f}百分点"
        if abs(number - round(number)) < 1e-9:
            return f"{sign}{int(round(number))}"
        if abs(number) >= 10:
            return f"{sign}{number:.1f}"
        return f"{sign}{number:.2f}"

    @staticmethod
    def direction_phrase(outcome: str, rho: float) -> str:
        """旋钮越大时，这项怎么变。"""
        higher = _OUTCOME_HIGHER_IS_BETTER.get(outcome)
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
