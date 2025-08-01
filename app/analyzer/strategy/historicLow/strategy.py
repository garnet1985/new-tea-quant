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
        """扫描单个股票"""
        # 准备数据
        monthly_data = self.service.get_most_recent_klines(self.required_tables["stock_kline"], stock, 'monthly', self.service.get_max_required_monthly_records())

        if len(monthly_data) < self.service.get_min_required_monthly_records():
            return []

        # 获取最新的日线数据，添加错误处理
        daily_data = self.service.get_most_recent_klines(self.required_tables["stock_kline"], stock, 'daily', 1)
        if not daily_data or len(daily_data) == 0:
            print(f"    ❌ {stock['code']} 没有日线数据")
            return []
        
        latest_daily_record = daily_data[0]

        opportunity = self.scan_single_stock(stock, latest_daily_record, monthly_data)
        
        # 返回列表格式以保持接口兼容性
        if opportunity:
            return [opportunity]
        else:
            return []



    def scan_single_stock(self, stock: Dict[str, Any], latest_daily_record: Dict[str, Any], monthly_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """寻找投资机会"""
        # 寻找最低点记录
        low_points = self.service.find_lowest_records(monthly_data)
        print(f"    🔍 找到 {len(low_points)} 个最低点")
        
        # 从最低点寻找机会
        opportunity = self._find_opportunity_from_low_points(stock, low_points, latest_daily_record)
        
        if opportunity:
            print(f"    📈 {stock['code']} {latest_daily_record['date']} 发现投资机会")
        else:
            print(f"    ❌ {stock['code']} {latest_daily_record['date']} 未发现投资机会")
        
        return opportunity
            
    def _find_opportunity_from_low_points(self, stock: Dict[str, Any], low_points: List[Dict[str, Any]], latest_record: Dict[str, Any]) -> Dict[str, Any]:
        """从最低点寻找投资机会（与JavaScript版本保持一致）"""
        current_price = float(latest_record['close'])
        
        print(f"    💰 当前价格: {current_price}")
        
        # 遍历所有最低点，找到第一个匹配的投资机会（与JavaScript版本一致）
        for low_point in low_points:
            # 检查low_point是否有效
            if low_point is None or low_point['record'] is None:
                print(f"    ⚠️ 扫描周期 {low_point['term'] if low_point else 'unknown'}: 无效的最低点记录，跳过")
                continue
                
            # 检查当前价格是否在投资范围内
            is_in_range = self.service.is_in_invest_range(latest_record, low_point)
            lowest_price = float(low_point['record']['lowest'])
            print(f"    📊 扫描周期 {low_point['term']}: 最低点 {lowest_price}, 在投资范围内: {is_in_range}")
            
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




    # def test_job(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
    #     stock_code = data['stock']['code']
    #     print(f"\n🔍 开始扫描股票 {stock_code}")
    #     print(f"   月度数据: {len(data['monthly_data'])} 条")
    #     print(f"   日度数据: {len(data['daily_data'])} 条")
        
    #     scan_count = 0
    #     invest_count = 0
        
    #     for daily_record in data['daily_data']:
    #         monthly_data = self.service.get_records_before_date(data['monthly_data'], daily_record['date'])
    #         if len(monthly_data) < self.service.get_min_required_monthly_records():
    #             continue
    #         else:
    #             scan_count += 1
    #             result = self.simulate_a_day_for_a_stock(data['stock'], daily_record, monthly_data)
    #             if result:
    #                 invest_count += 1

    #     print(f"   扫描天数: {scan_count}")
    #     print(f"   投资次数: {invest_count}")
    #     print(f"   最终投资状态: {len(self.test_tracker['investing'])} 个")
    #     print(f"   已结算投资: {len(self.test_tracker['settled'])} 个")
        
    #     self.settle_open_investments(data['stock'], data['daily_data'][-1])

    # def simulate_a_day_for_a_stock(self, stock: Dict[str, Any], daily_record: Dict[str, Any], monthly_data: List[Dict[str, Any]]) -> bool:
    #     """测试单个股票"""
    #     # 1. 先检查现有投资是否需要结算
    #     investment = self.service.get_investing(stock, self.test_tracker['investing'])
    #     if investment:
    #         # 检查是否需要结算（止损或止盈）
    #         should_settle = self.settle_investment(stock, investment, daily_record)
    #         # 如果结算了，扫描新机会
    #         if should_settle:
    #             # 投资已结算（在settle_result中已清空投资状态），扫描新机会
    #             opportunity = self.scan_single_stock(stock, daily_record, monthly_data)
    #             if opportunity:
    #                 self.invest(stock, opportunity)
    #                 return True
    #         # 如果没结算，继续持有（不扫描新机会）
    #         return False
    #     else:
    #         # 2. 没有投资，扫描新机会
    #         opportunity = self.scan_single_stock(stock, daily_record, monthly_data)
    #         if opportunity:
    #             self.invest(stock, opportunity)
    #             return True
    #         return False

    # def invest(self, stock: Dict[str, Any], opportunity: Dict[str, Any]) -> None:
    #     # 添加投资开始日期（投资当天的日期）
    #     opportunity['invest_start_date'] = opportunity['opportunity_record']['date']
    #     self.test_tracker['investing'][stock['code']] = opportunity


    # def settle_investment(self, stock: Dict[str, Any], investment: Dict[str, Any], latest_record: Dict[str, Any]) -> bool:
    #     """结算投资，返回是否结算了"""
    #     # 转换数据类型，确保计算一致性
    #     current_close = float(latest_record['close'])
    #     win_price = float(investment['goal']['win'])  # 使用已计算的止盈价格
    #     loss_price = float(investment['goal']['loss'])  # 使用已计算的止损价格
        
    #     if current_close >= win_price:
    #         print(f"🎉 {stock['code']} 投资成功，止盈 {current_close:.2f} (目标: {win_price:.2f})")
    #         self.settle_result(self.result_enum.WIN, stock, investment, latest_record)
    #         return True
    #     elif current_close <= loss_price:
    #         print(f"❌ {stock['code']} 投资失败，止损 {current_close:.2f} (目标: {loss_price:.2f})")
    #         self.settle_result(self.result_enum.LOSS, stock, investment, latest_record)
    #         return True
    #     else:
    #         # print(f'投资中... 当前: {current_close:.2f}, 止盈: {win_price:.2f}, 止损: {loss_price:.2f}')
    #         return False
    
    # def settle_result(self, result: InvestmentResult, stock: Dict[str, Any], investment: Dict[str, Any], latest_record: Dict[str, Any]) -> None:
    #     """结算投资结果"""
    #     invest_duration_days = self.common.get_duration_in_days(investment['invest_start_date'], latest_record['date'])
    #     purchase_price = float(investment['goal']['purchase'])  # 使用已记录的购买价格
    #     profit = float(latest_record['close']) - purchase_price
        
    #     self.test_tracker['settled'][stock['code']] = {
    #         'investment_ref': investment,
    #         'result': {
    #             'result': result.value,
    #             'start_date': investment['opportunity_record']['date'],
    #             'end_date': latest_record['date'],
    #             'profit': profit,
    #             'invest_duration_days': invest_duration_days,
    #             'annual_return': self.common.get_annual_return(
    #                 profit / purchase_price,
    #                 invest_duration_days
    #             )
    #         }
    #     }
    #     self.test_tracker['investing'][stock['code']] = None

    # def settle_open_investments(self, stock: Dict[str, Any], latest_record: Dict[str, Any]) -> None:
    #     """结算所有未结算的投资"""
    #     for stock_code, investment in self.test_tracker['investing'].items():
    #         if investment and stock_code == stock['code']:
    #             self.settle_result(self.result_enum.OPEN, stock, investment, latest_record)




    
