#!/usr/bin/env python3
"""
历史低点策略
"""

from typing import Dict, List, Any
from loguru import logger

# 导入抽象基类
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from base_strategy import BaseStrategy

from tables.meta.model import HLMetaModel
from tables.opportunity_history.model import HLOpportunityHistoryModel
from tables.strategy_summary.model import HLStrategySummaryModel

class HistoricLowStrategy(BaseStrategy):
    def __init__(self):
        super().__init__()
        self.strategy_name = "Historic Low"
        self.strategy_description = "寻找股票的历史低点，识别可能的买入机会"

        self.db_tables = {
            "meta": HLMetaModel(self.db),
            "opportunity_history": HLOpportunityHistoryModel(self.db),
            "strategy_summary": HLStrategySummaryModel(self.db)
        }


    
    def scan(self):
        return super().scan()

    def test(self):
        return super().test()

    def report(self):
        return super().report()
