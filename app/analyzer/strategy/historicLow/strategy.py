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
from utils.worker.futures_worker import FuturesWorker
from .tables.meta.model import HLMetaModel
from .tables.opportunity_history.model import HLOpportunityHistoryModel
from .tables.strategy_summary.model import HLStrategySummaryModel
from ...libs.base_strategy import BaseStrategy
from .strategy_service import HistoricLowService
from .strategy_settings import invest_settings
from ...analyzer_service import AnalyzerService
from .strategy_simulator import HLSimulator
from app.data_source.data_source_service import DataSourceService

class HistoricLowStrategy(BaseStrategy):
    """HistoricLow 策略实现"""
    
    # 策略启用状态
    is_enabled = True
    
    def __init__(self, db, is_verbose=False):
        """
        初始化 HistoricLow 策略
        
        Args:
            db: 已初始化的数据库管理器实例
            is_verbose: 是否显示详细日志
        """
        
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
        self.settings = invest_settings

        self.common = AnalyzerService()
        self.service = HistoricLowService()
        self.simulator = HLSimulator(self)


    def initialize(self):
        # this method is automatically called by base strategy class

        self._initialize_tables()
        pass

    def _initialize_tables(self):
        """初始化策略所需的表模型"""
        
        self.required_tables = {
            "stock_index": self.db.get_table_instance("stock_index"),
            "stock_kline": self.db.get_table_instance("stock_kline"),
            "adj_factor": self.db.get_table_instance("adj_factor"),
            "meta": HLMetaModel(self.db),
            "opportunity_history": HLOpportunityHistoryModel(self.db),
            "strategy_summary": HLStrategySummaryModel(self.db)
        }
    
    def scan(self) -> List[Dict[str, Any]]:
        """
        扫描投资机会
        
        Returns:
            List[Dict]: 投资机会列表
        """
        
        # 获取股票列表
        stock_idx = self.required_tables["stock_index"].get_stock_index()
        
        # 测试阶段：只扫描000001和000002
        test_stocks = []
        for stock in stock_idx:
            if stock['id'] in ['000001.SZ', '000002.SZ']:
                test_stocks.append(stock)
        
        stock_idx = test_stocks
        print(f'🧪 测试模式：只扫描 {len(stock_idx)} 只股票: {[s["id"] for s in stock_idx]}')

        if not stock_idx:
            return []

        # 使用多线程扫描
        opportunities = self._scan_stocks_with_worker(stock_idx)
        logger.info(f"🔍 扫描完成，共扫描 {len(stock_idx)} 只股票，发现 {len(opportunities)} 个投资机会")

        return opportunities
    
    def report(self, opportunities: List[Dict[str, Any]]) -> None:
        """
        呈现扫描结果
        
        Args:
            opportunities: 投资机会列表
        """
        self._present_report(opportunities)

    def simulate(self) -> None:
        self.simulator.test_strategy()

    
    def _scan_stocks_with_worker(self, stock_idx: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """使用多线程扫描股票"""
        opportunities = []
        
        # 创建任务
        jobs = []
        for stock in stock_idx:
            job_id = f"scan_{stock['id']}"
            jobs.append({
                'id': job_id,
                'data': stock
            })
        
        # 使用 FuturesWorker 并行处理
        worker = FuturesWorker(
            max_workers=10,
            enable_monitoring=False
        )
        
        # 设置任务执行函数
        worker.set_job_executor(self.scan_job)
        
        # 添加任务
        for job in jobs:
            worker.add_job(job['id'], job['data'])
        
        # 执行任务
        worker.run_jobs()
        
        # 获取结果
        results = worker.get_results()
        
        # 收集结果
        for result in results:
            if result.status.value == 'completed' and result.result:
                opportunities.extend(result.result)
        
        return opportunities
    
    def scan_job(self, stock: Dict[str, Any]) -> List[Dict[str, Any]]:
        # 准备数据
        # 先检查日线记录数是否满足要求
        daily_k_lines_count = self.required_tables["stock_kline"].count("id = %s AND term = %s", (stock['id'], 'daily'))
        min_required_daily_records = invest_settings['daily_data_requirements']['min_required_daily_records']
        
        if daily_k_lines_count < min_required_daily_records:
            return []
        
        # 获取日线数据并应用复权
        daily_data_result = self.required_tables["stock_kline"].get_all_k_lines_by_term(stock['id'], 'daily')
         # 获取复权因子
        qfq_factors = self.required_tables["adj_factor"].get_stock_factors(stock['id'])

        # 应用复权
        daily_records = DataSourceService.to_qfq(daily_data_result, qfq_factors)
        
        # 分割数据为冻结期和历史期
        data_split = self.service.split_daily_data_for_analysis(daily_records)
        freeze_data = data_split['freeze_data']
        history_data = data_split['history_data']
        
        # 在历史数据中寻找历史低点（跳过冻结期）
        low_points = self.service.find_historic_lows(history_data)

        opportunity = self.scan_single_stock(stock, freeze_data, low_points)
        
        # 返回列表格式以保持接口兼容性
        if opportunity:
            return [opportunity]
        else:
            return []



    def scan_single_stock(self, stock: Dict[str, Any], freeze_data: List[Dict[str, Any]], low_points: List[Dict[str, Any]]) -> Dict[str, Any]:
        """寻找投资机会"""
        
        # 1. 趋势过滤：检查股票趋势是否适合投资
        if self.service.is_trend_too_steep(freeze_data):
            return None
        
        # 2. 从历史低点寻找机会
        opportunity = self._find_opportunity_from_low_points(stock, low_points, freeze_data)
        
        return opportunity


            
    def _find_opportunity_from_low_points(self, stock: Dict[str, Any], low_points: List[Dict[str, Any]], freeze_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """从历史低点寻找投资机会"""
        record_of_today = freeze_data[-1]
    
        # 检查当前价格是否在投资范围内
        for low_point in low_points:
            # 检查投资范围和新低
            if (self.service.is_in_invest_range(record_of_today, low_point) and 
                not self.service.has_lower_point_in_latest_daily_records(low_point, freeze_data)):
                # 找到匹配的历史低点，创建投资机会
                # 使用新的动态止损止盈逻辑
                investment_targets = self.service.calculate_investment_targets(record_of_today, low_point)
                
                # 获取之前出现的历史低价点
                previous_low_points = self.service.get_previous_low_points(record_of_today, low_points)
                
                opportunity = {
                    'stock': {
                        'code': stock['id'],
                        'name': stock['name'],
                        'market': DataSourceService.parse_ts_code(stock['id'])[1]
                    },
                    'opportunity_record': record_of_today,
                    'goal': {
                        'loss': investment_targets['stop_loss_price'],
                        'win': investment_targets['take_profit_price'],
                        'purchase': record_of_today['close']
                    },
                    'historic_low_ref': low_point,
                    'investment_targets': investment_targets,  # 保存完整的投资目标信息
                    'previous_low_points': previous_low_points  # 添加之前出现的低价点
                }
                return opportunity
        
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