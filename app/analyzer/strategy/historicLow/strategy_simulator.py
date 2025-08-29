from typing import Dict, List, Any, Tuple
from datetime import datetime
from loguru import logger
import json
import os
from pprint import pprint


from app.analyzer.analyzer_service import AnalyzerService
from app.analyzer.strategy.historicLow.strategy_service import HistoricLowService
from .strategy_enum import InvestmentResult

from app.data_source.data_source_service import DataSourceService
from app.analyzer.strategy.historicLow.investment_recorder import InvestmentRecorder
from app.analyzer.strategy.historicLow.strategy_settings import strategy_settings

class HLSimulator:
    def __init__(self, strategy):

        self.strategy = strategy

        # init tracker
        self.invest_recorder = InvestmentRecorder()

        # 汇总收集器（单线程汇总，无需锁）
        self.session_results = []
        
        # 股票投资记录存储
        self.stock_investment_records = {}
        
        # 投资记录器初始化标志
        self._investment_recorder_initialized = False
        
        # 是否启用详细日志
        self.is_verbose = True
        


    def test_strategy(self) -> bool:
        stock_idx = self.strategy.required_tables["stock_index"].load_filtered_index()

        # todo: remove below line
        stock_idx = stock_idx[0:2]  # 测试前1只股票

        # 记录测试股票总数
        self.total_stocks_tested = len(stock_idx)

        # 仅准备轻量任务（只包含stock信息，数据在子进程内加载）
        jobs = self.build_jobs(stock_idx)

        results = self.run_jobs(jobs)

        # 创建两层汇总：股票级别和会话级别（统一用service汇总器）
        stock_summaries = {}
        for stock_result in self.session_results:
            summary = HistoricLowService.to_stock_summary(stock_result)
            stock_summaries[summary['stock_id']] = summary
        session_summary = HistoricLowService.to_session_summary(self.session_results)
        
        # 将汇总结果传递给investment_recorder进行记录
        self._record_all_summaries(stock_idx, stock_summaries, session_summary)
        
        # 打印聚合结果
        self.print_aggregated_results()
        
        # 打印投资记录摘要
        self._print_investment_summary()
        
        return True

    def build_jobs(self, stock_idx: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        jobs = []
        for i, stock in enumerate(stock_idx):
            jobs.append({
                'id': f"stock_{i}_{stock['id']}",
                'data': stock
            })
        return jobs

    def run_jobs(self, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        from utils.worker import ProcessWorker, ProcessExecutionMode

        worker = ProcessWorker(
            max_workers=None,
            execution_mode=ProcessExecutionMode.QUEUE,
            job_executor=HLSimulator.simulate_single_stock,
            is_verbose=self.is_verbose
        )

        worker.run_jobs(jobs)

        results = worker.get_results()

        actual_results = []
        for result in results:
            if hasattr(result, 'result') and result.result:
                actual_results.append(result.result)

        return actual_results

    def _record_all_summaries(self, stocks: List[Dict[str, Any]], stock_summaries: Dict[str, Dict[str, Any]], session_summary: Dict[str, Any]):
        """记录所有汇总结果到investment_recorder"""
        # 从session_results中获取每只股票的原始数据
        for stock_result in self.session_results:
            stock = stock_result['stock_info']
            investments = stock_result['investments']
            
            # 转换为investment_recorder期望的格式
            investment_history = []
            for investment in investments.values():
                converted_investment = {
                    'status': investment['result']['result'],
                    'settlement_info': {
                        'profit_loss': investment['result']['profit'],
                        'duration_days': investment['result']['invest_duration_days'],
                        'exit_date': investment['result']['end_date']
                    }
                }
                investment_history.append(converted_investment)
            
            self.invest_recorder.to_record(stock, investment_history)
        
        # 记录会话汇总
        self.invest_recorder._save_session_summary(session_summary)
        
        # 更新meta文件
        self.invest_recorder._update_meta_file()


    # 删除未使用的实例版单股模拟（多进程版本已取代）

    def _settle_stock_investments(self, stock: Dict[str, Any], thread_tracker: Dict[str, Any]) -> Dict[str, Any]:
        """清算单只股票的所有投资"""
        stock_id = stock['id']
        
        # 清算未完成的投资（标记为open）
        if stock_id in thread_tracker['investing']:
            investment = thread_tracker['investing'][stock_id]
            # 使用投资开始日期作为结算日期
            settle_date = investment['invest_start_date']
            
            # 标记为open状态
            investment_id = f"{stock_id}_{investment['invest_start_date']}"
            thread_tracker['settled'][investment_id] = {
                'investment_ref': investment,
                'result': {
                    'result': 'open',
                    'start_date': investment['opportunity_record']['date'],
                    'end_date': settle_date,
                    'profit': 0,
                    'invest_duration_days': 0,
                    'annual_return': 0
                }
            }
            
            # 从investing中删除
            del thread_tracker['investing'][stock_id]
        
        # 返回股票的投资结果
        return {
            'stock_info': stock,
            'investments': thread_tracker['settled']
        }


    def find_opportunity(self, stock: Dict[str, Any], daily_k_lines: List[Dict[str, Any]]) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """查找投资机会（旧版本，保留兼容性）"""
        # 在simulator中重新划分数据，避免重复读取数据库
        freeze_records, history_records = HistoricLowService.split_daily_data_for_analysis(daily_k_lines)
        
        # 在历史数据中寻找历史低点（跳过冻结期）
        low_points = HistoricLowService.find_historic_lows(history_records)
        
        # 调用策略扫描机会，使用划分后的数据
        opportunity = self.strategy.scan_single_stock(stock, freeze_records, low_points)

        return opportunity, low_points

    def invest(self, stock: Dict[str, Any], opportunity: Dict[str, Any], low_points: List[Dict[str, Any]], thread_tracker: Dict[str, Any]) -> None:
        # 检查是否已经在投资
        if stock['id'] in thread_tracker['investing']:
            return
        
        # 添加投资开始日期（投资当天的日期）
        opportunity['invest_start_date'] = opportunity['opportunity_record']['date']
        opportunity['previous_low_points'] = low_points
        
        # 记录到线程自己的tracker
        thread_tracker['investing'][stock['id']] = opportunity


    # def settle_result(self, result: InvestmentResult, stock: Dict[str, Any], investment: Dict[str, Any], latest_record: Dict[str, Any], thread_tracker: Dict[str, Any]) -> None:
    #     """结算投资结果"""
        
    #     logger.info(f"🔍 settle_result: {result.value}")

    #     # 检查投资是否已经被结算过
    #     investment_id = f"{stock['id']}_{investment['invest_start_date']}"
        
    #     # 双重检查，确保在锁内再次验证
    #     if investment_id in thread_tracker['settled']:
    #         return
        
    #     invest_duration_days = AnalyzerService.get_duration_in_days(investment['invest_start_date'], latest_record['date'])
    #     purchase_price = float(investment['goal']['purchase'])  # 使用已记录的购买价格
    #     profit = float(latest_record['close']) - purchase_price
        
    #     # 为每次投资生成唯一标识符，避免同一股票多次投资被覆盖
    #     thread_tracker['settled'][investment_id] = {
    #         'investment_ref': investment,
    #         'result': {
    #             'result': result.value,
    #             'start_date': investment['opportunity_record']['date'],
    #             'end_date': latest_record['date'],
    #             'profit': profit,
    #             'invest_duration_days': invest_duration_days,
    #             'annual_return': AnalyzerService.get_annual_return(
    #                 profit / purchase_price,
    #                 invest_duration_days
    #             )
    #         }
    #     }


    #     print(f"🔍 investment {stock['id']} - {stock['name']} is settled. result: {result.value}")
        
    #     # 删除投资状态，而不是设置为None
    #     if stock['id'] in thread_tracker['investing']:
    #         del thread_tracker['investing'][stock['id']]
    
    
    
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
                    'session_id': os.path.basename(self.invest_recorder.current_session_dir) if self.invest_recorder and self.invest_recorder.current_session_dir else 'unknown',
                    'created_at': datetime.now().isoformat(),
                    'strategy': 'HistoricLow'
                },
                'results': self.stock_investment_records[stock_id],
                'statistics': self._calculate_stock_statistics(stock_id),
                # 添加所有计算出的历史低点信息
                'all_historic_lows': stock_info.get('all_historic_lows', [])
            }
            
            # 保存到文件
            if self.invest_recorder and self.invest_recorder.current_session_dir:
                stock_file_path = os.path.join(self.invest_recorder.current_session_dir, f"{stock_id}.json")
                
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
                logger.error(f"  investment_recorder: {self.invest_recorder}")
                if self.invest_recorder:
                    logger.error(f"  current_session_dir: {self.invest_recorder.current_session_dir}")
            
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
    
    def aggregate_results(self) -> Dict[str, Any]:
        """
        已弃用：请使用 HistoricLowService.to_session_summary(self.session_results)
        """
        return HistoricLowService.to_session_summary(self.session_results)

    def print_aggregated_results(self) -> None:
        """打印聚合的测试结果（使用 HistoricLowService 统一会话汇总）"""
        aggregated = HistoricLowService.to_session_summary(self.session_results)
        
        print("\n" + "="*60)
        print("📊 HistoricLow 策略回测结果汇总")
        print("="*60)
    
    def _print_investment_summary(self) -> None:
        """打印投资记录摘要"""
        # 获取投资结果统计信息（从session_results中获取）
        results_summary = {}
        if hasattr(self, 'session_results') and self.session_results:
            # 使用统一的会话级汇总
            results_summary = HistoricLowService.to_session_summary(self.session_results)
        
        print("\n" + "="*60)
        print(f"🕐 投资记录摘要创建时间: {datetime.now().isoformat()}")
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
            # 更新外层的 total_stocks_tested
            session_update_data = {
                "total_stocks_tested": getattr(self, 'total_stocks_tested', 0)
            }
            
            # 更新会话信息
            self.invest_recorder.update_session_info(session_update_data)
            
            # 追加时间戳并写入统一的会话级统计
            summary_with_ts = dict(results_summary)
            summary_with_ts["summary_generated_at"] = datetime.now().isoformat()
            self.invest_recorder.update_session_summary(summary_with_ts)
            
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
            self.invest_recorder = InvestmentRecorder(base_dir=strategy_tmp_dir)
            self._investment_recorder_initialized = True



    @staticmethod
    def load_qfq_daily(stock_id: str) -> List[Dict[str, Any]]:
        """
        加载指定股票的前复权日线
        """
        from utils.db.db_manager import get_db_manager
        db = get_db_manager()
        kline_model = db.get_table_instance('stock_kline')
        adj_model = db.get_table_instance('adj_factor')
        raw = kline_model.get_all_k_lines_by_term(stock_id, 'daily')
        factors = adj_model.get_stock_factors(stock_id) if hasattr(adj_model, 'get_stock_factors') else []
        return DataSourceService.to_qfq(raw, factors)

    @staticmethod
    def is_daily_data_meet_simulation_requirements(daily_data: List[Dict[str, Any]]) -> bool:
        """
        规则：
        1) 寻找最后一个包含负值价格的记录索引（close/highest/lowest 任一为负）
        2) 取该索引之后的连续片段作为有效序列
        3) 判断该连续片段长度是否满足配置中的最小所需日线数
        """
        if not daily_data:
            return False

        last_negative_idx = -1
        for idx, rec in enumerate(daily_data):
            try:
                close_v = float(rec.get('close', 0))
                high_v = float(rec.get('highest', close_v))
                low_v = float(rec.get('lowest', close_v))
            except Exception:
                # 非法记录按负值处理，推动起点
                last_negative_idx = idx
                continue
            if close_v < 0 or high_v < 0 or low_v < 0:
                last_negative_idx = idx

        # 取连续片段（最后一个负值之后）
        continuous_slice = daily_data[last_negative_idx + 1:] if last_negative_idx + 1 < len(daily_data) else []

        from app.analyzer.strategy.historicLow.strategy_settings import strategy_settings as _settings
        min_required = _settings.get('daily_data_requirements', {}).get('min_required_daily_records', 2000)
        return len(continuous_slice) >= min_required

    # because the python does not share the class instance, we need to use static method to simulate the single stock
    @classmethod
    def simulate_single_stock(cls, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        类方法：独立的模拟函数，可以安全地用于多进程
        不依赖实例状态，避免pickle问题
        """
        # 提取任务数据（仅包含stock信息），其余数据在子进程内加载

        # 在子进程内按需加载复权后的日线
        daily_data = cls.load_qfq_daily(job_data['id'])

        # 使用配置的最小天数
        if not cls.is_daily_data_meet_simulation_requirements(daily_data):
            return {}

        # 本地tracker（仿照实例版）
        tracker: Dict[str, Any] = {
            'investing': {},
            'settled': {}
        }

        # 使用类静态方法，避免函数内嵌定义

        # 累积分发K线，模拟
        current_daily_data: List[Dict[str, Any]] = []
        
        from app.analyzer.strategy.historicLow.strategy_settings import strategy_settings

        min_required_days = strategy_settings.get('daily_data_requirements', {}).get('min_required_daily_records')

        for daily_record in daily_data:
            current_daily_data.append(daily_record)
            if len(current_daily_data) < min_required_days:
                continue
            cls.simulate_one_day(job_data, current_daily_data, tracker)
            
            

        # 清算未结持仓为 open
        if job_data['id'] in tracker['investing']:
            inv = tracker['investing'][job_data['id']]
            inv_id = f"{job_data['id']}_{inv['invest_start_date']}"
            tracker['settled'][inv_id] = {
                'investment_ref': inv,
                'result': {
                    'result': 'open',
                    'start_date': inv['opportunity_record']['date'],
                    'end_date': inv['invest_start_date'],
                    'profit': 0,
                    'invest_duration_days': 0,
                    'annual_return': 0
                }
            }
            del tracker['investing'][job_data['id']]

        return {
            'stock_info': job_data,
            'investments': tracker['settled']
        }

    @staticmethod
    def simulate_one_day(stock: Dict[str, Any], daily_k_lines: List[Dict[str, Any]], tracker: Dict[str, Any]) -> Dict[str, Any]:
        record_of_today = daily_k_lines[-1]

        investing = tracker['investing'].get(stock['id'])

        if investing:
            current_close = float(record_of_today['close'])
            if current_close >= investing['goal']['win']:
                logger.info(f"🔍 settle_result: win - {investing['goal']}")
                HLSimulator.settle_result('win', stock, investing, record_of_today, tracker)
            elif current_close <= investing['goal']['loss']:
                HLSimulator.settle_result('loss', stock, investing, record_of_today, tracker)
            else:
                pass
            # 结算后可继续寻找机会
            if stock['id'] not in tracker['investing']:
                from app.analyzer.strategy.historicLow.strategy import HistoricLowStrategy
                freeze_records, history_records = HistoricLowService.split_daily_data_for_analysis(daily_k_lines)
                low_points = HistoricLowService.find_historic_lows(history_records)
                opp = HistoricLowStrategy.scan_single_stock(stock, freeze_records, low_points)
                if opp:
                    tracker['investing'][stock['id']] = opp
        else:
            from app.analyzer.strategy.historicLow.strategy import HistoricLowStrategy
            freeze_records, history_records = HistoricLowService.split_daily_data_for_analysis(daily_k_lines)
            low_points = HistoricLowService.find_historic_lows(history_records)
            opp = HistoricLowStrategy.scan_single_stock(stock, freeze_records, low_points)
            if opp:
                tracker['investing'][stock['id']] = opp





    @staticmethod
    def settle_result(result_value: str, stock: Dict[str, Any], investment: Dict[str, Any], latest_record: Dict[str, Any], tracker: Dict[str, Any]) -> None:
        """
        写入结算结果到传入的 tracker['settled']
        """

        logger.info(f"🔍 start_date: {investment['invest_start_date']}")
        logger.info(f"🔍 end_date: {latest_record['date']}")

        invest_duration_days = AnalyzerService.get_duration_in_days(investment['invest_start_date'], latest_record['date'])
        logger.info(f"🔍 invest_duration_days: {invest_duration_days}")
        
        
        
        purchase_price = float(investment['goal']['purchase'])
        profit = float(latest_record['close']) - purchase_price


        investment_id = f"{stock['id']}_{investment['invest_start_date']}"


        tracker['settled'][investment_id] = {
            'investment_ref': investment,
            'result': {
                'result': result_value,
                'start_date': investment['opportunity_record']['date'],
                'end_date': latest_record['date'],
                'profit': profit,
                'invest_duration_days': invest_duration_days,
                'annual_return': AnalyzerService.get_annual_return(
                    profit / purchase_price if purchase_price != 0 else 0.0,
                    invest_duration_days
                )
            }
        }


        if stock['id'] in tracker['investing']:
            del tracker['investing'][stock['id']]


    # def settle_investment(self, stock: Dict[str, Any], investment: Dict[str, Any], latest_record: Dict[str, Any], thread_tracker: Dict[str, Any]) -> bool:
    #     """结算投资，返回是否结算了"""
    #     # 检查投资是否已经被结算过
    #     investment_id = f"{stock['id']}_{investment['invest_start_date']}"

    #     if investment_id in thread_tracker['settled']:
    #         return False
        
    #     # 转换数据类型，确保计算一致性
    #     current_close = float(latest_record['close'])
    #     loss_price = investment['goal']['loss']
    #     win_price = investment['goal']['win']
        
    #     if current_close >= win_price:
    #         self.settle_result(self.result_enum.WIN, stock, investment, latest_record, thread_tracker)
    #         self._record_investment_settlement(stock, investment, 'win', current_close, latest_record['date'])
    #         return True
    #     if current_close <= loss_price:
    #         self.settle_result(self.result_enum.LOSS, stock, investment, latest_record, thread_tracker)
    #         self._record_investment_settlement(stock, investment, 'loss', current_close, latest_record['date'])
    #         return True

    #     return False



    # def simulate_one_day_for_one_stock(self, stock: Dict[str, Any], daily_k_lines: List[Dict[str, Any]], thread_tracker: Dict[str, Any]) -> bool:
    #     record_of_today = daily_k_lines[-1]
    #     opportunity = None
        
    #     # 使用线程自己的tracker
    #     investing_opportunity = HistoricLowService.get_investing(stock, thread_tracker['investing'])
        
    #     if investing_opportunity:
    #         # 检查是否需要结算（止损或止盈）
    #         is_settled = self.settle_investment(stock, investing_opportunity, record_of_today, thread_tracker)
    #         if is_settled:
    #             # 投资已结算，看看今天还有机会不
    #             opportunity, low_points = self.find_opportunity(stock, daily_k_lines)
    #     else:
    #         # 没有投资，扫描新机会
    #         opportunity, low_points = self.find_opportunity(stock, daily_k_lines)

    #     # 只有在没有投资且找到机会时才投资
    #     if opportunity and not investing_opportunity:
    #         self.invest(stock, opportunity, low_points, thread_tracker)
    #         return True
        
    #     return False