import threading
from typing import Dict, List, Any
from datetime import datetime
from loguru import logger


from app.analyzer.analyzer_service import AnalyzerService
from app.analyzer.strategy.historicLow.strategy_service import HistoricLowService
from app.analyzer.analyzer_service import InvestmentResult
from app.analyzer.strategy.historicLow.strategy_settings import invest_settings

from app.data_source.data_source_service import DataSourceService
from utils.worker.futures_worker import FuturesWorker
from app.analyzer.strategy.historicLow.investment_recorder import InvestmentRecorder

class HLSimulator:
    def __init__(self, strategy):

        self.strategy = strategy

        self.test_tracker = {
            'investing': {},
            'settled': {}
        }
        # 添加线程锁来保护共享数据
        self.tracker_lock = threading.Lock()

        self.settings = invest_settings

        self.result_enum = InvestmentResult

        self.common = AnalyzerService()
        self.service = HistoricLowService()
        
        # 初始化投资记录器，使用策略目录下的tmp文件夹
        import os
        strategy_tmp_dir = os.path.join(os.path.dirname(__file__), "tmp")
        self.investment_recorder = InvestmentRecorder(tmp_dir=strategy_tmp_dir)

    def test_strategy(self) -> bool:
        # 移除investment_recorder相关代码
        # self.investment_recorder.start_new_session()
        
        stock_idx = self.strategy.required_tables["stock_index"].get_stock_index()
        stock_idx = AnalyzerService.to_usable_stock_idx(stock_idx)

        # todo: remove below line
        stock_idx = stock_idx[5:10]  # 测试前20只股票
        # print(f"🎯 测试股票: {stock_idx[0]['code']} - {stock_idx[0]['name']}")

        print(f"🚀 开始处理 {len(stock_idx)} 只股票...")
        
        # 批量预加载数据以提高性能
        jobs = self._prepare_jobs_batch(stock_idx)
        
        print(f"📊 准备处理 {len(jobs)} 个有效任务...")

        worker = FuturesWorker(
            max_workers=invest_settings['simulate']['max_workers'],  # 减少并发数，避免线程竞争
            enable_monitoring=invest_settings['simulate']['enable_monitoring']
        )

        worker.set_job_executor(self.test_job)

        worker.add_jobs(jobs)

        worker.run_jobs()

        # 获取结果并打印聚合统计
        results = worker.get_results()

        # 结算所有未完成的投资
        self.settle_all_open_investments(None)

        # 打印聚合结果
        self.print_aggregated_results(results)
        
        # 打印投资记录摘要
        self._print_investment_summary()
        
        return True

    def _prepare_jobs_batch(self, stock_idx: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        分批准备任务，参考Node.js版本的处理方式
        
        Args:
            stock_idx: 股票列表
            
        Returns:
            List[Dict]: 任务列表
        """
        jobs = []
        
        print("📥 准备任务中...")

        
        # 分批处理，避免数据库连接超时
        batch_size = invest_settings['simulate']['batch_size']  # 每批处理50只股票
        total_batches = (len(stock_idx) + batch_size - 1) // batch_size
        
        for batch_idx in range(total_batches):
            start_idx = batch_idx * batch_size
            end_idx = min(start_idx + batch_size, len(stock_idx))
            batch_stocks = stock_idx[start_idx:end_idx]
            
            print(f"    📊 处理批次 {batch_idx + 1}/{total_batches} (股票 {start_idx + 1}-{end_idx})")
            
            # 为每个股票单独准备数据
            for stock in batch_stocks:
                # 单独查询每个股票的数据，避免大批量查询超时
                qfq_factors = self.strategy.required_tables["adj_factor"].get_stock_factors(stock['id'])
                monthly_data = self.strategy.required_tables["stock_kline"].get_all_k_lines_by_term(stock['id'], 'monthly')
                
                if len(monthly_data) > invest_settings['min_required_monthly_records']:
                    daily_data = self.strategy.required_tables["stock_kline"].get_all_k_lines_by_term(stock['id'], 'daily')
                    
                    if len(daily_data) > 0:
                        jobs.append({
                            'id': f"scan_{stock['id']}",
                            'data': {
                                'stock': stock,
                                'monthly_data': DataSourceService.to_qfq(monthly_data, qfq_factors),
                                'daily_data': DataSourceService.to_qfq(daily_data, qfq_factors)
                            }
                        })

        
        print(f"✅ 任务准备完成，有效任务: {len(jobs)}")
        return jobs

    def test_job(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        
        # 获取日线数据的日期范围
        if not data['daily_data']:
            return []
            
        # 模拟每一天
        for daily_record in data['daily_data']:
            # 使用二分查找获取到当前日期为止的月线数据
            monthly_k_lines = self.service.get_k_lines_before_date(daily_record['date'], data['monthly_data'])
            
            if not self.service.is_reached_min_required_monthly_records(monthly_k_lines):
                continue
            else:
                # 使用二分查找获取到当前日期为止的日线数据
                daily_k_lines = self.service.get_k_lines_before_date(daily_record['date'], data['daily_data'])
                
                self.simulate_one_day_for_one_stock(data['stock'], monthly_k_lines, daily_k_lines)

        # 结算当前股票的未完成投资
        self.settle_open_investments_for_stock(data['stock'], data['daily_data'][-1])


    def simulate_one_day_for_one_stock(self, stock: Dict[str, Any], monthly_k_lines: List[Dict[str, Any]], daily_k_lines: List[Dict[str, Any]]) -> bool:
        """测试单个股票"""
        # 1. 先检查现有投资是否需要结算
        record_of_today = daily_k_lines[-1]
        investment = self.service.get_investing(stock, self.test_tracker['investing'])
        if investment:
            # 检查是否需要结算（止损或止盈）
            is_settled = self.settle_investment(stock, investment, record_of_today)
            # 如果结算了，扫描新机会
            if is_settled:
                # 投资已结算（在settle_result中已清空投资状态），扫描新机会
                self.find_opportunity(stock, monthly_k_lines, daily_k_lines)
            # 如果没结算，继续持有（不扫描新机会）
            return False
        else:
            # 2. 没有投资，扫描新机会
            self.find_opportunity(stock, monthly_k_lines, daily_k_lines)
            return False

    def find_opportunity(self, stock: Dict[str, Any], monthly_k_lines: List[Dict[str, Any]], daily_k_lines: List[Dict[str, Any]]) -> None:
        invest_frozen_window_daily_data = daily_k_lines[-invest_settings['goal']['invest_reference_day_distance_threshold']:]
        opportunity = self.strategy.scan_single_stock(stock, invest_frozen_window_daily_data, monthly_k_lines)
        if opportunity:
            self.invest(stock, opportunity)

    def invest(self, stock: Dict[str, Any], opportunity: Dict[str, Any]) -> None:
        # 添加投资开始日期（投资当天的日期）
        opportunity['invest_start_date'] = opportunity['opportunity_record']['date']
        with self.tracker_lock:
            self.test_tracker['investing'][stock['id']] = opportunity
        
        # 记录投资信息（使用前复权数据）
        try:
            # 获取K线数据（使用前复权数据，与模拟器保持一致）
            daily_data = self.strategy.required_tables["stock_kline"].get_all_k_lines_by_term(stock['id'], 'daily')
            monthly_data = self.strategy.required_tables["stock_kline"].get_all_k_lines_by_term(stock['id'], 'monthly')
            
            # 获取复权因子并转换为前复权数据
            qfq_factors = self.strategy.required_tables["adj_factor"].get_stock_factors(stock['id'])
            qfq_daily_data = DataSourceService.to_qfq(daily_data, qfq_factors)
            qfq_monthly_data = DataSourceService.to_qfq(monthly_data, qfq_factors)
            
            kline_data = {
                'daily': qfq_daily_data,
                'monthly': qfq_monthly_data
            }
            
            # TODO: 使用新的recorder记录投资信息
            # self.investment_recorder.record_investment(opportunity, stock, kline_data)
            
        except Exception as e:
            logger.error(f"❌ 记录投资信息失败: {e}")


    def settle_investment(self, stock: Dict[str, Any], investment: Dict[str, Any], latest_record: Dict[str, Any]) -> bool:
        """结算投资，返回是否结算了"""
        # 转换数据类型，确保计算一致性
        current_close = float(latest_record['close'])
        loss_price = investment['goal']['loss']
        win_price = investment['goal']['win']
        
        if current_close >= win_price:
            print(f"🎉 {stock['id']} {stock['name']} 投资成功，止盈 {current_close:.2f} (目标: {win_price:.2f}) start date: {investment['invest_start_date']} | end date: {latest_record['date']}")
            print(f"start price: {investment['goal']['purchase']}")
            print(f"参考数据: 日期 {investment['historic_low_ref']['record']['date']} 周期 {investment['historic_low_ref']['term']} 最低点 {investment['historic_low_ref']['record']['lowest']}")
            
            # 记录投资结算（成功）
            self._record_investment_settlement(stock, investment, 'win', current_close, latest_record['date'])
            
            self.settle_result(self.result_enum.WIN, stock, investment, latest_record)
            return True
        elif current_close <= loss_price:
            print(f"❌ {stock['id']} {stock['name']} 投资失败，止损 {current_close:.2f} (目标: {loss_price:.2f}) start date: {investment['invest_start_date']} | end date: {latest_record['date']}")
            print(f"start price: {investment['goal']['purchase']}")
            print(f"参考数据: 日期 {investment['historic_low_ref']['record']['date']} 周期 {investment['historic_low_ref']['term']} 最低点 {investment['historic_low_ref']['record']['lowest']}")
            
            # 记录投资结算（失败）
            self._record_investment_settlement(stock, investment, 'loss', current_close, latest_record['date'])
            
            self.settle_result(self.result_enum.LOSS, stock, investment, latest_record)
            return True
        else:
            # print(f'投资中... 当前: {current_close:.2f}, 止盈: {win_price:.2f}, 止损: {loss_price:.2f}')
            return False

    def settle_result(self, result: InvestmentResult, stock: Dict[str, Any], investment: Dict[str, Any], latest_record: Dict[str, Any]) -> None:
        """结算投资结果"""
        invest_duration_days = self.common.get_duration_in_days(investment['invest_start_date'], latest_record['date'])
        purchase_price = float(investment['goal']['purchase'])  # 使用已记录的购买价格
        profit = float(latest_record['close']) - purchase_price
        
        # 为每次投资生成唯一标识符，避免同一股票多次投资被覆盖
        investment_id = f"{stock['id']}_{investment['invest_start_date']}"
        
        with self.tracker_lock:
            self.test_tracker['settled'][investment_id] = {
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
                    # 删除投资状态，而不是设置为None
        if stock['id'] in self.test_tracker['investing']:
            del self.test_tracker['investing'][stock['id']]
    
    
    def settle_open_investments_for_stock(self, stock: Dict[str, Any], latest_record: Dict[str, Any]) -> None:
        """结算特定股票的未结算投资"""
        investment = self.test_tracker['investing'].get(stock['id'])
        if investment:
            self.settle_result(self.result_enum.OPEN, stock, investment, latest_record)

    def settle_all_open_investments(self, latest_date: str) -> None:
        """结算所有未结算的投资（在整个模拟结束后调用）"""
        for stock_code, investment in self.test_tracker['investing'].items():
            if investment:
                # 使用投资开始日期作为结算日期，或者使用传入的最新日期
                settle_date = latest_date or investment['invest_start_date']
                stock_info = {'code': stock_code, 'name': 'Unknown'}
                
                # 记录open状态的投资结算
                self._record_investment_settlement(stock_info, investment, 'open', investment['goal']['purchase'], settle_date)
                
                self.settle_result(self.result_enum.OPEN, stock_info, investment, {'date': settle_date, 'close': investment['goal']['purchase']})
    
    def _record_investment_settlement(self, stock: Dict[str, Any], investment: Dict[str, Any], 
                                    result: str, exit_price: float, exit_date: str) -> None:
        """记录投资结算信息"""
        try:
            # 获取K线数据（使用前复权数据，与模拟器保持一致）
            daily_data = self.strategy.required_tables["stock_kline"].get_all_k_lines_by_term(stock['id'], 'daily')
            monthly_data = self.strategy.required_tables["stock_kline"].get_all_k_lines_by_term(stock['id'], 'monthly')
            
            # 获取复权因子并转换为前复权数据
            qfq_factors = self.strategy.required_tables["adj_factor"].get_stock_factors(stock['id'])
            qfq_daily_data = DataSourceService.to_qfq(daily_data, qfq_factors)
            qfq_monthly_data = DataSourceService.to_qfq(monthly_data, qfq_factors)
            
            kline_data = {
                'daily': qfq_daily_data,
                'monthly': qfq_monthly_data
            }
            
            # 使用新的recorder记录投资结算
            self.investment_recorder.record_investment_settlement(stock, investment, result, exit_price, exit_date, kline_data)
            
        except Exception as e:
            logger.error(f"❌ 记录投资结算失败: {e}")
    
    def aggregate_results(self, results: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        聚合测试结果 - 参照Node.js版本实现
        
        Args:
            results: 测试结果列表（可选，如果不提供则使用内部数据）
            
        Returns:
            Dict[str, Any]: 聚合结果
        """
        if results is None:
            results = []
        
        # 调试信息：查看实际数据结构（简化版）
        print(f"\n🔍 调试信息:")
        print(f"   settled 数据: {len(self.test_tracker['settled'])} 条")
        print(f"   investing 数据: {len(self.test_tracker['investing'])} 条")
        
        # 统计变量 - 参照Node.js的aggregator结构
        aggregator = {
            'total': 0,
            'total_win': 0,
            'total_loss': 0,
            'total_open': 0,
            'total_roi': 0.0,
            'total_duration': 0,
            'total_profit': 0.0,
            'total_investment_amount': 0.0,
            'total_stocks_with_opportunities': 0
        }
        
        # 按股票分组统计
        stock_summaries = {}
        
        # 遍历所有结算的投资
        for investment_id, investment_data in self.test_tracker['settled'].items():
            if investment_data and 'result' in investment_data:
                result = investment_data['result']
                investment_ref = investment_data['investment_ref']
                
                # 调试信息
                # print(f"    🔍 investment_ref: {investment_ref}")
                
                # 安全地获取stock_code
                if 'stock' in investment_ref and isinstance(investment_ref['stock'], dict) and 'code' in investment_ref['stock']:
                    stock_code = investment_ref['stock']['code']
                else:
                    # 从investment_id中提取stock_code
                    stock_code = investment_id.split('_')[0]
                
                # 初始化股票统计
                if stock_code not in stock_summaries:
                    stock_summaries[stock_code] = {
                        'total': 0,
                        'win': 0,
                        'loss': 0,
                        'open': 0,
                        'total_duration': 0,
                        'total_roi': 0.0,
                        'total_profit': 0.0,
                        'total_investment_amount': 0.0
                    }
                
                # 股票级别统计
                stock_summaries[stock_code]['total'] += 1
                stock_summaries[stock_code]['total_duration'] += result['invest_duration_days']
                stock_summaries[stock_code]['total_profit'] += result['profit']
                
                # 获取投资金额
                investment_amount = float(investment_ref['goal']['purchase'])
                stock_summaries[stock_code]['total_investment_amount'] += investment_amount
                
                # 计算ROI（参照Node.js: (exitPrice / enterPrice) - 1）
                exit_price = float(investment_ref['goal']['purchase']) + result['profit']
                enter_price = float(investment_ref['goal']['purchase'])
                roi = (exit_price / enter_price) - 1
                stock_summaries[stock_code]['total_roi'] += roi
                
                # 统计结果类型
                if result['result'] == 'win':
                    stock_summaries[stock_code]['win'] += 1
                elif result['result'] == 'loss':
                    stock_summaries[stock_code]['loss'] += 1
                elif result['result'] == 'open':
                    stock_summaries[stock_code]['open'] += 1
        
        # 汇总所有股票的统计
        for stock_code, stock_summary in stock_summaries.items():
            aggregator['total'] += stock_summary['total']
            aggregator['total_win'] += stock_summary['win']
            aggregator['total_loss'] += stock_summary['loss']
            aggregator['total_open'] += stock_summary['open']
            aggregator['total_duration'] += stock_summary['total_duration']
            aggregator['total_roi'] += stock_summary['total_roi']
            aggregator['total_profit'] += stock_summary['total_profit']
            aggregator['total_investment_amount'] += stock_summary['total_investment_amount']
            aggregator['total_stocks_with_opportunities'] += 1
        
        # 计算平均值和比率
        avg_duration_days = aggregator['total_duration'] / aggregator['total'] if aggregator['total'] > 0 else 0.0
        avg_roi = aggregator['total_roi'] / aggregator['total'] if aggregator['total'] > 0 else 0.0
        
        # 计算胜率（只考虑已结算的投资）
        settled_investments = aggregator['total_win'] + aggregator['total_loss']
        win_rate = (aggregator['total_win'] / settled_investments * 100) if settled_investments > 0 else 0.0
        
        # 计算年化收益率（参照Node.js: (Math.pow(1 + ROI / 100, 365 / days) - 1) * 100）
        # 注意：这里ROI已经是小数形式，不需要除以100
        annual_return = 0.0
        if avg_roi != 0 and avg_duration_days > 0:
            annual_return = ((1 + avg_roi) ** (365 / avg_duration_days) - 1) * 100
        
        # 构建聚合结果
        aggregated_results = {
            'total_investments': aggregator['total'],
            'win_count': aggregator['total_win'],
            'loss_count': aggregator['total_loss'],
            'open_count': aggregator['total_open'],
            'settled_investments': settled_investments,
            'win_rate': round(win_rate, 2),  # 胜率百分比
            'avg_duration_days': round(avg_duration_days, 1),  # 平均投资时长（天）
            'avg_roi': round(avg_roi * 100, 2),  # 平均ROI（百分比）
            'annual_return': round(annual_return, 2),  # 年化收益率（百分比）
            'total_profit': round(aggregator['total_profit'], 2),  # 总利润
            'avg_profit_per_investment': round(aggregator['total_profit'] / aggregator['total'], 2) if aggregator['total'] > 0 else 0.0,
            'total_stocks_with_opportunities': aggregator['total_stocks_with_opportunities']
        }
        
        return aggregated_results

    def print_aggregated_results(self, results: List[Dict[str, Any]] = None) -> None:
        """
        打印聚合的测试结果
        
        Args:
            results: 测试结果列表（可选，如果不提供则使用内部数据）
        """
        aggregated = self.aggregate_results(results)
        
        print("\n" + "="*60)
        print("📊 HistoricLow 策略回测结果汇总")
        print("="*60)
    
    def _print_investment_summary(self) -> None:
        """打印投资记录摘要"""
        summary = self.investment_recorder.get_summary()
        
        print("\n" + "="*60)
        print("📁 投资记录摘要")
        print("="*60)
        print(f"📂 会话目录: {summary.get('session_dir', 'N/A')}")
        print(f"📊 总记录数: {summary.get('total_investment_count', 0)} 条")
        print(f"✅ 成功投资: {summary.get('success_count', 0)} 条")
        print(f"❌ 失败投资: {summary.get('fail_count', 0)} 条")
        print(f"⏳ 未完成投资: {summary.get('open_count', 0)} 条")
        print(f"🕐 创建时间: {summary.get('created_at', 'N/A')}")
        print("="*60)