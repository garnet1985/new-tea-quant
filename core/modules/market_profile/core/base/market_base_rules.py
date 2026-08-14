#!/usr/bin/env python3
"""市场规则基类（Market Base Rules）- 提供默认实现，子类只需提供settings。"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Sequence, Tuple

from ..services import (
    AmplitudeLimitService,
    LotSizeService,
    SettlementService,
)
from ..services.lot_size_service import LotSizeResolved


class MarketBaseRules(ABC):
    """市场规则基类。

    子类只需：
    1. 提供 settings 属性（返回配置字典）
    2. 提供 profile_id 属性
    3. 可选覆盖特殊方法（如果算法不同）

    基类提供：
    - 配置验证和默认值应用
    - 所有方法的默认实现
    - 从 settings 自动初始化
    """

    # 子类必须提供的属性
    @property
    @abstractmethod
    def profile_id(self) -> str:
        """市场配置ID（如 'china_a_stock', 'hong_kong'）"""
        pass

    @property
    @abstractmethod
    def settings(self) -> Dict[str, Any]:
        """市场配置字典"""
        pass

    # ==================== 初始化和验证 ====================

    def __init__(self) -> None:
        """初始化：验证配置、应用默认值、从settings初始化"""
        self._validated_settings = self._validate_and_apply_defaults(self.settings)
        self._init_from_settings()

    def _validate_and_apply_defaults(self, raw_settings: Dict[str, Any]) -> Dict[str, Any]:
        """验证配置并应用默认值。

        Args:
            raw_settings: 原始配置字典

        Returns:
            验证后的配置字典
        """
        validated = {}

        # 元数据（可选）
        meta = raw_settings.get("meta", {})
        validated["meta"] = {
            "name": str(meta.get("name", "")),
            "description": str(meta.get("description", "")),
        }

        # 交收规则
        settlement = raw_settings.get("settlement", {})
        validated["settlement"] = {
            "t_plus": int(settlement.get("t_plus", 0)),  # 默认T+0
        }

        # 涨跌幅规则
        amplitude = raw_settings.get("amplitude_limit", {})
        validated["amplitude_limit"] = {
            "default_ratio": float(amplitude.get("default_ratio", 0.0)),  # 默认无限制
            "price_round_decimals": int(amplitude.get("price_round_decimals", 2)),
            "default_risk": amplitude.get("default_risk", {}),
            "rules": amplitude.get("rules", []),
        }

        # 整手规则
        lot_size = raw_settings.get("lot_size", {})
        validated["lot_size"] = {
            "default_min_lot": int(lot_size.get("default_min_lot", 1)),  # 默认1股/手
            "default_lot_step": int(lot_size.get("default_lot_step", 1)),  # 默认步长1
            "rules": lot_size.get("rules", []),
        }

        return validated

    def _init_from_settings(self) -> None:
        """从settings初始化所有属性"""
        settings = self._validated_settings

        # 元数据
        meta = settings["meta"]
        self._name = meta["name"]
        self._description = meta["description"]

        # 涨跌幅规则
        amplitude = settings["amplitude_limit"]
        self._default_ratio = amplitude["default_ratio"]
        self._price_decimals = amplitude["price_round_decimals"]
        self._default_risk_ratios = AmplitudeLimitService.parse_risk_ratios(amplitude["default_risk"])
        self._amplitude_entries = AmplitudeLimitService.parse_entries(amplitude, self._default_ratio)

        # 整手规则
        lot = settings["lot_size"]
        self._default_min_lot = lot["default_min_lot"]
        self._default_lot_step = lot["default_lot_step"]
        self._lot_entries = LotSizeService.parse_entries(lot, self._default_min_lot, self._default_lot_step)

        # 交收规则
        settlement = settings["settlement"]
        self._t_plus = settlement["t_plus"]

    # ==================== 元数据属性（默认实现） ====================

    @property
    def name(self) -> str:
        """市场名称"""
        return self._name

    @property
    def description(self) -> str:
        """市场描述"""
        return self._description

    def get_name(self) -> str:
        """获取市场名称"""
        return self._name

    def get_description(self) -> str:
        """获取市场描述"""
        return self._description

    def get_profile_id(self) -> str:
        """获取市场配置ID"""
        return self.profile_id

    # ==================== 涨跌幅限制（默认实现） ====================

    def get_limit_ratio(self) -> float:
        """获取默认涨跌幅限制比例"""
        return self._default_ratio

    def get_limit_ratio_for_stock(
        self, stock_id: str, status_tags: Optional[Sequence[str]] = None
    ) -> float:
        """获取特定股票的涨跌幅限制比例。子类可覆盖实现特殊逻辑。"""
        return AmplitudeLimitService.resolve_ratio(
            stock_id, status_tags, self._amplitude_entries, self._default_ratio, self._default_risk_ratios
        )

    def compute_limit_prices(self, prev_close: float) -> Tuple[float, float]:
        """计算涨跌停价格（使用默认规则）"""
        return AmplitudeLimitService.compute_limit_prices(prev_close, self._default_ratio, self._price_decimals)

    def compute_limit_prices_for_stock(
        self, prev_close: float, stock_id: str, status_tags: Optional[Sequence[str]] = None
    ) -> Tuple[float, float]:
        """为特定股票计算涨跌停价格。子类可覆盖实现特殊逻辑。"""
        ratio = self.get_limit_ratio_for_stock(stock_id, status_tags)
        return AmplitudeLimitService.compute_limit_prices(prev_close, ratio, self._price_decimals)

    def is_within_price_limit(self, current_price: float, prev_close: float) -> bool:
        """判断价格是否在涨跌幅范围内（使用默认规则）"""
        limit_up, limit_down = self.compute_limit_prices(prev_close)
        return AmplitudeLimitService.is_within_limit(current_price, limit_up, limit_down)

    def is_within_price_limit_for_stock(
        self, current_price: float, prev_close: float, stock_id: str, status_tags: Optional[Sequence[str]] = None
    ) -> bool:
        """判断特定股票的价格是否在涨跌幅范围内。子类可覆盖实现特殊逻辑。"""
        limit_up, limit_down = self.compute_limit_prices_for_stock(prev_close, stock_id, status_tags)
        return AmplitudeLimitService.is_within_limit(current_price, limit_up, limit_down)

    def is_at_limit_up(
        self,
        price: float,
        prev_close: float,
        stock_id: str,
        status_tags: Optional[Sequence[str]] = None,
    ) -> bool:
        """成交价是否视为涨停（贴涨停 → 通常难买入）。

        无涨跌幅市场、无效 ``prev_close``/``price`` 时返回 False（不挡交易）。
        """
        if float(prev_close or 0.0) <= 0 or float(price or 0.0) <= 0:
            return False
        ratio = self.get_limit_ratio_for_stock(stock_id, status_tags)
        limit_up, _ = self.compute_limit_prices_for_stock(
            prev_close, stock_id, status_tags
        )
        return AmplitudeLimitService.is_at_limit_up(
            price,
            limit_up,
            ratio=ratio,
            price_decimals=self._price_decimals,
        )

    def is_at_limit_down(
        self,
        price: float,
        prev_close: float,
        stock_id: str,
        status_tags: Optional[Sequence[str]] = None,
    ) -> bool:
        """成交价是否视为跌停（贴跌停 → 通常难卖出）。

        无涨跌幅市场、无效 ``prev_close``/``price`` 时返回 False（不挡交易）。
        """
        if float(prev_close or 0.0) <= 0 or float(price or 0.0) <= 0:
            return False
        ratio = self.get_limit_ratio_for_stock(stock_id, status_tags)
        _, limit_down = self.compute_limit_prices_for_stock(
            prev_close, stock_id, status_tags
        )
        return AmplitudeLimitService.is_at_limit_down(
            price,
            limit_down,
            ratio=ratio,
            price_decimals=self._price_decimals,
        )

    # ==================== 整手规则（默认实现） ====================

    def get_min_lot(self) -> int:
        """获取默认最小买入单位"""
        return self._default_min_lot

    def get_lot_step(self) -> int:
        """获取默认每手步长"""
        return self._default_lot_step

    def is_valid_quantity(self, quantity: int) -> bool:
        """判断数量是否符合整手规则（使用默认规则）。子类可覆盖实现特殊逻辑。"""
        resolved = LotSizeService.resolve(None, self._lot_entries, self._default_min_lot, self._default_lot_step)
        return LotSizeService.is_valid_quantity(quantity, resolved)

    def is_valid_quantity_for_stock(self, quantity: int, stock_id: str) -> bool:
        """判断特定股票的数量是否符合整手规则。子类可覆盖实现特殊逻辑。"""
        resolved = LotSizeService.resolve(stock_id, self._lot_entries, self._default_min_lot, self._default_lot_step)
        return LotSizeService.is_valid_quantity(quantity, resolved)

    def floor_quantity(self, target_quantity: int) -> int:
        """计算符合整手规则的最大买入数量（使用默认规则）。子类可覆盖实现特殊逻辑。"""
        resolved = LotSizeService.resolve(None, self._lot_entries, self._default_min_lot, self._default_lot_step)
        return LotSizeService.floor_quantity(target_quantity, resolved)

    def floor_quantity_for_stock(self, target_quantity: int, stock_id: str) -> int:
        """计算特定股票符合整手规则的最大买入数量。子类可覆盖实现特殊逻辑。"""
        resolved = LotSizeService.resolve(stock_id, self._lot_entries, self._default_min_lot, self._default_lot_step)
        return LotSizeService.floor_quantity(target_quantity, resolved)

    def resolve_lot_size(self, stock_id: str) -> LotSizeResolved:
        """解析特定股票的整手规则"""
        return LotSizeService.resolve(stock_id, self._lot_entries, self._default_min_lot, self._default_lot_step)

    # ==================== 交收规则（默认实现） ====================

    def get_settlement_period(self) -> int:
        """获取交收周期（T+N）"""
        return SettlementService.get_settlement_period(self._t_plus)

    def is_allowed_to_sell(self, days_held: int) -> bool:
        """判断是否允许卖出（交收规则）"""
        return SettlementService.is_allowed_to_settle(days_held, self._t_plus)


__all__ = ["MarketBaseRules"]