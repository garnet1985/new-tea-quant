#!/usr/bin/env python3
"""
HistoricLow 策略 - 寻找股票的历史低点，识别可能的买入机会
"""
import math
from typing import Dict, List, Any
from datetime import datetime, timedelta
import pprint
from enum import Enum
from loguru import logger
from app.analyzer.strategy.historicLow.strategy_simulator import HLSimulator
from utils.worker import ProcessWorker, ProcessExecutionMode 
from .tables.meta.model import HLMetaModel
from .tables.opportunity_history.model import HLOpportunityHistoryModel
from .tables.strategy_summary.model import HLStrategySummaryModel
from ...libs.base_strategy import BaseStrategy
from .strategy_service import HistoricLowService
from .strategy_settings import strategy_settings
from app.data_source.data_source_service import DataSourceService

class HistoricLowStrategy(BaseStrategy):
    """HistoricLow 策略实现"""
    
    # 策略启用状态
    is_enabled = True
    
    def __init__(self, db, is_verbose=False):
        description = "从股票的历史价格的低点中寻找历史最低点和历史中波谷多次触及的低点，识别可能的买入机会"
        name = "Historic Low"
        abbreviation = "HL"

        super().__init__(
            db=db,
            is_verbose=is_verbose,
            name=name,
            abbreviation=abbreviation,
            description=description
        )

        
        # 加载策略设置
        self.strategy_settings = strategy_settings


    def initialize(self):
        self._initialize_tables()

    def _initialize_tables(self):
        self.required_tables = {
            "stock_index": self.db.get_table_instance("stock_index"),
            "stock_kline": self.db.get_table_instance("stock_kline"),
            "adj_factor": self.db.get_table_instance("adj_factor"),
            "meta": HLMetaModel(self.db),
            "opportunity_history": HLOpportunityHistoryModel(self.db),
            "strategy_summary": HLStrategySummaryModel(self.db)
        }

    def get_service(self):
        return self.service

    def get_settings(self):
        return self.strategy_settings
    
    def scan(self) -> List[Dict[str, Any]]:
        stock_idx = self.required_tables["stock_index"].load_filtered_index()
        
        if not stock_idx:
            return []

        # 使用多进程扫描
        opportunities = self._scan_stocks_with_worker(stock_idx)

        return opportunities
    
    def report(self, opportunities: List[Dict[str, Any]]) -> None:
        self._present_report(opportunities)
    
    def _scan_stocks_with_worker(self, stock_idx: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        opportunities = []
        
        # 创建任务
        jobs = []
        for stock in stock_idx:
            job_id = f"scan_{stock['id']}"
            jobs.append({
                'id': job_id,
                'data': stock
            })
        
        # 使用 ProcessWorker 多进程处理
        worker = ProcessWorker(
            max_workers=None,  # 自动使用CPU核心数
            execution_mode=ProcessExecutionMode.QUEUE,  # 队列模式，最大化CPU利用率
            job_executor=self.scan_job,
            is_verbose=self.is_verbose
        )
        
        # 执行任务
        stats = worker.run_jobs(jobs)
        
        # 获取结果
        results = worker.get_successful_results()
        
        # 收集结果
        for result in results:
            if result.result:
                opportunities.extend(result.result)
        
        # 打印执行统计
        if self.is_verbose:
            worker.print_stats()
        
        return opportunities
    
    def scan_job(self, stock: Dict[str, Any]) -> List[Dict[str, Any]]:
        daily_k_lines_count = self.required_tables["stock_kline"].count("id = %s AND term = %s", (stock['id'], 'daily'))
        min_required_daily_records = self.strategy_settings['daily_data_requirements']['min_required_daily_records']
        
        if daily_k_lines_count < min_required_daily_records:
            return []
        
        # 获取日线数据并应用复权
        daily_data_result = self.required_tables["stock_kline"].get_all_k_lines_by_term(stock['id'], 'daily')
        # 获取复权因子
        qfq_factors = self.required_tables["adj_factor"].get_stock_factors(stock['id'])

        # 应用复权
        daily_records = DataSourceService.to_qfq(daily_data_result, qfq_factors)

        daily_records = HistoricLowService.filter_out_negative_records(daily_records)

        if not HistoricLowService.is_meet_strategy_requirements(daily_records):
            return []
        
        # 分割数据为冻结期和历史期
        opportunity = self.scan_single_stock(stock, daily_records)
        
        # 返回列表格式以保持接口兼容性
        if opportunity:
            return [opportunity]
        else:
            return []



    @staticmethod
    def scan_single_stock(stock: Dict[str, Any], daily_records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """寻找投资机会"""

        freeze_records, history_records = HistoricLowService.split_daily_data_for_analysis(daily_records)

        low_points = HistoricLowService.find_historic_low_points(history_records)

        investment = HistoricLowStrategy.find_opportunity_from_low_points(stock, low_points, freeze_records, history_records)

        return investment

        if len(daily_records) == 4000:
            pprint.pprint(low_points)
        
        return opportunity
            
    @staticmethod
    def find_opportunity_from_low_points(stock: Dict[str, Any], low_points: List[Dict[str, Any]], freeze_data: List[Dict[str, Any]], history_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """从历史低点寻找投资机会"""
        record_of_today = freeze_data[-1]

        # 检查当前价格是否在投资范围内
        for low_point in low_points:
            # 检查投资范围和新低
            if HistoricLowService.is_in_invest_range(record_of_today, low_point):
                # 找到匹配的历史低点，创建投资机会
                # 使用新的动态止损止盈逻辑
                investment_targets = HistoricLowService.calculate_investment_targets(record_of_today, low_point, freeze_data, history_data)

                if not investment_targets:
                    continue

                # 创建投资机会
                opportunity = HistoricLowService.to_opportunity(
                    stock_info=stock,
                    record_of_today=record_of_today,
                    low_point=low_point
                )

                # 转换为投资对象
                investment = HistoricLowService.to_investment(opportunity, investment_targets)

                return investment
        
        # 没有找到投资机会
        return None
    
    
    def _present_report(self, opportunities: List[Dict[str, Any]]) -> None:
        """呈现扫描报告"""
        if not opportunities:
            print("\n📊 HistoricLow 策略扫描报告")
            print("=" * 50)
            print("❌ 未发现投资机会")
            return
        
        print("\n📊 HistoricLow 策略扫描报告")
        print("=" * 50)
        print(f"🎯 发现 {len(opportunities)} 个投资机会")
        print("=" * 50)
        
        for i, opp in enumerate(opportunities, 1):
            stock_info = opp['stock']
            opportunity_record = opp['opportunity_record']
            goal = opp['goal']
            historic_low = opp['historic_low_ref']
            
            print(f"\n{i}. {stock_info['code']} - {stock_info['name']}")
            print(f"   当前价格: {opportunity_record['close']:.2f}")
            print(f"   历史低点: {historic_low['lowest_price']:.2f}")
            print(f"   止损价格: {goal['loss']:.2f}")
            print(f"   止盈价格: {goal['win']:.2f}")
            print(f"   扫描日期: {opportunity_record['date']}")
    
    def _save_meta(self, opportunities: List[Dict[str, Any]]) -> None:
        """保存扫描结果到元数据表"""
        # 准备元数据
        meta_data = {
            'date': datetime.now().strftime('%Y%m%d'),
            'lastOpportunityUpdateTime': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'lastSuggestedStockCodes': [opp['stock']['code'] for opp in opportunities]
        }
        
        # 使用元数据表模型保存
        meta_table = self.required_tables['meta']
        meta_table.update_meta(
            date=meta_data['date'],
            last_opportunity_update_time=meta_data['lastOpportunityUpdateTime'],
            last_suggested_stock_codes=meta_data['lastSuggestedStockCodes']
        )


    def simulate(self) -> None:
        # 延迟导入，避免与 simulator 的循环依赖
        from .strategy_simulator import HLSimulator
        HLSimulator(self).test_strategy()
