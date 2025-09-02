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
        
        # 是否启用详细日志
        self.is_verbose = False
        

    def test_strategy(self) -> bool:
        # 验证策略配置
        is_valid, validation_errors = HistoricLowService.validate_strategy_settings(strategy_settings)
        if not is_valid:
            logger.error("❌ 策略配置验证失败:")
            for error in validation_errors:
                logger.error(f"  - {error}")
            raise ValueError("策略配置无效，请检查上述错误")
        logger.info("✅ 策略配置验证通过")
        
        stock_idx = self.strategy.required_tables["stock_index"].load_filtered_index()

        # todo: remove below line
        stock_idx = stock_idx[0:10]  # 测试前2只股票

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
                'id': stock['id'],  # 直接使用股票ID
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
            if result.status.value == 'completed' and result.result:
                actual_results.append(result.result)
            elif result.status.value == 'failed':
                logger.error(f"❌ 任务 {result.job_id} 执行失败: {result.error}")

        # 保存结果到session_results
        self.session_results = actual_results

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
                    'start_date': investment['result']['start_date'],
                    'end_date': investment['result']['end_date'],
                    'ref': {
                        'lowest_price': investment['investment_ref'].get('historic_low_ref', {}).get('lowest_price'),
                        'lowest_date': investment['investment_ref'].get('historic_low_ref', {}).get('lowest_date'),
                        'conclusion_from': investment['investment_ref'].get('historic_low_ref', {}).get('conclusion_from', [])
                    },
                    'target': {
                        'purchase_price': investment['investment_ref']['goal']['purchase'],
                        'win_price': investment['investment_ref']['goal']['win'],
                        'loss_price': investment['investment_ref']['goal']['loss'],
                        'stop_win_rate': investment['result'].get('win_percentage', 0),
                        'stop_loss_rate': investment['result'].get('loss_percentage', 0),
                        # 新增：持有期间的峰值/谷值收益率
                        'max_close_rate': investment['result'].get('max_close_rate'),
                        'min_close_rate': investment['result'].get('min_close_rate')
                    },
                    'settlement_info': {
                        'profit_loss': investment['result']['profit'],
                        'duration_days': investment['result']['invest_duration_days'],
                        'exit_date': investment['result']['end_date'],
                        'annual_return': investment['result'].get('annual_return', 0),
                        # 新增：持有期间的峰值/谷值信息
                        'max_close': investment['result'].get('max_close'),
                        'max_close_date': investment['result'].get('max_close_date'),
                        'max_close_rate': investment['result'].get('max_close_rate'),
                        'min_close': investment['result'].get('min_close'),
                        'min_close_date': investment['result'].get('min_close_date'),
                        'min_close_rate': investment['result'].get('min_close_rate')
                    },
                    # 新增：freeze data统计信息
                    'freeze_data_stats': investment['investment_ref'].get('freeze_data_stats', {}),
                    # 新增：分段平仓信息
                    'staged_exit': investment['result'].get('staged_exit', {})
                }
                investment_history.append(converted_investment)
            
            # 只有当股票有投资记录时才生成文件
            if investment_history:
                self.invest_recorder.to_record(stock, investment_history)
        
        # 记录会话汇总
        self.invest_recorder._save_session_summary(session_summary)
        
        # 更新meta文件
        self.invest_recorder._update_meta_file()


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
            # 计算止损和止盈百分比
            purchase_price = investment['goal']['purchase']
            loss_price = investment['goal']['loss']
            win_price = investment['goal']['win']
            loss_percentage = ((loss_price - purchase_price) / purchase_price * 100) if purchase_price != 0 else 0.0
            win_percentage = ((win_price - purchase_price) / purchase_price * 100) if purchase_price != 0 else 0.0
            
            # 构建open状态结算信息
            open_settlement_result = {
                'result': 'open',
                'start_date': investment['opportunity_record']['date'],
                'end_date': settle_date,
                'profit': 0,
                'invest_duration_days': 0,
                'loss_percentage': round(loss_percentage, 2),
                'win_percentage': round(win_percentage, 2),
                'annual_return': 0
            }
            
            thread_tracker['settled'][investment_id] = {
                'investment_ref': investment,
                'result': open_settlement_result
            }
            
            # 通过investment_recorder生成统一格式的结算信息
            try:
                investment_recorder = InvestmentRecorder()
                settlement_record = investment_recorder.to_settlement(stock, open_settlement_result)
                # 将结算记录添加到settled中，保持原有格式
                thread_tracker['settled'][investment_id]['settlement_record'] = settlement_record
            except Exception as e:
                logger.error(f"🔍 生成open状态结算信息失败: {e}")
            
            # 从investing中删除
            del thread_tracker['investing'][stock_id]
        
        # 返回股票的投资结果
        return {
            'stock_info': stock,
            'investments': thread_tracker['settled']
        }


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
            # 追加时间戳并写入统一的会话级统计
            summary_with_ts = dict(results_summary)
            summary_with_ts["summary_generated_at"] = datetime.now().isoformat()
            self.invest_recorder.update_session_summary(summary_with_ts)
            
        except Exception as e:
            logger.error(f"❌ 保存投资摘要到会话失败: {e}")


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

    # because the python does not share the class instance, we need to use static method to simulate the single stock
    @classmethod
    def simulate_single_stock(cls, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        类方法：独立的模拟函数，可以安全地用于多进程
        不依赖实例状态，避免pickle问题
        """

        # 在子进程内按需加载复权后的日线
        daily_data = cls.load_qfq_daily(job_data['id'])

        # 过滤负值记录
        daily_data = HistoricLowService.filter_out_negative_records(daily_data)

        # 检查是否满足策略要求
        is_valid = HistoricLowService.is_meet_strategy_requirements(daily_data)
        
        if not is_valid:
            return {
                'stock_info': job_data,
                'investments': {}
            }


        # 本地tracker（仿照实例版）
        tracker: Dict[str, Any] = {
            'investing': {},
            'settled': {}
        }


        # 累积分发K线，模拟
        current_daily_data: List[Dict[str, Any]] = []

        min_required_days = strategy_settings.get('daily_data_requirements', {}).get('min_required_daily_records')
        

        for daily_record in daily_data:
            current_daily_data.append(daily_record)
            if len(current_daily_data) < min_required_days:
                continue
            
            # 模拟每日交易
            cls.simulate_one_day(job_data, current_daily_data, tracker)
            
        # 清算未结持仓为 open（重用settle_result方法）
        if job_data['id'] in tracker['investing']:
            inv = tracker['investing'][job_data['id']]
            # 使用最后一天的记录作为结算记录
            last_record = daily_data[-1] if daily_data else None
            if last_record:
                cls.settle_result('open', job_data, inv, last_record, tracker)
        
        return {
            'stock_info': job_data,
            'investments': tracker['settled']
        }

    @staticmethod
    def simulate_one_day(stock: Dict[str, Any], daily_k_lines: List[Dict[str, Any]], tracker: Dict[str, Any]) -> None:
        record_of_today = daily_k_lines[-1]

        investing_opportunity = tracker['investing'].get(stock['id'])

        if investing_opportunity:
            current_close = record_of_today['close']
            current_date = record_of_today['date']
            
            # 更新持有期间的最高/最低价
            if current_close > investing_opportunity['period_max_close']:
                investing_opportunity['period_max_close'] = current_close
                investing_opportunity['period_max_close_date'] = current_date
            if current_close < investing_opportunity['period_min_close']:
                investing_opportunity['period_min_close'] = current_close
                investing_opportunity['period_min_close_date'] = current_date
            
            # 新增：分段平仓逻辑
            if investing_opportunity.get('staged_exit', {}).get('enabled', False):
                HLSimulator.process_staged_exit(stock, investing_opportunity, record_of_today, tracker)
            
            # 检查是否触发止损或止盈
            if current_close >= investing_opportunity['goal']['win']:
                HLSimulator.settle_result('win', stock, investing_opportunity, record_of_today, tracker)
            elif current_close <= investing_opportunity['goal']['loss']:
                HLSimulator.settle_result('loss', stock, investing_opportunity, record_of_today, tracker)
            else:
                pass
            # 结算后可继续寻找机会
            if stock['id'] not in tracker['investing']:
                from app.analyzer.strategy.historicLow.strategy import HistoricLowStrategy
                opp = HistoricLowStrategy.scan_single_stock(stock, daily_k_lines)
                if opp:
                    tracker['investing'][stock['id']] = opp
                    logger.info(f"🎯 {stock['id']} 找到投资机会: {record_of_today['date']}")
        else:
            from app.analyzer.strategy.historicLow.strategy import HistoricLowStrategy
            opp = HistoricLowStrategy.scan_single_stock(stock, daily_k_lines)
            if opp:
                tracker['investing'][stock['id']] = opp
                logger.info(f"🎯 {stock['id']} 找到投资机会: {record_of_today['date']}")




    @staticmethod
    def settle_result(result_value: str, stock: Dict[str, Any], opportunity: Dict[str, Any], record_of_today: Dict[str, Any], tracker: Dict[str, Any]) -> None:
        try:

            start_date = opportunity['invest_start_date']
            end_date = record_of_today['date']

            invest_duration_days = AnalyzerService.get_duration_in_days(start_date, end_date)
            
            # 计算综合收益（已实现收益 + 未实现收益）
            purchase_price = opportunity['goal']['purchase']
            current_close = record_of_today['close']
            staged_exit = opportunity.get('staged_exit', {})
            total_realized_profit = staged_exit.get('total_realized_profit', 0.0)
            remaining_position_ratio = staged_exit.get('current_position_ratio', 1.0)
            
            # 确保剩余仓位不为负数
            remaining_position_ratio = max(0.0, remaining_position_ratio)
            
            # 调试信息
            logger.info(f"🔍 {stock['id']} 结算时剩余仓位: {remaining_position_ratio:.2f}, 已实现收益: {total_realized_profit:.4f}")
            
            # 未实现收益 = 剩余持仓 * (当前价格 - 买入价格)
            unrealized_profit = remaining_position_ratio * (current_close - purchase_price)
            total_profit = total_realized_profit + unrealized_profit
            
            # 基于综合收益判断胜负
            if total_profit > 0:
                actual_result = 'win'
            else:
                actual_result = 'loss'
            
            # 计算综合收益率
            total_profit_rate = total_profit / purchase_price if purchase_price != 0 else 0.0
            total_realized_profit_rate = total_realized_profit / purchase_price if purchase_price != 0 else 0.0

            investment_id = f"{stock['id']}_{start_date}"


            # 计算止损和止盈百分比
            loss_price = opportunity['goal']['loss']
            win_price = opportunity['goal']['win']
            loss_percentage = ((loss_price - purchase_price) / purchase_price * 100) if purchase_price != 0 else 0.0
            win_percentage = ((win_price - purchase_price) / purchase_price * 100) if purchase_price != 0 else 0.0
            
            # 计算期间最高/最低价的收益率
            period_max_close = opportunity.get('period_max_close', purchase_price)
            period_min_close = opportunity.get('period_min_close', purchase_price)
            period_max_close_date = opportunity.get('period_max_close_date', start_date)
            period_min_close_date = opportunity.get('period_min_close_date', start_date)
            
            max_close_rate = ((period_max_close / purchase_price) - 1.0) if purchase_price != 0 else 0.0
            min_close_rate = ((period_min_close / purchase_price) - 1.0) if purchase_price != 0 else 0.0
            
            # 构建结算信息
            settlement_result = {
                'result': actual_result,  # 使用基于综合收益判断的结果
                'start_date': opportunity['opportunity_record']['date'],
                'end_date': end_date,
                'profit': total_profit,  # 使用综合收益
                'invest_duration_days': invest_duration_days,
                'loss_percentage': round(loss_percentage, 2),
                'win_percentage': round(win_percentage, 2),
                'annual_return': AnalyzerService.get_annual_return(
                    total_profit_rate,  # 使用综合收益率
                    invest_duration_days
                ),
                # 新增：持有期间的峰值/谷值信息
                'max_close': period_max_close,
                'max_close_date': period_max_close_date,
                'max_close_rate': round(max_close_rate, 6),
                'min_close': period_min_close,
                'min_close_date': period_min_close_date,
                'min_close_rate': round(min_close_rate, 6),
                # 新增：分段平仓信息
                'total_realized_profit': total_realized_profit,
                'total_realized_profit_rate': round(total_realized_profit_rate, 6),
                'unrealized_profit': unrealized_profit,
                'remaining_position_ratio': remaining_position_ratio,
                # 新增：完整的分段平仓信息
                'staged_exit': staged_exit,
                'ref': opportunity.get('ref', {}),
                'target': opportunity.get('goal', {}),
                'freeze_data_stats': opportunity.get('freeze_data_stats', {})
            }
            
            tracker['settled'][investment_id] = {
                'investment_ref': opportunity,
                'result': settlement_result
            }

            if stock['id'] in tracker['investing']:
                del tracker['investing'][stock['id']]
                
            if actual_result.upper() == "WIN":
                result_dot = "🟢"
            elif actual_result.upper() == "LOSS":
                result_dot = "🔴"
            else:  # OPEN
                result_dot = "🟡"
            logger.info(f" {result_dot} {stock['id']} investment {actual_result} (综合收益{total_profit:.4f}, 已实现{total_realized_profit:.4f}), duration: {invest_duration_days} days")
            
            # 生成统一格式的投资结算信息
            try:
                settlement_record = InvestmentRecorder().to_settlement(stock, settlement_result)
                # 将结算记录添加到settled中，保持原有格式
                tracker['settled'][investment_id]['settlement_record'] = settlement_record
            except Exception as e:
                logger.error(f"🔍 生成投资结算信息失败: {e}")
            
        except Exception as e:
            logger.error(f"🔍 settle_result 方法执行出错: {e}")
            import traceback
            logger.error(f"🔍 错误详情: {traceback.format_exc()}")
    
    @staticmethod
    def process_staged_exit(stock: Dict[str, Any], investment: Dict[str, Any], record_of_today: Dict[str, Any], tracker: Dict[str, Any]) -> None:
        """
        处理分段平仓逻辑
        """
        current_close = float(record_of_today['close'])
        purchase_price = float(investment['goal']['purchase'])
        current_profit_rate = (current_close - purchase_price) / purchase_price
        
        staged_exit = investment.get('staged_exit', {})
        exited_stages = staged_exit.get('exited_stages', [])
        
        # 获取分段平仓配置
        staged_config = strategy_settings.get('staged_exit_strategy', {})
        if not staged_config.get('enabled', False):
            return
        
        stages = staged_config.get('stages', [])
        
        # 检查是否已经启动动态止损
        if staged_exit.get('dynamic_trailing_enabled', False):
            # 如果已经启动动态止损，只更新动态止损价格
            HLSimulator.update_trailing_stop(stock, investment, record_of_today)
            return
        
        # 按顺序检查每个阶段
        for i, stage in enumerate(stages):
            profit_rate = stage.get('profit_rate', 0)
            action = stage.get('action', '')
            stage_key = f"{profit_rate:.2f}"
            
            # 检查是否已经执行过这个阶段
            if stage_key in exited_stages:
                continue
            
            # 检查是否达到这个阶段的触发条件
            if current_profit_rate >= profit_rate:
                # 执行当前阶段动作
                HLSimulator.execute_stage_action(stock, investment, stage, record_of_today, tracker)
                exited_stages.append(stage_key)
                staged_exit['exited_stages'] = exited_stages
                
                # 如果是最后一个阶段，启动动态止损
                if i == len(stages) - 1:
                    HLSimulator.start_dynamic_trailing_stop(stock, investment, stage, record_of_today)
                    staged_exit['dynamic_trailing_enabled'] = True
                # 移除20%启动动态止损，改为40%启动
                # elif profit_rate == 0.2:
                #     HLSimulator.start_dynamic_trailing_stop(stock, investment, stage, record_of_today)
                #     staged_exit['dynamic_trailing_enabled'] = True
                # 移除break，允许继续检查下一个阶段
                # break
    
    @staticmethod
    def start_dynamic_trailing_stop(stock: Dict[str, Any], investment: Dict[str, Any], stage: Dict[str, Any], record_of_today: Dict[str, Any]) -> None:
        """
        启动动态止损
        """
        action = stage.get('action', '')
        profit_rate = stage.get('profit_rate', 0)
        current_close = float(record_of_today['close'])
        purchase_price = float(investment['goal']['purchase'])
        
        # 获取动态止损配置
        staged_config = strategy_settings.get('staged_exit_strategy', {})
        stages = staged_config.get('stages', [])
        last_stage = stages[-1] if stages else {}
        trailing_stop_ratio = last_stage.get('trailing_stop_ratio', 0.10)  # 改为10%，按照用户逻辑
        
        staged_exit = investment.get('staged_exit', {})
        
        # 设置动态止损价格
        trailing_stop_price = current_close * (1 - trailing_stop_ratio)
        staged_exit['trailing_stop_price'] = trailing_stop_price
        staged_exit['last_close_price'] = current_close
        
        # 更新止损价格
        investment['goal']['loss'] = trailing_stop_price
        
        logger.info(f"🎯 {stock['id']} 涨幅{profit_rate*100:.0f}%: 启动动态止损，止损价格{trailing_stop_price:.4f}")
    
    @staticmethod
    def update_trailing_stop(stock: Dict[str, Any], investment: Dict[str, Any], record_of_today: Dict[str, Any]) -> None:
        """
        更新动态止损价格
        """
        current_close = float(record_of_today['close'])
        staged_exit = investment.get('staged_exit', {})
        last_close_price = staged_exit.get('last_close_price', current_close)
        trailing_stop_price = staged_exit.get('trailing_stop_price', current_close)
        
        # 如果当前价格更高，更新动态止损价格
        if current_close > last_close_price:
            # 获取动态止损配置
            staged_config = strategy_settings.get('staged_exit_strategy', {})
            stages = staged_config.get('stages', [])
            last_stage = stages[-1] if stages else {}
            trailing_stop_ratio = last_stage.get('trailing_stop_ratio', 0.10)  # 改为10%，按照用户逻辑
            
            new_trailing_stop_price = current_close * (1 - trailing_stop_ratio)
            
            # 只有当新的止损价格更高时才更新
            if new_trailing_stop_price > trailing_stop_price:
                staged_exit['trailing_stop_price'] = new_trailing_stop_price
                staged_exit['last_close_price'] = current_close
                investment['goal']['loss'] = new_trailing_stop_price
                
                logger.info(f"🎯 {stock['id']} 更新动态止损: {trailing_stop_price:.4f} -> {new_trailing_stop_price:.4f}")
    
    @staticmethod
    def execute_stage_action(stock: Dict[str, Any], investment: Dict[str, Any], stage: Dict[str, Any], record_of_today: Dict[str, Any], tracker: Dict[str, Any]) -> None:
        """
        执行分段平仓的具体动作
        """
        action = stage.get('action', '')
        profit_rate = stage.get('profit_rate', 0)
        current_close = float(record_of_today['close'])
        purchase_price = float(investment['goal']['purchase'])
        
        if action == 'move_stop_loss_to_breakeven':
            # 将止损移到不亏不赚
            investment['goal']['loss'] = purchase_price
            # logger.info(f"🎯 {stock['id']} 涨幅{profit_rate*100:.0f}%: 止损移到不亏不赚 {purchase_price:.4f}")
            
        elif action == 'partial_exit':
            # 部分平仓 - 修正：平仓总仓位的20%，而不是剩余仓位的20%
            exit_ratio = stage.get('exit_ratio', 0.2)
            staged_exit = investment.get('staged_exit', {})
            current_position_ratio = staged_exit.get('current_position_ratio', 1.0)
            
            # 计算平仓收益 - 基于总仓位计算
            exit_profit = (current_close - purchase_price) * exit_ratio
            remaining_position_ratio = current_position_ratio - exit_ratio  # 直接减去总仓位的比例
            
            # 更新累计已实现收益
            total_realized_profit = staged_exit.get('total_realized_profit', 0.0) + exit_profit
            total_realized_profit_rate = total_realized_profit / purchase_price
            staged_exit['total_realized_profit'] = total_realized_profit
            staged_exit['total_realized_profit_rate'] = total_realized_profit_rate
            
            # 更新持仓比例
            staged_exit['current_position_ratio'] = remaining_position_ratio
            
            # 记录部分平仓
            # logger.info(f"🎯 {stock['id']} 涨幅{profit_rate*100:.0f}%: 平仓总仓位{exit_ratio*100:.0f}%, 收益{exit_profit:.4f}, 累计收益{total_realized_profit:.4f}({total_realized_profit_rate*100:.1f}%), 剩余持仓{remaining_position_ratio*100:.0f}%")
            
            # 如果剩余持仓为0，完全平仓
            if remaining_position_ratio <= 0:
                HLSimulator.settle_result('win', stock, investment, record_of_today, tracker)
                
        elif action == 'dynamic_trailing_stop':
            # 动态止盈 - 现在由专门的方法处理
            pass