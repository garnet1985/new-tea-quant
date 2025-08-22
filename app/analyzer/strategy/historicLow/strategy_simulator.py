import threading
from typing import Dict, List, Any, Tuple
from datetime import datetime
from loguru import logger
import json
import os

from app.analyzer.analyzer_service import AnalyzerService
from app.analyzer.strategy.historicLow.strategy_service import HistoricLowService
from app.analyzer.analyzer_service import InvestmentResult

from app.data_source.data_source_service import DataSourceService
from utils.worker.futures_worker import FuturesWorker
from app.analyzer.strategy.historicLow.investment_recorder import InvestmentRecorder

class HLSimulator:
    def __init__(self, strategy):

        # import strategy
        self.strategy = strategy

        # init tracker
        self.invest_recorder = InvestmentRecorder()
        self.tracker = {
            'investing': {},
            'settled': {},
            'all_invests': {}
        }

        self.tracker_lock = threading.Lock()
        # 添加线程锁来保护共享数据
        


    def test_strategy(self) -> bool:
        stock_idx = self.strategy.required_tables["stock_index"].get_stock_index()
        stock_idx = AnalyzerService.to_usable_stock_idx(stock_idx)

        # todo: remove below line
        stock_idx = stock_idx[0:1]  # 测试前1只股票

        # 记录测试股票总数
        self.total_stocks_tested = len(stock_idx)

        # 批量预加载数据以提高性能
        single_stock_jobs = self._prepare_single_stock_jobs_by_batch(stock_idx)

        results = self.run_jobs(single_stock_jobs)

        # 结算所有未完成的投资
        self.settle_all_open_investments(None)

        # 使用新的investment_recorder创建会话汇总
        session_summary = self.invest_recorder.to_session(stock_idx)
        
        # 打印聚合结果
        self.print_aggregated_results(results)
        
        # 打印投资记录摘要
        self._print_investment_summary()
        
        return True

    def run_jobs(self, single_stock_jobs: List[Dict[str, Any]]) -> None:
        
        worker = FuturesWorker(
            max_workers=invest_settings['simulate']['max_workers'],  # 减少并发数，避免线程竞争
            enable_monitoring=invest_settings['simulate']['enable_monitoring']
        )

        worker.set_job_executor(self.simulate_single_stock)

        worker.add_jobs(single_stock_jobs)

        worker.run_jobs()

        results = worker.get_results()
        
        return results


    def _prepare_single_stock_jobs_by_batch(self, stock_idx: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        jobs = []
        
        batch_size = invest_settings['simulate']['batch_size']
        total_batches = (len(stock_idx) + batch_size - 1) // batch_size
        min_required_daily_records = invest_settings.get('daily_data_requirements').get('min_required_daily_records')
        
        for batch_idx in range(total_batches):
            start_idx = batch_idx * batch_size
            end_idx = min(start_idx + batch_size, len(stock_idx))
            batch_stocks = stock_idx[start_idx:end_idx]
            
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
                    
        return jobs

    def simulate_single_stock(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        min_required_days = invest_settings.get('daily_data_requirements').get('min_required_daily_records')
        day_counter = 0;

        for daily_record in data['daily_data']:
            day_counter += 1

            if day_counter < min_required_days:
                continue

            daily_k_lines = self.service.get_k_lines_before_date(daily_record['date'], data['daily_data'])

            self.simulate_one_day_for_one_stock(data['stock'], daily_k_lines)
        
        # 模拟完成后，记录该股票的投资历史
        self._record_stock_investments(data['stock'])
        
        return []


    def simulate_one_day_for_one_stock(self, stock: Dict[str, Any], daily_k_lines: List[Dict[str, Any]]) -> bool:
        record_of_today = daily_k_lines[-1]
        opportunity = None
        investing_opportunity = self.service.get_investing(stock, self.tracker['investing'])
        
        if investing_opportunity:
            # 检查是否需要结算（止损或止盈）
            is_settled = self.settle_investment(stock, investing_opportunity, record_of_today)
            if is_settled:
                # 投资已结算，看看今天还有机会不
                opportunity, low_points = self.find_opportunity(stock, daily_k_lines)
        else:
            # 没有投资，扫描新机会
            opportunity, low_points = self.find_opportunity(stock, daily_k_lines)

        # 只有在没有投资且找到机会时才投资
        if opportunity and not investing_opportunity:
            self.invest(stock, opportunity, low_points)
            return True
        
        return False


    def find_opportunity(self, stock: Dict[str, Any], daily_k_lines: List[Dict[str, Any]]) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """查找投资机会（旧版本，保留兼容性）"""
        # 在simulator中重新划分数据，避免重复读取数据库
        freeze_records, history_records = self.service.split_daily_data_for_analysis(daily_k_lines)
        
        # 在历史数据中寻找历史低点（跳过冻结期）
        low_points = self.service.find_historic_lows(history_records)
        
        # 调用策略扫描机会，使用划分后的数据
        opportunity = self.strategy.scan_single_stock(stock, freeze_records, low_points)

        return opportunity, low_points

    def invest(self, stock: Dict[str, Any], opportunity: Dict[str, Any], low_points: List[Dict[str, Any]]) -> None:
        # 检查是否已经在投资
        with self.tracker_lock:
            if stock['id'] in self.tracker['investing']:
                return
            
            # 添加投资开始日期（投资当天的日期）
            opportunity['invest_start_date'] = opportunity['opportunity_record']['date']
            opportunity['previous_low_points'] = low_points
            
            self.tracker['investing'][stock['id']] = opportunity


    def settle_investment(self, stock: Dict[str, Any], investment: Dict[str, Any], latest_record: Dict[str, Any]) -> bool:
        """结算投资，返回是否结算了"""
        # 检查投资是否已经被结算过
        investment_id = f"{stock['id']}_{investment['invest_start_date']}"
        if investment_id in self.tracker['settled']:
            return False
        
        # 转换数据类型，确保计算一致性
        current_close = float(latest_record['close'])
        loss_price = investment['goal']['loss']
        win_price = investment['goal']['win']
        
        if current_close >= win_price:
            
            self.settle_result(self.result_enum.WIN, stock, investment, latest_record)
            self._record_investment_settlement(stock, investment, 'win', current_close, latest_record['date'])
            return True
        if current_close <= loss_price:
            
            self.settle_result(self.result_enum.LOSS, stock, investment, latest_record)
            self._record_investment_settlement(stock, investment, 'loss', current_close, latest_record['date'])
            return True

        return False

    def settle_result(self, result: InvestmentResult, stock: Dict[str, Any], investment: Dict[str, Any], latest_record: Dict[str, Any]) -> None:
        """结算投资结果"""
        # 检查投资是否已经被结算过
        investment_id = f"{stock['id']}_{investment['invest_start_date']}"
        
        with self.tracker_lock:
            # 双重检查，确保在锁内再次验证
            if investment_id in self.tracker['settled']:
                return
            
            invest_duration_days = self.common.get_duration_in_days(investment['invest_start_date'], latest_record['date'])
            purchase_price = float(investment['goal']['purchase'])  # 使用已记录的购买价格
            profit = float(latest_record['close']) - purchase_price
            
            # 为每次投资生成唯一标识符，避免同一股票多次投资被覆盖
            self.tracker['settled'][investment_id] = {
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
            if stock['id'] in self.tracker['investing']:
                del self.tracker['investing'][stock['id']]
    
    
    def settle_open_investments_for_stock(self, stock: Dict[str, Any], latest_record: Dict[str, Any]) -> None:
        """结算特定股票的未结算投资"""
        investment = self.tracker['investing'].get(stock['id'])
        if investment:
            self.settle_result(self.result_enum.OPEN, stock, investment, latest_record)

    def _precompute_historic_lows(self, daily_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        🚀 性能优化：一次性预计算所有历史低点
        
        Args:
            daily_data: 完整的日线数据
            
        Returns:
            List[Dict]: 预计算的历史低点列表
        """
        if not daily_data or len(daily_data) < 100:
            return []
        
        # 使用所有数据一次性计算历史低点
        all_historic_lows = self.service.find_merged_historic_lows(daily_data)
        
        # 转换为旧格式以保持兼容性
        low_points = []
        for low_point in all_historic_lows:
            low_points.append({
                'record': low_point['record'],
                'period_name': 'merged_historic_low',
                'trading_days': len(daily_data),
                'lowest_price': low_point['price'],
                'lowest_date': low_point['date'],
                'price_range': low_point.get('price_range', {}),
                'conclusion_from': low_point.get('conclusion_from', []),
                'drop_rate': low_point.get('drop_rate', 0),
                'left_peak': low_point.get('left_peak', 0),
                'left_peak_date': low_point.get('left_peak_date', '')
            })
        
        return low_points

    def settle_all_open_investments(self, latest_date: str) -> None:
        """结算所有未结算的投资（在整个模拟结束后调用）"""
        # 创建副本避免在迭代时修改字典
        investing_items = list(self.tracker['investing'].items())
        
        for stock_code, investment in investing_items:
            if investment:
                # 检查投资是否已经被结算过
                investment_id = f"{stock_code}_{investment['invest_start_date']}"
                if investment_id in self.tracker['settled']:
                    continue
                
                # 使用投资开始日期作为结算日期，或者使用传入的最新日期
                settle_date = latest_date or investment['invest_start_date']
                stock_info = {'id': stock_code, 'code': stock_code, 'name': 'Unknown'}
                
                # 记录open状态的投资结算
                self._record_investment_settlement(stock_info, investment, 'open', investment['goal']['purchase'], settle_date)
                
                self.settle_result(self.result_enum.OPEN, stock_info, investment, {'date': settle_date, 'close': investment['goal']['purchase']})
    
    def _record_investment_settlement(self, stock: Dict[str, Any], investment: Dict[str, Any], 
                                result: str, exit_price: float, exit_date: str) -> None:

        # 计算投资持续天数
        start_date = investment.get('invest_start_date')
        duration_days = None
        if start_date and exit_date:
            start_dt = datetime.strptime(start_date, "%Y%m%d")
            exit_dt = datetime.strptime(exit_date, "%Y%m%d")
            duration_days = (exit_dt - start_dt).days
        
            # 准备投资记录
            investment_record = {
                'investment_info': {
                    'start_date': start_date,
                    'purchase_price': self._safe_float(investment.get('goal', {}).get('purchase')),
                    'target_win': self._safe_float(investment.get('goal', {}).get('win')),
                    'target_loss': self._safe_float(investment.get('goal', {}).get('loss')),
                    'selected_low_point': {
                        'date': investment.get('historic_low_ref', {}).get('lowest_date'),
                        'term': investment.get('historic_low_ref', {}).get('period_name'),
                        'lowest_price': self._safe_float(investment.get('historic_low_ref', {}).get('lowest_price'))
                    },
                    # 添加之前出现的历史低价点信息
                    'all_historic_lows': investment.get('previous_low_points', [])
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
        
        stock_id = stock['id']
        # 收集到内存中
        if stock_id not in self.stock_investment_records:
            self.stock_investment_records[stock_id] = []
        self.stock_investment_records[stock_id].append(investment_record)
            


    def save_stock_investment_records(self, stock_id: str, stock_info: Dict[str, Any]):
        """
        保存指定股票的所有投资记录到JSON文件
        
        Args:
            stock_id: 股票ID
            stock_info: 股票基本信息
        """
        if stock_id not in self.stock_investment_records:
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
                'statistics': self._calculate_stock_statistics(stock_id),
                # 添加所有计算出的历史低点信息
                'all_historic_lows': stock_info.get('all_historic_lows', [])
            }
            
            # 保存到文件
            if self.investment_recorder and self.investment_recorder.current_session_dir:
                stock_file_path = os.path.join(self.investment_recorder.current_session_dir, f"{stock_id}.json")
                
                # 转换Decimal类型为float，确保JSON序列化成功
                def convert_decimal(obj):
                    if hasattr(obj, '__float__'):
                        return float(obj)
                    elif isinstance(obj, dict):
                        return {k: convert_decimal(v) for k, v in obj.items()}
                    elif isinstance(obj, list):
                        return [convert_decimal(item) for item in obj]
                    else:
                        return obj
                
                serializable_data = convert_decimal(stock_data)
                
                with open(stock_file_path, 'w', encoding='utf-8') as f:
                    json.dump(serializable_data, f, ensure_ascii=False, indent=2)
            else:
                logger.error(f"  investment_recorder: {self.investment_recorder}")
                if self.investment_recorder:
                    logger.error(f"  current_session_dir: {self.investment_recorder.current_session_dir}")
            
        except Exception as e:
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
        for investment_id, investment_data in self.tracker['settled'].items():
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
        
        # 获取投资结果统计信息（从tracker中获取）
        results_summary = {}
        if hasattr(self, 'tracker') and self.tracker.get('settled'):
            settled_results = []
            for investment_id, data in self.tracker['settled'].items():
                settled_results.append(data['result'])
            results_summary = self.aggregate_results(settled_results)
        
        print("\n" + "="*60)
        print(f"🕐 投资记录摘要创建时间: {file_summary.get('created_at', 'N/A')}")
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

    def _record_stock_investments(self, stock: Dict[str, Any]):
        """记录单只股票的投资历史"""
        stock_id = stock['id']
        
        # 收集该股票的所有投资记录
        investment_history = []
        
        # 从settled中收集已结算的投资
        for investment_id, investment_data in self.tracker['settled'].items():
            if investment_id.startswith(f"{stock_id}_"):
                # 构建投资记录
                investment_record = {
                    'status': investment_data['result']['result'],
                    'settlement_info': {
                        'profit_loss': investment_data['result']['profit'],
                        'duration_days': investment_data['result']['invest_duration_days'],
                        'exit_date': investment_data['result']['end_date']
                    }
                }
                investment_history.append(investment_record)
        
        # 从investing中收集未结算的投资
        if stock_id in self.tracker['investing']:
            investment = self.tracker['investing'][stock_id]
            investment_record = {
                'status': 'open',
                'settlement_info': {
                    'profit_loss': 0,
                    'duration_days': 0,
                    'exit_date': investment['invest_start_date']
                }
            }
            investment_history.append(investment_record)
        
        # 如果有投资记录，调用investment_recorder记录
        if investment_history:
            self.invest_recorder.to_record(stock, investment_history)