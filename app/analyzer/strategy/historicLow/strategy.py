#!/usr/bin/env python3
"""
HistoricLow 策略 - 寻找股票的历史低点，识别可能的买入机会
"""
import math
import time
from typing import Dict, List, Any, Tuple
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
from .strategy_entity import HistoricLowEntity
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

        pprint.pprint(opportunities)

        return opportunities

    def simulate(self) -> None:
        # 延迟导入，避免与 simulator 的循环依赖
        from .strategy_simulator import HLSimulator
        HLSimulator(self).test_strategy()

    def report(self, opportunities: List[Dict[str, Any]]) -> None:
        # todo: present the report
        pass


    # ========================================================
    # Core logic:
    # ========================================================

    @staticmethod
    def scan_single_stock(stock: Dict[str, Any], daily_records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """寻找投资机会"""

        freeze_records, history_records = HistoricLowStrategy.split_daily_data(daily_records)

        low_points = HistoricLowStrategy.find_low_points(history_records)

        opportunity = HistoricLowStrategy.find_opportunity_from_low_points(stock, low_points, freeze_records, history_records)
        # investment = HistoricLowEntity.to_investment(opportunity)

        return opportunity

    @staticmethod
    def split_daily_data(daily_records: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        分割日线数据为冻结期和历史期
        
        Args:
            daily_data: 完整的日线数据列表
            
        Returns:
            freeze_records: 投资冻结期的数据
            history_records: 可以用来寻找机会的日线数据
        """
        # 获取配置参数
        freeze_days = strategy_settings['daily_data_requirements']['freeze_period_days']
        
        # 分割数据
        freeze_records = daily_records[-freeze_days:]  # 最近200个交易日（冻结期）
        history_records = daily_records[:-freeze_days]  # 之前的数据（历史期）

        return freeze_records, history_records


    @staticmethod
    def find_low_points(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        low_points = []
        target_years = strategy_settings['daily_data_requirements']['low_points_ref_years']
        date_of_today = records[-1]['date']
        
        # 解析今天的日期
        from datetime import datetime, timedelta
        today = datetime.strptime(date_of_today, '%Y%m%d')
        
        for years_back in target_years:
            # 计算时间区间的开始日期（往前推years_back年）
            start_date = today - timedelta(days=years_back * 365)
            start_date_str = start_date.strftime('%Y%m%d')
            
            # 找到该时间区间内的所有记录
            period_records = [record for record in records 
                            if record['date'] >= start_date_str and record['date'] < date_of_today]
            
            if not period_records:
                continue
                
            # 找到该时间区间内的最低价格
            min_record = min(period_records, key=lambda x: float(x['close']))
            
            low_points.append(HistoricLowEntity.to_low_point(years_back, min_record))
        
        return low_points

    @staticmethod
    def find_opportunity_from_low_points(stock: Dict[str, Any], low_points: List[Dict[str, Any]], freeze_data: List[Dict[str, Any]], history_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """从历史低点寻找投资机会"""
        record_of_today = freeze_data[-1]

        # 检查当前价格是否在投资范围内
        for low_point in low_points:
            if HistoricLowService.is_in_invest_range(record_of_today, low_point, freeze_data):
                # logger.info(f"股票 {stock['id']} 历史低点 {low_point['date']} 在投资范围内")
                if (HistoricLowService.has_no_new_low_during_freeze(freeze_data)
                    and HistoricLowService.is_amplitude_sufficient(freeze_data)
                    and HistoricLowService.is_slope_sufficient(freeze_data)
                    and HistoricLowService.is_out_of_continuous_limit_down(freeze_data)
                    # and HistoricLowService.is_wave_completed(freeze_data + history_data, low_point)
                ):
                    # logger.info(f"且没有出现新低，且振幅足够，且斜率足够，且不在连续跌停，且波段完成")
                    opportunity = HistoricLowEntity.to_opportunity(stock, record_of_today, low_point)
                    return opportunity

        return None


    # ========================================================
    # Result presentation:
    # ========================================================

    def to_presentable_report(self, opportunities: List[Dict[str, Any]]) -> None:
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
    

    # ========================================================
    # Workers:
    # ========================================================

    def _scan_stocks_with_worker(self, stock_idx: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        opportunities = []
        
        # 使用单线程处理，避免数据库连接冲突
        total_stocks = len(stock_idx)
        logger.info(f"开始扫描 {total_stocks} 只股票...")
        
        start_time = time.time()

        for i, stock in enumerate(stock_idx, 1):
            try:
                # 直接调用原有的扫描方法
                opportunity = self.scan_opportunity_job_for_single_stock(stock)
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

    def scan_opportunity_job_for_single_stock(self, stock: Dict[str, Any]) -> List[Dict[str, Any]]:
        """扫描单只股票的投资机会"""
        daily_k_lines_count = self.required_tables["stock_kline"].count("id = %s AND term = %s", (stock['id'], 'daily'))
        min_required_daily_records = self.strategy_settings['daily_data_requirements']['min_required_daily_records']
        
        if daily_k_lines_count < min_required_daily_records:
            return []

        formatted_daily_records = self.acquire_qfq_daily_records(stock)

        opportunity = self.scan_single_stock(stock, formatted_daily_records)
        
        # 返回列表格式以保持接口兼容性
        if opportunity:
            return [opportunity]
        else:
            return []

    def acquire_qfq_daily_records(self, stock: Dict[str, Any]) -> List[Dict[str, Any]]:
        raw_daily_records = self.required_tables["stock_kline"].get_all_k_lines_by_term(stock['id'], 'daily')
        qfq_factors = self.required_tables["adj_factor"].get_stock_factors(stock['id'])
        qfq_daily_records = DataSourceService.to_qfq(raw_daily_records, qfq_factors)
        daily_records = HistoricLowService.filter_out_negative_records(qfq_daily_records)

        return daily_records