#!/usr/bin/env python3
"""涨跌幅限制服务（Amplitude Limit Service）。"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple


@dataclass(frozen=True)
class AmplitudeLimitEntry:
    """涨跌幅规则条目（针对特定股票）。"""

    entry_key: str  # 规则键
    matching: Dict[str, Any]  # 匹配配置
    ratio: float  # 涨跌幅比例
    risk_ratios: Dict[str, float] = field(default_factory=dict)  # 风险标签涨跌幅


class AmplitudeLimitService:
    """涨跌幅限制服务。

    为所有公有方法提供涨跌幅计算功能。
    """

    @staticmethod
    def parse_entries(config: Dict[str, Any], default_ratio: float) -> List[AmplitudeLimitEntry]:
        """解析涨跌幅规则条目。

        Args:
            config: 配置字典
            default_ratio: 默认涨跌幅比例

        Returns:
            涨跌幅规则条目列表
        """
        from .matching_service import MatchingService

        entries: List[AmplitudeLimitEntry] = []
        for item in config.get("rules") or []:
            if not isinstance(item, dict):
                continue

            matching = item.get("matching")
            if not isinstance(matching, dict):
                continue

            try:
                ratio = float(item.get("ratio", default_ratio))
            except (TypeError, ValueError):
                ratio = default_ratio

            entries.append(
                AmplitudeLimitEntry(
                    entry_key=str(item.get("key") or "").strip(),
                    matching=matching,
                    ratio=ratio,
                    risk_ratios=AmplitudeLimitService.parse_risk_ratios(item.get("risk")),
                )
            )

        # 按前缀长度排序
        entries.sort(key=lambda e: MatchingService.max_matching_prefix_len(e.matching), reverse=True)
        return entries

    @staticmethod
    def parse_risk_ratios(risk_config: Any) -> Dict[str, float]:
        """解析风险标签涨跌幅配置"""
        if not isinstance(risk_config, dict):
            return {}

        result: Dict[str, float] = {}
        for tag, cfg in risk_config.items():
            if isinstance(cfg, dict):
                try:
                    result[tag] = float(cfg.get("ratio", 0.0))
                except (TypeError, ValueError):
                    pass

        return result

    @staticmethod
    def resolve_ratio(
        stock_id: str,
        status_tags: Optional[Sequence[str]],
        entries: List[AmplitudeLimitEntry],
        default_ratio: float,
        default_risk_ratios: Dict[str, float],
    ) -> float:
        """解析特定股票的涨跌幅比例。

        Args:
            stock_id: 股票ID
            status_tags: 状态标签
            entries: 涨跌幅规则条目列表
            default_ratio: 默认涨跌幅比例
            default_risk_ratios: 默认风险标签涨跌幅

        Returns:
            涨跌幅比例
        """
        from .matching_service import MatchingService

        # 查找匹配的规则条目
        matched_entry = None
        for entry in entries:
            if MatchingService.match_stock_id(stock_id, entry.matching):
                matched_entry = entry
                break

        if matched_entry is not None:
            base_ratio = matched_entry.ratio
            risk_map = matched_entry.risk_ratios
        else:
            base_ratio = default_ratio
            risk_map = default_risk_ratios

        # 应用风险标签
        if status_tags:
            for tag in status_tags:
                if tag in risk_map:
                    return risk_map[tag]

        return base_ratio

    @staticmethod
    def compute_limit_prices(prev_close: float, ratio: float, price_decimals: int) -> Tuple[float, float]:
        """计算涨跌停价格。

        Args:
            prev_close: 前收盘价
            ratio: 涨跌幅比例
            price_decimals: 价格小数位数

        Returns:
            (涨停价, 跌停价)
        """
        if prev_close <= 0:
            return (0.0, 0.0)

        limit_up = round(prev_close * (1 + ratio), price_decimals)
        limit_down = round(prev_close * (1 - ratio), price_decimals)

        return (limit_up, limit_down)

    @staticmethod
    def is_within_limit(current_price: float, limit_up: float, limit_down: float) -> bool:
        """判断价格是否在涨跌幅范围内"""
        return limit_down <= current_price <= limit_up


__all__ = ["AmplitudeLimitService", "AmplitudeLimitEntry"]