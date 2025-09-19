#!/usr/bin/env python3
"""
HistoricLow 策略 - 寻找股票的历史低点，识别可能的买入机会
"""
from typing import Dict, List, Any, Optional, Tuple
from loguru import logger

from app.analyzer.components.entity.entity_builder import EntityBuilder
from app.analyzer.components.simulator.simulator import Simulator
from app.analyzer.strategy.HL.HL_service import HistoricLowService
from ...components.base_strategy import BaseStrategy
from .HL_simulator import HistoricLowSimulator
from .settings import settings
from app.analyzer.components.investment import InvestmentRecorder

class HistoricLow(BaseStrategy):
    """HistoricLow 策略实现"""
    
    # 策略启用状态
    is_enabled = True
    
    def __init__(self, db, is_verbose: bool = False):
        super().__init__(
            db=db, 
            is_verbose=is_verbose,
            name="HistoricLow",
            abbreviation="HL"
        )
        
        # 加载策略设置
        self.settings = settings
        
        # 初始化投资记录器
        self.invest_recorder = InvestmentRecorder(self.settings['folder_name'])

        self.simulator = Simulator()

    def initialize(self):
        """初始化策略 - 调用父类的自动表管理"""
        super().initialize()

    # ========================================================
    # Core API: Scan opportunity
    # ========================================================
    @staticmethod
    def scan_opportunity(stock: Dict[str, Any], data: List[Dict[str, Any]], settings: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        # """扫描单只股票的投资机会"""
        # return HistoricLowSimulator.scan_single_stock(stock_id, data)

        daily_klines = data.get('klines', {}).get('daily', [])

        """扫描单只股票的投资机会"""
        if not data:
            return None
        
        # 分割数据为冻结期和历史期
        freeze_records, history_records = HistoricLowService.split_freeze_and_history_data(daily_klines)
        
        # 寻找历史低点
        low_points = HistoricLowService.find_low_points(history_records)
        
        # 从低点中寻找投资机会
        opportunity = HistoricLow._find_opportunity_from_low_points(stock, low_points, freeze_records, history_records)
        
        return opportunity

    @staticmethod
    def _find_opportunity_from_low_points(stock: Dict[str, Any], low_points: List[Dict[str, Any]], freeze_data: List[Dict[str, Any]], history_data: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """从历史低点中寻找投资机会（恢复风控过滤：跌停/新低/振幅/斜率）"""
        if not low_points or not freeze_data:
            return None

        record_of_today = freeze_data[-1]

        # 风控过滤（与旧算法一致的语义）：
        # 1) 不处于连续跌停
        if not HistoricLowService.is_out_of_continuous_limit_down(freeze_data):
            return None
        # 2) 冻结期无新低
        if not HistoricLowService.has_no_new_low_during_freeze(freeze_data):
            return None
        # 3) 振幅足够
        if not HistoricLowService.is_amplitude_sufficient(freeze_data):
            return None
        # 4) 斜率不过陡（满足上升/止跌的斜率阈值）
        if not HistoricLowService.is_slope_sufficient(freeze_data):
            return None

        # 核心入场条件：当前价位位于以历史低点为参考的投资区间内
        for low_point in low_points:
            if HistoricLowService.is_in_invest_range(record_of_today, low_point, freeze_data):
                opportunity = EntityBuilder.to_opportunity(
                    stock=stock,
                    date=record_of_today.get('date'),
                    price=record_of_today.get('close'),
                    lower_bound=low_point.get('invest_lower_bound'),
                    upper_bound=low_point.get('invest_upper_bound'),
                    extra_fields={
                        'opportunity_record': record_of_today,
                        'low_point_ref': low_point,
                    }
                )
                return opportunity

        return None




    # ========================================================
    # Core API: Simulate
    # ========================================================








































    def simulate_one_day(self, stock_id: str, current_date: str, current_record: Dict[str, Any], 
                        historical_data: List[Dict[str, Any]], current_investment: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """模拟单日交易逻辑"""
        return HistoricLowSimulator.simulate_single_day(stock_id, current_date, current_record, historical_data, current_investment)

    def report(self, opportunities: List[Dict[str, Any]]) -> None:
        """报告投资机会"""
        if not opportunities:
            logger.info("🔍 未发现投资机会")
            return
        
        logger.info(f"🔍 发现 {len(opportunities)} 个投资机会")
        
        # 按股票分组显示
        stock_opportunities = {}
        for opp in opportunities:
            stock_id = opp.get('stock', {}).get('id', 'unknown')
            if stock_id not in stock_opportunities:
                stock_opportunities[stock_id] = []
            stock_opportunities[stock_id].append(opp)
        
        for stock_id, opps in stock_opportunities.items():
            logger.info(f"📈 {stock_id}: {len(opps)} 个机会")

    # ========================================================
    # Core logic:
    # ========================================================
    # 多进程扫描逻辑已移至StrategyExecutor中

    # ========================================================
    # Result presentation:
    # ========================================================

    def to_presentable_report(self, opportunities: List[Dict[str, Any]]) -> None:
        """
        将投资机会转换为可呈现的报告格式
        
        Args:
            opportunities: 投资机会列表
        """
        if not opportunities:
            logger.info("📊 无投资机会可报告")
            return
        
        logger.info("📊 HistoricLow 策略扫描报告")
        logger.info("=" * 50)
        
        # 按股票分组统计
        stock_stats = {}
        for opp in opportunities:
            stock_id = opp.get('stock', {}).get('id', 'unknown')
            if stock_id not in stock_stats:
                stock_stats[stock_id] = 0
            stock_stats[stock_id] += 1
        
        # 显示统计信息
        logger.info(f"📈 发现投资机会: {len(opportunities)} 个")
        logger.info(f"📊 涉及股票: {len(stock_stats)} 只")
        
        # 显示每只股票的详细信息
        for stock_id, count in sorted(stock_stats.items()):
            logger.info(f"  {stock_id}: {count} 个机会")
        
        logger.info("=" * 50)



    def stock_summary(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        在HL策略中，按需简化每个投资的 opportunity 字段
        
        Args:
            result: 单只股票的模拟结果（包含 investments/settled_investments）
            
        Returns:
            Dict: 追加到默认summary的track（此处无额外统计，返回空）
        """
        # 就地简化：仅保留 HL 关键信息，避免污染通用框架
        for key in ('settled_investments', 'investments'):
            for inv in result.get(key, []) or []:
                opp = inv.get('opportunity')
                if not opp:
                    continue
                inv['opportunity'] = {
                    'date': opp.get('date'),
                    'price': opp.get('price'),
                    'lower_bound': opp.get('lower_bound'),
                    'upper_bound': opp.get('upper_bound'),
                    'low_point_ref': opp.get('low_point_ref')
                }
        # 不新增额外summary字段
        return {}