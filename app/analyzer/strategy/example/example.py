#!/usr/bin/env python3
"""
HistoricLow 策略 - 寻找股票的历史低点，识别可能的买入机会
"""
from typing import Dict, List, Any, Optional
from loguru import logger

from app.analyzer.components.simulator.simulator import Simulator
from ...components.base_strategy import BaseStrategy
from .example_simulator import ExampleSimulator
from .settings import settings
from app.analyzer.components.investment import InvestmentRecorder

class Example(BaseStrategy):
    """HistoricLow 策略实现"""
    
    # 策略启用状态
    # 如果不启用，在start.py运行时则会自动跳过这个策略的机会扫描和模拟
    is_enabled = True
    
    def __init__(self, db, is_verbose: bool = False):
        super().__init__(
            db=db, 
            is_verbose=is_verbose,
            name="example",
            abbreviation="EXAMPLE"
        )
        
        # 加载策略设置
        self.settings = settings
        
        # 初始化投资记录器
        self.invest_recorder = InvestmentRecorder(self.settings['folder_name'])

        # 这个simulator是simulator库，当前文件夹下的simulator（ExampleSimulator）是存放simulator所有逻辑的主文件
        self.simulator = Simulator()

    def initialize(self):
        """初始化策略 - 调用父类的自动表管理"""
        super().initialize()

    # ========================================================
    # External (Bridge) APIs:
    # ========================================================
    def scan_opportunity(self, stock_id: str, data: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """扫描单只股票的投资机会"""
        # 示例：简单的机会识别逻辑
        if len(data) < 10:  # 需要至少10天的数据
            return None
        
        # 简单的示例逻辑：如果最近3天都是上涨，则认为是机会
        recent_data = data[-3:]
        if all(day.get('close', 0) > day.get('open', 0) for day in recent_data):
            return {
                'stock': {'id': stock_id},
                'date': recent_data[-1].get('date'),
                'price': recent_data[-1].get('close'),
                'reason': '连续3天上涨'
            }
        
        return None

    def simulate_one_day(self, stock_id: str, current_date: str, current_record: Dict[str, Any], 
                        historical_data: List[Dict[str, Any]], current_investment: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """模拟单日交易逻辑"""
        return ExampleSimulator.simulate_single_day(stock_id, current_date, current_record, historical_data, current_investment)

    def report(self, opportunities: List[Dict[str, Any]]) -> None:
        # 这个函数会在策略启用时自动调用，是用来报告策略的扫描结果的
        # 这里可以添加一些汇总的逻辑，比如：
        # - 为找到的机会加上历史模拟结果

        if not opportunities:
            logger.info("🔍 未发现投资机会")
            return
        
        logger.info(f"🔍 发现 {len(opportunities)} 个投资机会")
        

    # ========================================================
    # Core logic:
    # ========================================================
    # 多进程扫描逻辑已移至StrategyExecutor中


    # ========================================================
    # Result presentation:
    # ========================================================

    def stock_summary(self, result: Dict[str, Any]) -> Dict[str, Any]:
        # 这个函数会在策略启用时自动调用，是用来汇总单只股票的模拟结果的
        # 这里可以添加一些汇总的逻辑，比如：
        # - 为找到的机会加上历史模拟结果
        return {}