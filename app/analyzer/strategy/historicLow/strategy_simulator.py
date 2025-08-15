import threading
from typing import Dict, List, Any
from datetime import datetime
from loguru import logger
import json
import os


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
        
        # 延迟初始化投资记录器，避免在__init__时自动创建tmp目录
        self.investment_recorder = None
        self._investment_recorder_initialized = False
        
        # 添加投资记录收集器
        self.stock_investment_records = {}  # 存储每只股票的投资记录

    def _safe_float(self, value, default=0.0):
        """
        安全地将值转换为float类型
        
        Args:
            value: 要转换的值
            default: 默认值，如果转换失败则返回
            
        Returns:
            float: 转换后的值
        """
        if value is None:
            return default
        try:
            return float(value)
        except (ValueError, TypeError):
            return default

    def _init_investment_recorder_if_needed(self):
        """延迟初始化投资记录器，只在需要时才创建"""
        if not self._investment_recorder_initialized:
            import os
            strategy_tmp_dir = os.path.join(os.path.dirname(__file__), "tmp")
            self.investment_recorder = InvestmentRecorder(base_dir=strategy_tmp_dir)
            self._investment_recorder_initialized = True

    def test_strategy(self) -> bool:
        # 延迟初始化投资记录器
        self._init_investment_recorder_if_needed()
        
        stock_idx = self.strategy.required_tables["stock_index"].get_stock_index()
        stock_idx = AnalyzerService.to_usable_stock_idx(stock_idx)

        # todo: remove below line
        stock_idx = stock_idx[0:20]  # 测试前20只股票
        # print(f"🎯 测试股票: {stock_idx[0]['code']} - {stock_idx[0]['name']}")
        
        # 记录测试股票总数
        self.total_stocks_tested = len(stock_idx)

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

            min_required_daily_records = invest_settings['daily_data_requirements']['min_required_daily_records']

            
            # 为每个股票单独准备数据
            for stock in batch_stocks:
                # 单独查询每个股票的数据，避免大批量查询超时
                daily_data = self.strategy.required_tables["stock_kline"].get_all_k_lines_by_term(stock['id'], 'daily')
                
                # 检查是否满足最小日线记录数要求
                if len(daily_data) >= min_required_daily_records:
                    qfq_factors = self.strategy.required_tables["adj_factor"].get_stock_factors(stock['id'])
                    jobs.append({
                        'id': f"scan_{stock['id']}",
                        'data': {
                            'stock': stock,
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
            # 使用二分查找获取到当前日期为止的日线数据
            daily_k_lines = self.service.get_k_lines_before_date(daily_record['date'], data['daily_data'])
            
            # 检查是否满足最小日线记录数要求
            if not self.service.is_reached_min_required_daily_records(daily_k_lines):
                continue
            else:
                self.simulate_one_day_for_one_stock(data['stock'], daily_k_lines)

        # 结算当前股票的未完成投资
        self.settle_open_investments_for_stock(data['stock'], data['daily_data'][-1])
        
        # 保存当前股票的所有投资记录
        stock_id = data['stock']['id']
        if stock_id in self.stock_investment_records:
            self.save_stock_investment_records(stock_id, data['stock'])
            logger.info(f"💾 股票 {stock_id} 模拟完成，已保存投资记录")
        else:
            logger.info(f"📝 股票 {stock_id} 模拟完成，无投资记录")


    def simulate_one_day_for_one_stock(self, stock: Dict[str, Any], daily_k_lines: List[Dict[str, Any]]) -> bool:
        """测试单个股票"""
        # 1. 先检查现有投资是否需要结算
        record_of_today = daily_k_lines[-1]
        investment = self.service.get_investing(stock, self.test_tracker['investing'])
        if investment:
            # 检查是否需要结算（止损或止盈）
            is_settled = self.settle_investment(stock, investment, record_of_today)
            if is_settled:
                # 投资已结算，看看今天还有机会不
                self.find_opportunity(stock, daily_k_lines)
        else:
            # 2. 没有投资，扫描新机会
            self.find_opportunity(stock, daily_k_lines)

    def find_opportunity(self, stock: Dict[str, Any], daily_k_lines: List[Dict[str, Any]]) -> None:
        # 在simulator中重新划分数据，避免重复读取数据库
        data_split = self.service.split_daily_data_for_analysis(daily_k_lines)
        freeze_data = data_split['freeze_data']
        history_data = data_split['history_data']
        
        # 在历史数据中寻找历史低点（跳过冻结期）
        low_points = self.service.find_historic_lows(history_data)
        
        # 调用策略扫描机会，使用划分后的数据
        opportunity = self.strategy.scan_single_stock(stock, freeze_data, low_points)
        if opportunity:
            self.invest(stock, opportunity)

    def invest(self, stock: Dict[str, Any], opportunity: Dict[str, Any]) -> None:
        # 添加投资开始日期（投资当天的日期）
        opportunity['invest_start_date'] = opportunity['opportunity_record']['date']
        with self.tracker_lock:
            self.test_tracker['investing'][stock['id']] = opportunity


    def settle_investment(self, stock: Dict[str, Any], investment: Dict[str, Any], latest_record: Dict[str, Any]) -> bool:
        """结算投资，返回是否结算了"""
        # 转换数据类型，确保计算一致性
        current_close = float(latest_record['close'])
        loss_price = investment['goal']['loss']
        win_price = investment['goal']['win']
        
        if current_close >= win_price:
            print(f"✅ {stock['id']} {stock['name']} 投资成功")
            # print(f"止盈 {current_close:.2f} (目标: {win_price:.2f}) start date: {investment['invest_start_date']} | end date: {latest_record['date']}")
            # print(f"start price: {investment['goal']['purchase']}")
            # print(f"参考数据: 日期 {investment['historic_low_ref']['lowest_date']} 周期 {investment['historic_low_ref']['period_name']} 最低点 {investment['historic_low_ref']['lowest_price']}")
            
            # 记录投资结算（成功）
            self._record_investment_settlement(stock, investment, 'win', current_close, latest_record['date'])
            
            self.settle_result(self.result_enum.WIN, stock, investment, latest_record)
            return True
        elif current_close <= loss_price:
            print(f"❌ {stock['id']} {stock['name']} 投资失败")
            # print(f"止损 {current_close:.2f} (目标: {loss_price:.2f}) start date: {investment['invest_start_date']} | end date: {latest_record['date']}")
            # print(f"start price: {investment['goal']['purchase']}")
            # print(f"参考数据: 日期 {investment['historic_low_ref']['lowest_date']} 周期 {investment['historic_low_ref']['period_name']} 最低点 {investment['historic_low_ref']['lowest_price']}")
            
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
        """
        收集投资结算信息到内存中
        
        Args:
            stock: 股票基本信息
            investment: 投资数据
            result: 投资结果 ('win', 'loss', 'open')
            exit_price: 退出价格
            exit_date: 退出日期
        """
        try:
            stock_id = stock.get('id', 'unknown')
            
            # 计算投资持续天数
            start_date = investment.get('invest_start_date')
            duration_days = None
            if start_date and exit_date:
                try:
                    start_dt = datetime.strptime(start_date, "%Y%m%d")
                    exit_dt = datetime.strptime(exit_date, "%Y%m%d")
                    duration_days = (exit_dt - start_dt).days
                except ValueError:
                    logger.warning(f"⚠️ 日期格式错误，无法计算持续天数: start_date={start_date}, exit_date={exit_date}")
            
            # 准备投资记录
            investment_record = {
                'investment_info': {
                    'start_date': start_date,
                    'purchase_price': self._safe_float(investment.get('goal', {}).get('purchase')),
                    'target_win': self._safe_float(investment.get('goal', {}).get('win')),
                    'target_loss': self._safe_float(investment.get('goal', {}).get('loss')),
                    'historic_low_ref': {
                        'date': investment.get('historic_low_ref', {}).get('lowest_date'),
                        'term': investment.get('historic_low_ref', {}).get('period_name'),
                        'lowest_price': self._safe_float(investment.get('historic_low_ref', {}).get('lowest_price'))
                    }
                },
                'settlement_info': {
                    'result': result,
                    'exit_price': self._safe_float(exit_price) if exit_price else None,
                    'exit_date': exit_date,
                    'duration_days': duration_days,
                    'profit_loss': (self._safe_float(exit_price) - self._safe_float(investment.get('goal', {}).get('purchase'))) if exit_price else None,
                    'profit_loss_rate': ((self._safe_float(exit_price) - self._safe_float(investment.get('goal', {}).get('purchase'))) / self._safe_float(investment.get('goal', {}).get('purchase')) * 100) if exit_price and self._safe_float(investment.get('goal', {}).get('purchase')) != 0 else None,
                    'settled_at': datetime.now().isoformat()
                },
                'status': result
            }
            
            # 收集到内存中
            if stock_id not in self.stock_investment_records:
                self.stock_investment_records[stock_id] = []
            self.stock_investment_records[stock_id].append(investment_record)
            
        except Exception as e:
            logger.error(f"❌ 收集投资记录失败: {e}")

    def save_stock_investment_records(self, stock_id: str, stock_info: Dict[str, Any]):
        """
        保存指定股票的所有投资记录到JSON文件
        
        Args:
            stock_id: 股票ID
            stock_info: 股票基本信息
        """
        if stock_id not in self.stock_investment_records:
            logger.warning(f"股票 {stock_id} 没有投资记录")
            return
        
        try:
            # 延迟初始化投资记录器
            self._init_investment_recorder_if_needed()
            
            # 准备股票数据
            stock_data = {
                'stock_info': {
                    'code': stock_info.get('id', stock_id),
                    'name': stock_info.get('name', ''),
                    'market': stock_info.get('market', ''),
                    'sector': stock_info.get('sector', ''),
                    'industry': stock_info.get('industry', '')
                },
                'session_info': {
                    'session_id': os.path.basename(self.investment_recorder.current_session_dir) if self.investment_recorder and self.investment_recorder.current_session_dir else 'unknown',
                    'created_at': datetime.now().isoformat(),
                    'strategy': 'HistoricLow'
                },
                'results': self.stock_investment_records[stock_id],
                'statistics': self._calculate_stock_statistics(stock_id)
            }
            
            # 保存到文件
            if self.investment_recorder and self.investment_recorder.current_session_dir:
                stock_file_path = os.path.join(self.investment_recorder.current_session_dir, f"{stock_id}.json")
                with open(stock_file_path, 'w', encoding='utf-8') as f:
                    json.dump(stock_data, f, ensure_ascii=False, indent=2)
            else:
                logger.error(f"❌ investment_recorder 未正确初始化或 current_session_dir 为空")
                logger.error(f"  investment_recorder: {self.investment_recorder}")
                if self.investment_recorder:
                    logger.error(f"  current_session_dir: {self.investment_recorder.current_session_dir}")
            
        except Exception as e:
            logger.error(f"❌ 保存股票投资记录失败 {stock_id}: {e}")
            logger.error(f"  错误详情: {str(e)}")
            import traceback
            logger.error(f"  堆栈跟踪: {traceback.format_exc()}")

    def _calculate_stock_statistics(self, stock_id: str) -> Dict[str, Any]:
        """
        计算指定股票的统计信息
        
        Args:
            stock_id: 股票ID
            
        Returns:
            dict: 统计信息
        """
        results = self.stock_investment_records.get(stock_id, [])
        stats = {
            'total_investments': len(results),
            'success_count': len([r for r in results if r['status'] == 'win']),
            'fail_count': len([r for r in results if r['status'] == 'loss']),
            'open_count': len([r for r in results if r['status'] == 'open']),
            'win_rate': 0.0,
            'total_profit': 0.0,
            'avg_profit': 0.0,
            'avg_duration_days': 0.0
        }
        
        if stats['total_investments'] > 0:
            stats['win_rate'] = (stats['success_count'] / stats['total_investments']) * 100
        
        # 计算利润统计
        total_profit = 0.0
        total_duration = 0
        settled_count = 0
        
        for result in results:
            if result['status'] in ['win', 'loss']:
                profit = result['settlement_info'].get('profit_loss', 0)
                total_profit += profit
                duration = result['settlement_info'].get('duration_days', 0)
                total_duration += duration
                settled_count += 1
        
        stats['total_profit'] = total_profit
        if settled_count > 0:
            stats['avg_profit'] = total_profit / settled_count
            stats['avg_duration_days'] = total_duration / settled_count
        
        return stats
    
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
        # 获取文件统计信息
        file_summary = self.investment_recorder.get_summary()
        
        # 获取投资结果统计信息（从test_tracker中获取）
        results_summary = {}
        if hasattr(self, 'test_tracker') and self.test_tracker.get('settled'):
            # 将test_tracker['settled']转换为aggregate_results需要的格式
            settled_results = []
            for investment_id, data in self.test_tracker['settled'].items():
                settled_results.append(data['result'])
            results_summary = self.aggregate_results(settled_results)
        
        print("\n" + "="*60)
        print("📁 投资记录摘要")
        print("="*60)
        print(f"📂 会话目录: {file_summary.get('session_dir', 'N/A')}")
        print(f"📊 总记录数: {file_summary.get('total_investment_count', 0)} 条")
        print(f"✅ 成功投资: {file_summary.get('success_count', 0)} 条")
        print(f"❌ 失败投资: {file_summary.get('fail_count', 0)} 条")
        print(f"⏳ 未完成投资: {file_summary.get('open_count', 0)} 条")
        print(f"🕐 创建时间: {file_summary.get('created_at', 'N/A')}")
        print("="*60)
        
        # 显示投资结果统计
        if results_summary:
            win_rate = results_summary.get('win_rate', 0)
            annual_return = results_summary.get('annual_return', 0)
            
            # 使用绿色点显示胜率（胜率超过60%显示绿色）
            win_rate_dot = "🟢" if win_rate >= 60 else "🔴"
            print(f"🎯 胜率: {win_rate_dot} {win_rate}%")
            
            # 使用绿色点显示年化收益率（年化收益率超过10%显示绿色）
            annual_return_dot = "🟢" if annual_return >= 10 else "🔴"
            print(f"📈 平均年化收益率: {annual_return_dot} {annual_return}%")
            
            print(f"⏱️  平均投资时长: {results_summary.get('avg_duration_days', 0)} 天")
            print(f"💰 平均ROI: {results_summary.get('avg_roi', 0)}%")
            
            # 添加投资数量统计
            print(f"📊 总投资次数: {results_summary.get('total_investments', 0)}")
            print(f"✅ 成功次数: {results_summary.get('win_count', 0)}")
            print(f"❌ 失败次数: {results_summary.get('loss_count', 0)}")
            
            # 将投资摘要写入session_info.json
            self._save_investment_summary_to_session(results_summary)
        else:
            print("📊 投资结果统计: 暂无数据")
        
        print("="*60)

    def _save_investment_summary_to_session(self, results_summary: Dict[str, Any]) -> None:
        """
        将投资摘要信息保存到session_info.json中
        
        Args:
            results_summary: 投资结果摘要
        """
        try:
            # 获取文件统计信息
            file_summary = self.investment_recorder.get_summary()
            
            # 构建完整的摘要数据
            summary_data = {
                # 文件统计信息
                "total_investment_count": file_summary.get('total_investment_count', 0),
                "success_count": file_summary.get('success_count', 0),
                "fail_count": file_summary.get('fail_count', 0),
                "open_count": file_summary.get('open_count', 0),
                
                # 投资结果统计
                "win_rate": results_summary.get('win_rate', 0),
                "annual_return": results_summary.get('annual_return', 0),
                "avg_duration_days": results_summary.get('avg_duration_days', 0),
                "avg_roi": results_summary.get('avg_roi', 0),
                "total_investments": results_summary.get('total_investments', 0),
                "win_count": results_summary.get('win_count', 0),
                "loss_count": results_summary.get('loss_count', 0),
                
                # 额外信息
                "total_profit": results_summary.get('total_profit', 0),
                "avg_profit_per_investment": results_summary.get('avg_profit_per_investment', 0),
                "total_stocks_with_opportunities": results_summary.get('total_stocks_with_opportunities', 0),
                
                # 时间戳
                "summary_generated_at": datetime.now().isoformat()
            }
            
            # 同时更新外层的total_stocks_tested
            session_update_data = {
                "total_stocks_tested": getattr(self, 'total_stocks_tested', 0)
            }
            
            # 更新会话信息
            self.investment_recorder.update_session_info(session_update_data)
            
            # 调用recorder的更新方法
            self.investment_recorder.update_session_summary(summary_data)
            
        except Exception as e:
            logger.error(f"❌ 保存投资摘要到会话失败: {e}")