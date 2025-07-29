#!/usr/bin/env python3
"""
策略管理器 - 负责初始化和管理所有策略的表模型
"""

from loguru import logger
from utils.db.db_manager import DatabaseManager

class StrategyManager:
    """策略管理器"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.strategy_models = {}
        
    def initialize_strategies(self):
        """初始化所有策略的表模型"""
        
        try:
            # 初始化 HistoricLow 策略的表模型
            self._initialize_historic_low_strategy()
            
            # 可以在这里添加其他策略的初始化
            # self._initialize_other_strategy()
            
        except Exception as e:
            logger.error(f"❌ 策略表模型初始化失败: {e}")
            raise
    
    def _initialize_historic_low_strategy(self):
        """初始化 HistoricLow 策略的表模型"""
        try:
            from .historicLow.tables.meta.model import HLMetaModel
            from .historicLow.tables.opportunity_history.model import HLOpportunityHistoryModel
            from .historicLow.tables.strategy_summary.model import HLStrategySummaryModel
            
            # 初始化各个表模型
            self.strategy_models['HL_meta'] = HLMetaModel(self.db)
            self.strategy_models['HL_opportunity_history'] = HLOpportunityHistoryModel(self.db)
            self.strategy_models['HL_strategy_summary'] = HLStrategySummaryModel(self.db)
            
        except Exception as e:
            logger.error(f"❌ HistoricLow 策略表模型初始化失败: {e}")
            raise
    
    def get_model(self, model_name: str):
        """获取指定的表模型"""
        return self.strategy_models.get(model_name)
    
    def get_all_models(self):
        """获取所有表模型"""
        return self.strategy_models 