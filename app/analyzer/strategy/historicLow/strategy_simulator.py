


import pprint
from typing import Dict, List, Any
from app.analyzer.analyzer_service import AnalyzerService
from app.analyzer.strategy.historicLow.strategy_service import HistoricLowService
from app.analyzer.analyzer_service import InvestmentResult
from app.analyzer.strategy.historicLow.strategy_settings import invest_settings

from utils.worker.futures_worker import FuturesWorker

class HLSimulator:
    def __init__(self, strategy):

        self.strategy = strategy

        self.test_tracker = {
            'investing': {},
            'settled': {}
        }

        self.settings = invest_settings

        self.result_enum = InvestmentResult

        self.common = AnalyzerService()
        self.service = HistoricLowService()

    def test_strategy(self) -> bool:
        stock_idx = self.strategy.required_tables["stock_index"].get_stock_index()

        # todo: remove below line
        stock_idx = stock_idx[1:2]  # 只测试第二只股票 (000002)
        print(f"🎯 测试股票: {stock_idx[0]['code']} - {stock_idx[0]['name']}")

        jobs = []

        for stock in stock_idx:
            monthly_data = self.strategy.required_tables["stock_kline"].get_all_klines_by_term(stock['code'], 'monthly')
            
            if len(monthly_data) > invest_settings['min_required_monthly_records']:
                daily_data = self.strategy.required_tables["stock_kline"].get_all_klines_by_term(stock['code'], 'daily')
                jobs.append({
                    'id': f"scan_{stock['code']}",
                    'data': {
                        'stock': stock,
                        'monthly_data': monthly_data,
                        'daily_data': daily_data
                    }
                })


        worker = FuturesWorker(
            max_workers=10,
            enable_monitoring=False
        )

        worker.set_job_executor(self.test_job)

        worker.add_jobs(jobs)

        worker.run_jobs()

        # results = worker.get_results()r

        # for result in results:
        #     print(result.result)


    def test_job(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        stock_code = data['stock']['code']
        
        for daily_record in data['daily_data']:
            monthly_K_lines = self.service.get_records_before_date(data['monthly_data'], daily_record['date'])

            if not self.service.is_reached_min_required_monthly_records(monthly_K_lines):
                continue
            else:
                # debug code to check if get_records_before_date is correct
                # print(f"date of today: {daily_record['date']}")
                # print(f"{monthly_data[-1]['date']}")
                self.simulate_one_day_for_one_stock(data['stock'], daily_record, monthly_K_lines)

        # 添加错误处理，确保有日线数据才进行结算
        if data['daily_data'] and len(data['daily_data']) > 0:
            self.settle_open_investments(data['stock'], data['daily_data'][-1])
        else:
            print(f"    ❌ CRITICAL ERROR: {stock_code} 没有日线数据，跳过结算")


    def simulate_one_day_for_one_stock(self, stock: Dict[str, Any], record_of_today: Dict[str, Any], monthly_K_lines: List[Dict[str, Any]]) -> bool:
        """测试单个股票"""
        # 1. 先检查现有投资是否需要结算
        investment = self.service.get_investing(stock, self.test_tracker['investing'])
        if investment:
            # 检查是否需要结算（止损或止盈）
            is_settled = self.settle_investment(stock, investment, record_of_today)
            # 如果结算了，扫描新机会
            if is_settled:
                # 投资已结算（在settle_result中已清空投资状态），扫描新机会
                self.find_opportunity(stock, record_of_today, monthly_K_lines)
            # 如果没结算，继续持有（不扫描新机会）
            return False
        else:
            # 2. 没有投资，扫描新机会
            self.find_opportunity(stock, record_of_today, monthly_K_lines)
            return False

    def find_opportunity(self, stock: Dict[str, Any], record_of_today: Dict[str, Any], monthly_K_lines: List[Dict[str, Any]]) -> None:
        opportunity = self.strategy.scan_single_stock(stock, record_of_today, monthly_K_lines)
        if opportunity:
            self.invest(stock, opportunity)

    def invest(self, stock: Dict[str, Any], opportunity: Dict[str, Any]) -> None:
        # 添加投资开始日期（投资当天的日期）
        opportunity['invest_start_date'] = opportunity['opportunity_record']['date']
        self.test_tracker['investing'][stock['code']] = opportunity


    def settle_investment(self, stock: Dict[str, Any], investment: Dict[str, Any], latest_record: Dict[str, Any]) -> bool:
        """结算投资，返回是否结算了"""
        # 转换数据类型，确保计算一致性
        current_close = float(latest_record['close'])
        loss_price = investment['goal']['loss']
        win_price = investment['goal']['win']
        
        if current_close >= win_price:
            print(f"🎉 {stock['code']} 投资成功，止盈 {current_close:.2f} (目标: {win_price:.2f}) start date: {investment['invest_start_date']} | end date: {latest_record['date']}")
            self.settle_result(self.result_enum.WIN, stock, investment, latest_record)
            return True
        elif current_close <= loss_price:
            print(f"❌ {stock['code']} 投资失败，止损 {current_close:.2f} (目标: {loss_price:.2f}) start date: {investment['invest_start_date']} | end date: {latest_record['date']}")
            self.settle_result(self.result_enum.LOSS, stock, investment, latest_record)
            print(f"参考数据: 日期 {investment['historic_low_ref']['record']['date']} 期数 {investment['historic_low_ref']['term']} 最低点 {investment['historic_low_ref']['record']['lowest']}")
            return True
        else:
            # print(f'投资中... 当前: {current_close:.2f}, 止盈: {win_price:.2f}, 止损: {loss_price:.2f}')
            return False

    def settle_result(self, result: InvestmentResult, stock: Dict[str, Any], investment: Dict[str, Any], latest_record: Dict[str, Any]) -> None:
        """结算投资结果"""
        invest_duration_days = self.common.get_duration_in_days(investment['invest_start_date'], latest_record['date'])
        purchase_price = float(investment['goal']['purchase'])  # 使用已记录的购买价格
        profit = float(latest_record['close']) - purchase_price
        
        self.test_tracker['settled'][stock['code']] = {
            'investment_ref': investment,
            'result': {
                'result': result.value,
                'start_date': investment['opportunity_record']['date'],
                'end_date': latest_record['date'],
                'profit': profit,
                'invest_duration_days': invest_duration_days,
                'annual_return': self.common.get_annual_return(
                    profit / purchase_price,
                    invest_duration_days
                )
            }
        }
        self.test_tracker['investing'][stock['code']] = None

    def settle_open_investments(self, stock: Dict[str, Any], latest_record: Dict[str, Any]) -> None:
        """结算所有未结算的投资"""
        for stock_code, investment in self.test_tracker['investing'].items():
            if investment and stock_code == stock['code']:
                self.settle_result(self.result_enum.OPEN, stock, investment, latest_record)
