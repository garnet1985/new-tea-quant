#!/usr/bin/env python3
"""整手规则服务（Lot Size Service）。"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class LotSizeEntry:
    """整手规则条目（针对特定股票）。"""

    entry_key: str  # 规则键（如 "ke_chuang_ban"）
    matching: Dict[str, Any]  # 匹配配置
    min_lot: int  # 最小买入单位
    lot_step: int  # 每手步长


@dataclass(frozen=True)
class LotSizeResolved:
    """解析后的整手规则。"""

    min_lot: int
    lot_step: int
    board_entry_key: str = "default"


class LotSizeService:
    """整手规则服务。

    为所有公有方法提供整手规则计算功能。
    """

    @staticmethod
    def parse_entries(config: Dict[str, Any], default_min_lot: int, default_lot_step: int) -> List[LotSizeEntry]:
        """解析整手规则条目。

        Args:
            config: 配置字典
            default_min_lot: 默认最小买入单位
            default_lot_step: 默认每手步长

        Returns:
            整手规则条目列表
        """
        from .matching_service import MatchingService

        entries: List[LotSizeEntry] = []
        for item in config.get("rules") or []:
            if not isinstance(item, dict):
                continue

            matching = item.get("matching")
            if not isinstance(matching, dict):
                continue

            try:
                min_lot = max(int(item.get("min_lot", default_min_lot)), 1)
            except (TypeError, ValueError):
                min_lot = default_min_lot

            try:
                lot_step = max(int(item.get("lot_step", default_lot_step)), 1)
            except (TypeError, ValueError):
                lot_step = default_lot_step

            entries.append(
                LotSizeEntry(
                    entry_key=str(item.get("key") or "").strip(),
                    matching=matching,
                    min_lot=min_lot,
                    lot_step=lot_step,
                )
            )

        # 按前缀长度排序
        entries.sort(key=lambda e: MatchingService.max_matching_prefix_len(e.matching), reverse=True)
        return entries

    @staticmethod
    def resolve(stock_id: Optional[str], entries: List[LotSizeEntry], default_min_lot: int, default_lot_step: int) -> LotSizeResolved:
        """解析特定股票的整手规则。

        Args:
            stock_id: 股票ID（可选）
            entries: 整手规则条目列表
            default_min_lot: 默认最小买入单位
            default_lot_step: 默认每手步长

        Returns:
            LotSizeResolved实例
        """
        from .matching_service import MatchingService

        if stock_id is None:
            return LotSizeResolved(
                min_lot=default_min_lot,
                lot_step=default_lot_step,
                board_entry_key="default",
            )

        # 查找匹配的规则条目
        for entry in entries:
            if MatchingService.match_stock_id(stock_id, entry.matching):
                return LotSizeResolved(
                    min_lot=entry.min_lot,
                    lot_step=entry.lot_step,
                    board_entry_key=entry.entry_key,
                )

        return LotSizeResolved(
            min_lot=default_min_lot,
            lot_step=default_lot_step,
            board_entry_key="default",
        )

    @staticmethod
    def is_valid_quantity(quantity: int, resolved: LotSizeResolved) -> bool:
        """判断数量是否符合整手规则。

        Args:
            quantity: 买入数量
            resolved: 解析后的整手规则

        Returns:
            True表示符合规则
        """
        if quantity < resolved.min_lot:
            return False

        if (quantity - resolved.min_lot) % resolved.lot_step != 0:
            return False

        return True

    @staticmethod
    def floor_quantity(target_quantity: int, resolved: LotSizeResolved) -> int:
        """计算符合整手规则的最大买入数量。

        Args:
            target_quantity: 目标买入数量
            resolved: 解析后的整手规则

        Returns:
            符合规则的实际买入数量
        """
        if target_quantity < resolved.min_lot:
            return 0

        extra = target_quantity - resolved.min_lot
        steps = extra // resolved.lot_step

        return resolved.min_lot + steps * resolved.lot_step


__all__ = ["LotSizeService", "LotSizeEntry", "LotSizeResolved"]