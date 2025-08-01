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
        
        description = "寻找股票的历史低点，识别可能的买入机会"
        name = "Historic Low"
        prefix = "HL"

        super().__init__(
            db=db,
            is_verbose=is_verbose,
            name=name,
            prefix=prefix,
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

            "meta": HLMetaModel(self.db),
            "opportunity_history": HLOpportunityHistoryModel(self.db),
            "strategy_summary": HLStrategySummaryModel(self.db)
        }
    
    def scan(self) -> List[Dict[str, Any]]:


        # if self.service.should_test():
        if True:
            self.test()

        return []

        """
        扫描投资机会
        
        Returns:
            List[Dict]: 投资机会列表
        """
        
        # 获取股票列表
        stock_idx = self.required_tables["stock_index"].get_stock_index()
        
        # TODO: remove below line
        stock_idx = stock_idx[1195:1197]

        if not stock_idx:
            return []

        # 使用多线程扫描
        opportunities = self._scan_stocks_with_worker(stock_idx)
        logger.info(f"🔍 扫描完成，共扫描 {len(stock_idx)} 只股票，发现 {len(opportunities)} 个投资机会")

        print(opportunities)

        # # print(opportunities)

        # self.report(opportunities)
        
        # # 保存扫描结果
        # if opportunities:
        #     self._save_meta(opportunities)
        
        return opportunities
    
    def report(self, opportunities: List[Dict[str, Any]]) -> None:
        """
        呈现扫描结果
        
        Args:
            opportunities: 投资机会列表
        """
        self._present_report(opportunities)

    
    def _scan_stocks_with_worker(self, stock_idx: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """使用多线程扫描股票"""
        opportunities = []
        
        # 创建任务
        jobs = []
        for stock in stock_idx:
            job_id = f"scan_{stock['code']}"
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

        monthly_data = self.required_tables["stock_kline"].get_all_klines_by_term(stock['code'], 'monthly')

        if(len(monthly_data) < self.service.get_min_required_monthly_records()):
            return []

        # 获取最新的日线数据，添加错误处理
        daily_data = self.required_tables["stock_kline"].get_most_recent_one_by_term(stock['code'], 'daily')

        opportunity = self.scan_single_stock(stock, daily_data, monthly_data)
        
        # 返回列表格式以保持接口兼容性
        if opportunity:
            return [opportunity]
        else:
            return []



    def scan_single_stock(self, stock: Dict[str, Any], latest_daily_record: Dict[str, Any], monthly_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """寻找投资机会"""
        # 寻找最低点记录
        low_points = self.service.find_lowest_records(monthly_data)

        # print(f"    🔍 找到 {len(low_points)} 个最低点")
        
        # 从最低点寻找机会
        opportunity = self._find_opportunity_from_low_points(stock, low_points, latest_daily_record)
        
        # if opportunity:
        #     print(f"    📈 {stock['code']} {latest_daily_record['date']} 发现投资机会")
        # else:
        #     print(f"    ❌ {stock['code']} {latest_daily_record['date']} 未发现投资机会")
        
        return opportunity
            
    def _find_opportunity_from_low_points(self, stock: Dict[str, Any], low_points: List[Dict[str, Any]], latest_record: Dict[str, Any]) -> Dict[str, Any]:
        """从最低点寻找投资机会（与JavaScript版本保持一致）"""
        current_price = float(latest_record['close'])
        
        # 遍历所有最低点，找到第一个匹配的投资机会（与JavaScript版本一致）
        for low_point in low_points:
            # 检查low_point是否有效
            if low_point is None or low_point['record'] is None:
                # print(f"    ⚠️ 扫描周期 {low_point['term'] if low_point else 'unknown'}: 无效的最低点记录，跳过")
                continue
                
            # 检查当前价格是否在投资范围内
            is_in_range = self.service.is_in_invest_range(latest_record, low_point)
            lowest_price = float(low_point['record']['lowest'])
            # print(f"    📊 扫描周期 {low_point['term']}: 最低点 {lowest_price}, 在投资范围内: {is_in_range}")
            
            if is_in_range:
                # 找到第一个匹配的机会就返回（与JavaScript版本一致）
                opportunity = {
                    'meta': {
                        'code': stock['code'],
                        'name': stock['name'],
                        'market': stock['market']
                    },
                    'opportunity_record': latest_record,
                    'goal': {
                        'loss': self.service.set_loss(latest_record),
                        'win': self.service.set_win(latest_record),
                        'purchase': latest_record['close']
                    },
                    'historic_low_ref': {
                        'term': low_point['term'],
                        'ref': low_point
                    } 
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
            print(f"\n{i}. {opp['code']} - {opp['name']}")
            print(f"   当前价格: {opp['close']:.2f}")
            print(f"   历史低点: {opp['low_price']:.2f}")
            print(f"   投资范围: {opp['opportunity_range']}")
            print(f"   止损价格: {opp['loss']:.2f}")
            print(f"   止盈价格: {opp['win']:.2f}")
            print(f"   扫描周期: {', '.join(opp['scan_terms'])}")
            print(f"   扫描日期: {opp['date']}")
    
    def _save_meta(self, opportunities: List[Dict[str, Any]]) -> None:
        """保存扫描结果到元数据表"""
        # 准备元数据
        meta_data = {
            'date': datetime.now().strftime('%Y%m%d'),
            'lastOpportunityUpdateTime': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'lastSuggestedStockCodes': [opp['code'] for opp in opportunities]
        }
        
        # 使用元数据表模型保存
        meta_table = self.required_tables['meta']
        meta_table.update_meta(
            date=meta_data['date'],
            last_opportunity_update_time=meta_data['lastOpportunityUpdateTime'],
            last_suggested_stock_codes=meta_data['lastSuggestedStockCodes']
        )


    def test(self) -> None:
        self.simulator.test_strategy()