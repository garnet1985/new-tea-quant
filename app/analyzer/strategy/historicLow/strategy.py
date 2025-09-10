#!/usr/bin/env python3
"""
HistoricLow 策略 - 寻找股票的历史低点，识别可能的买入机会
"""
import math
import time
from typing import Dict, List, Any
from datetime import datetime, timedelta
import pprint
from enum import Enum
from loguru import logger
from app.analyzer.strategy.historicLow.strategy_simulator import HLSimulator
from utils.worker import ProcessWorker, ProcessExecutionMode 
from .tables.settings.model import HLMetaModel
from .tables.targets.model import HLOpportunityHistoryModel
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
        description = "历史低价策略: 使用某个周期前的历史最低点作为投资参考点，使用分段止盈来完成盈利"
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
    
    def report(self, opportunities: List[Dict[str, Any]]) -> None:
        self._present_report(opportunities)
    
    def _scan_stocks_with_worker(self, stock_idx: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        opportunities = []
        
        # 使用单线程处理，避免数据库连接冲突
        total_stocks = len(stock_idx)
        logger.info(f"开始扫描 {total_stocks} 只股票...")
        
        start_time = time.time()

        for i, stock in enumerate(stock_idx, 1):
            try:
                # 直接调用原有的扫描方法
                opportunity = self.scan_opportunity_for_single_stock(stock)
                progress = (i / total_stocks * 100)
                if opportunity:
                    opportunities.extend(opportunity)
                    logger.info(f"🔍 扫描股票 {stock['id']} {stock['name']} - ✅ 发现投资机会 {i}/{total_stocks} ({progress:.1f}%)")
                else:
                    logger.info(f"🔍 扫描股票 {stock['id']} {stock['name']} - 没有投资机会 {i}/{total_stocks} ({progress:.1f}%)")
                    
            except Exception as e:
                logger.error(f"扫描股票 {stock['id']} 失败: {e}")
                continue
        
        logger.info(f"✅ 股票扫描完成: 共扫描 {total_stocks} 只股票，发现 {len(opportunities)} 个投资机会, 共耗时 {time.time() - start_time:.2f} 秒")
        return opportunities

    def scan_opportunity_for_single_stock(self, stock: Dict[str, Any]) -> List[Dict[str, Any]]:
        """扫描单只股票的投资机会"""
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
            
    @staticmethod
    def find_opportunity_from_low_points(stock: Dict[str, Any], low_points: List[Dict[str, Any]], freeze_data: List[Dict[str, Any]], history_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """从历史低点寻找投资机会"""
        record_of_today = freeze_data[-1]

        # 检查当前价格是否在投资范围内
        for low_point in low_points:
            # 检查投资范围和新低
            # 1. 检查是否在投资范围内
            # 2. 检查是否不在连续下跌趋势中
            # 3. 检查是否存在连续跌停等无法操作的风险
            # 注意：ST股票已在数据库层面通过load_filtered_index过滤

            if (HistoricLowService.is_in_invest_range(record_of_today, low_point, freeze_data) and 
                not HistoricLowService.is_in_continuous_limit_down(freeze_data) and
                HistoricLowService.is_amplitude_sufficient(freeze_data) and
                HistoricLowService.is_slope_sufficient(freeze_data)):

                # 新增：波段完成过滤（参考低点后是否完成至少一个“谷-峰-回撤”）
                full_series = history_data + freeze_data
                if not HistoricLowService.is_wave_completed(full_series, low_point):
                    continue



            # if (HistoricLowService.is_in_invest_range(record_of_today, low_point, freeze_data) and 
            #     not HistoricLowService.is_in_continuous_downtrend(freeze_data) and
            #     not HistoricLowService.has_limit_down_risk(freeze_data)):

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
                investment = HistoricLowService.to_investment(opportunity, investment_targets, freeze_data)

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
    
    def simulate(self) -> None:
        # 延迟导入，避免与 simulator 的循环依赖
        from .strategy_simulator import HLSimulator
        HLSimulator(self).test_strategy()


    async def scan(self) -> List[Dict[str, Any]]:
        stock_idx = self.required_tables["stock_index"].load_filtered_index()
        
        if not stock_idx:
            return []

        opportunities = self._scan_stocks_with_worker(stock_idx)

        pprint.pprint(opportunities)

        return opportunities