#!/usr/bin/env python3
"""
Waly 策略 - 寻找市盈率小于 1/国债利率*2 and asset debt ratio < 0.5 的股票
"""
from typing import Dict, List, Any, Optional
from loguru import logger

from app.analyzer.components.simulator.simulator import Simulator
from ...components.base_strategy import BaseStrategy
from .settings import settings
from app.analyzer.components.investment import InvestmentRecorder

class Waly(BaseStrategy):
    """Waly 策略实现"""
    
    def __init__(self, db=None, is_verbose: bool = False):
        super().__init__(
            db=db, 
            is_verbose=is_verbose,
            name="Waly",
            key="Waly",
            version="1.0.0"
        )
        if db is not None:
            super().initialize()

    def scan_opportunity(self, stock_id: str, data: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """扫描单只股票的投资机会"""
        # 获取股票的市盈率和国债利率

        logger.info(f"Waly 策略扫描股票: {data}")

        breakpoint()

        if not self.is_PE_reached_condition(data.get('pe', 0), data.get('bond_rate', 0)):
            return None
        if not self.is_asset_debt_ratio_reached_condition(data.get('asset_debt_ratio', 0)):
            return None

        return self.to_opportunity(stock_id, data)

    def is_PE_reached_condition(self, pe: float, bond_rate: float) -> bool:
        return pe < 1 / bond_rate * 2

    def is_asset_debt_ratio_reached_condition(self, asset_debt_ratio: float) -> bool:
        return asset_debt_ratio < 0.5