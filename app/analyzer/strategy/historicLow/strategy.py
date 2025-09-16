#!/usr/bin/env python3
"""
HistoricLow 策略 - 寻找股票的历史低点，识别可能的买入机会
"""
from doctest import debug
import time
from typing import Dict, List, Any, Tuple, Optional
from loguru import logger

from app.analyzer.libs.simulator.simulator import Simulator
from ...libs.base_strategy import BaseStrategy
from .strategy_service import HistoricLowService
from .strategy_entity import HistoricLowEntity
from .strategy_simulator import HLSimulator
from .strategy_settings import strategy_settings
from app.analyzer.libs.investment import InvestmentRecorder
from app.data_source.data_source_service import DataSourceService

class HistoricLowStrategy(BaseStrategy):
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
        self.strategy_settings = strategy_settings
        
        # 初始化投资记录器
        self.invest_recorder = InvestmentRecorder("historicLow")

        self.simulator = Simulator()

    def initialize(self):
        self._initialize_tables()

    def _initialize_tables(self):
        self.required_tables = {
            "stock_index": self.db.get_table_instance("stock_index"),
            "stock_kline": self.db.get_table_instance("stock_kline"),
            "adj_factor": self.db.get_table_instance("adj_factor"),
            # todo: will add storage later, for now use file system.
            # "meta": HLMetaModel(self.db),
            # "opportunity_history": HLOpportunityHistoryModel(self.db),
            # "strategy_summary": HLStrategySummaryModel(self.db)
        }

    # ========================================================
    # External (Bridge) APIs:
    # ========================================================
    async def scan(self) -> List[Dict[str, Any]]:
        stock_idx = self.required_tables["stock_index"].load_filtered_index()

        if not stock_idx:
            return []

        opportunities = self._scan_stocks_with_worker(stock_idx)

        self.report(opportunities)

        return opportunities

    def simulate(self) -> Dict[str, Any]:
        # 运行模拟 - 传递单日模拟函数和自定义汇总函数
        result = self.simulator.run(
            settings=strategy_settings,
            on_simulate_one_day=HLSimulator.simulate_single_day,
            on_single_stock_summary=self._simplify_opportunity_structure,
            on_simulate_complete=HLSimulator.present_final_report
        )
        return result

    def _simplify_opportunity_structure(self, result: Dict[str, Any]) -> Dict[str, Any]:
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

    def _scan_stocks_with_worker(self, stock_idx: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """使用多进程扫描股票"""
        from utils.worker.multi_process.process_worker import ProcessWorker
        
        # 构建任务
        jobs = []
        for stock in stock_idx:
            job = {
                'stock': stock,
                'data': self.required_tables["stock_kline"].load_stock_kline_data(stock['id'], 'daily')
            }
            jobs.append(job)
        
        # 使用多进程执行
        worker = ProcessWorker(job_executor=self._scan_single_stock)
        results = worker.run_jobs(jobs)
        
        # 提取投资机会
        opportunities = []
        for result in results:
            if result.success and result.result_data:
                opportunities.extend(result.result_data)
        
        return opportunities

    def _scan_single_stock(self, job: Dict[str, Any]) -> List[Dict[str, Any]]:
        """扫描单只股票的投资机会"""
        stock = job['stock']
        daily_k_lines = job['data']
        
        if not daily_k_lines:
            return []
        
        # 使用HLSimulator的扫描逻辑
        opportunities = []
        for i in range(len(daily_k_lines)):
            current_data = daily_k_lines[:i+1]
            opportunity = HLSimulator.scan_single_stock(stock['id'], current_data)
            if opportunity:
                opportunities.append(opportunity)
        
        return opportunities

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