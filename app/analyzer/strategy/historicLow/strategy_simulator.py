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
from .strategy_entity import HistoricLowEntity

class HLSimulator:
    def __init__(self, strategy):
        self.strategy = strategy
        
        # init tracker
        self.invest_recorder = InvestmentRecorder()

        # 汇总收集器（单线程汇总，无需锁）
        self.session_results = []

        # 是否启用详细日志
        self.is_verbose = False

    # ========================================================
    # External (Bridge) APIs:
    # ========================================================

    def test_strategy(self) -> None:
        
        if not self.is_invest_settings_valid():
            return

        stock_idx = self.get_stock_list_by_test_mode()

        jobs = self.build_jobs(stock_idx)

        results = self.run_jobs(jobs)

        self.consolidate_summaries(stock_idx, results)
        
        self.present_investment_summary(results)   



    # ========================================================
    # Core logic:
    # ========================================================


    #      'targets': {
        #         'all': {
        #             'stop_loss': [
        #                 {
        #                     'close_invest': True,
        #                     'name': 'loss20%',
        #                     'ratio': -0.2
        #                 },
        #                 {
        #                     'close_invest': True,
        #                     'name': 'break_even',
        #                     'ratio': 0
        #                 },
        #                 {
        #                     'close_invest': True,
        #                     'name': 'dynamic',
        #                     'ratio': -0.1
        #                 }
        #             ],
        #             'take_profit': [
        #                 {
        #                     'name': 'win10%',
        #                     'ratio': 0.1,
        #                     'sell_ratio': 0.2,
        #                     'set_stop_loss': 'break_even'
        #                 },
        #                 {
        #                     'name': 'win20%',
        #                     'ratio': 0.2,
        #                     'sell_ratio': 0.2
        #                 },
        #                 {
        #                     'name': 'win30%',
        #                     'ratio': 0.3,
        #                     'sell_ratio': 0.2
        #                 },
        #                 {
        #                     'name': 'win40%',
        #                     'ratio': 0.4,
        #                     'sell_ratio': 0.2,
        #                     'set_stop_loss': 'dynamic'
        #                 }
        #             ]
        #         }
        #     },
        #     'investment_ratio_left': 1.0,
        #     'completed': [],
        #     'ongoing': []
        # }





    @staticmethod
    def simulate_one_day(stock: Dict[str, Any], daily_k_lines: List[Dict[str, Any]], tracker: Dict[str, Any]) -> None:
        record_of_today = daily_k_lines[-1]

        investment = tracker['investing'].get(stock['id'])

        # if there is an investing opportunity on going, try to settle it firstly
        if investment:
            is_investment_ended, investment = HLSimulator.check_targets(investment, record_of_today)

            HLSimulator.update_investment_max_min_close(investment, record_of_today)

            if is_investment_ended:
                tracker['settled'][stock['id']] = investment
                del tracker['investing'][stock['id']]

        # if no investment, scan to find an investment opportunity
        else:

            from app.analyzer.strategy.historicLow.strategy import HistoricLowStrategy
            from app.analyzer.strategy.historicLow.strategy import HistoricLowEntity

            opportunity = HistoricLowStrategy.scan_single_stock(stock, daily_k_lines)

            if opportunity:
                tracker['investing'][stock['id']] = HistoricLowEntity.to_investment(opportunity)
        





            # current_close = record_of_today['close']
            # current_date = record_of_today['date']
            
            # # 更新持有期间的最高/最低价
            # if current_close > investing_opportunity['period_max_close']:
            #     investing_opportunity['period_max_close'] = current_close
            #     investing_opportunity['period_max_close_date'] = current_date
            # if current_close < investing_opportunity['period_min_close']:
            #     investing_opportunity['period_min_close'] = current_close
            #     investing_opportunity['period_min_close_date'] = current_date
            
            # # 新增：分段平仓逻辑
            # if investing_opportunity.get('staged_exit', {}).get('enabled', False):
            #     HLSimulator.process_staged_exit(stock, investing_opportunity, record_of_today, tracker)
            
            # # 检查是否触发止损或止盈
            # # 分段平仓启用时：达到止盈仅做分段处理，不整单结算；仅当触发止损（含动态止损）时才结算
            # staged_enabled = investing_opportunity.get('staged_exit', {}).get('enabled', False)
            # if not staged_enabled and current_close >= investing_opportunity['goal']['win']:
            #     HLSimulator.settle_result('win', stock, investing_opportunity, record_of_today, tracker)
            # elif current_close <= investing_opportunity['goal']['loss']:
            #     # 若已启用动态止损，记录触发点日志
            #     if investing_opportunity.get('staged_exit', {}).get('dynamic_trailing_enabled', False):
            #         ts_price = investing_opportunity.get('staged_exit', {}).get('trailing_stop_price')
            #     HLSimulator.settle_result('loss', stock, investing_opportunity, record_of_today, tracker)
            # else:
            #     pass
            # # 结算后可继续寻找机会
            # if stock['id'] not in tracker['investing']:
            #     from app.analyzer.strategy.historicLow.strategy import HistoricLowStrategy
            #     opp = HistoricLowStrategy.scan_single_stock(stock, daily_k_lines)
            #     if opp:
            #         tracker['investing'][stock['id']] = opp






    @staticmethod
    def check_targets(investment: Dict[str, Any], record_of_today: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        price_today = record_of_today['close']
        purchase_price = investment['purchase_price']

        to_be_achieved_stop_loss_targets = investment['targets']['all']['stop_loss']
        to_be_achieved_take_profit_targets = investment['targets']['all']['take_profit']

        is_investment_ended = False

        for target in to_be_achieved_take_profit_targets:
            if 'is_achieved' in target and target['is_achieved']:
                continue

            if price_today >= purchase_price * (1 + target['ratio']):
                investment['targets']['investment_ratio_left'] -= target['sell_ratio']

                target = HLSimulator.to_settable_target(target, target['sell_ratio'], price_today - purchase_price, price_today, record_of_today['date'])
                investment['targets']['completed'].append(target)

                if 'set_stop_loss' in target and target['set_stop_loss'] == 'break_even':
                    investment['targets']['is_breakeven'] = True

                if 'set_stop_loss' in target and target['set_stop_loss'] == 'dynamic':
                    investment['targets']['is_dynamic_stop_loss'] = True

        for target in to_be_achieved_stop_loss_targets:
            if investment['targets']['is_dynamic_stop_loss']:
                if price_today <= purchase_price * (1 + target['ratio']):
                    if 'close_invest' in target and target['close_invest']:
                        sell_ratio = investment['targets']['investment_ratio_left']
                        investment['targets']['investment_ratio_left'] = 0
                    else:
                        sell_ratio = target['sell_ratio']
                        investment['targets']['investment_ratio_left'] -= target['sell_ratio']

                    target = HLSimulator.to_settable_target(target, sell_ratio, price_today - purchase_price, price_today, record_of_today['date'])
                    investment['targets']['completed'].append(target)

            elif investment['targets']['is_breakeven']:
                if price_today <= purchase_price:
                    if 'close_invest' in target and target['close_invest']:
                        sell_ratio = investment['targets']['investment_ratio_left']
                        investment['targets']['investment_ratio_left'] = 0
                    else:
                        sell_ratio = target['sell_ratio']
                        investment['targets']['investment_ratio_left'] -= target['sell_ratio']

                    target = HLSimulator.to_settable_target(target, sell_ratio, price_today - purchase_price, price_today, record_of_today['date'])
                    investment['targets']['completed'].append(target)
                    
            else:
                if price_today <= purchase_price * (1 + target['ratio']):
                    if 'close_invest' in target and target['close_invest']:
                        sell_ratio = investment['targets']['investment_ratio_left']
                        investment['targets']['investment_ratio_left'] = 0
                    else:
                        sell_ratio = target['sell_ratio']
                        investment['targets']['investment_ratio_left'] -= target['sell_ratio']

                    target = HLSimulator.to_settable_target(target, sell_ratio, price_today - purchase_price, price_today, record_of_today['date'])
                    investment['targets']['completed'].append(target)

        # the invest run out of invested money, need to settle the result
        if investment['targets']['investment_ratio_left'] <= 0:
            is_investment_ended = True

            achieved_targets = investment['targets']['completed']
            overall_profit = 0
            for target in achieved_targets:
                overall_profit += target['profit'] * target['sell_ratio']

            investment['overall_profit'] = overall_profit
            investment['overall_profit_rate'] = overall_profit / purchase_price

            if overall_profit > 0:
                investment['result'] = InvestmentResult.WIN.value
            else:
                investment['result'] = InvestmentResult.LOSS.value

            for target in achieved_targets:
                target['weighted_profit'] = target['profit'] * target['sell_ratio']
                target['profit_contribution'] = target['profit'] / overall_profit

        return is_investment_ended, investment

    

    @staticmethod
    def to_settable_target(target: Dict[str, Any], sell_ratio: float, profit: float, exit_price: float, exit_date: str) -> Dict[str, Any]:
        target['is_achieved'] = True
        if 'sell_ratio' not in target or target['sell_ratio'] <= 0:
            target['sell_ratio'] = sell_ratio
        target['profit'] = profit
        target['exit_price'] = exit_price
        target['exit_date'] = exit_date
        return target;




    @staticmethod
    def update_investment_max_min_close(investment: Dict[str, Any], record_of_today: Dict[str, Any]) -> None:
        if record_of_today['close'] > investment['tracking']['max_close_reached']['price']:
            investment['tracking']['max_close_reached']['price'] = record_of_today['close']
            investment['tracking']['max_close_reached']['date'] = record_of_today['date']
            investment['tracking']['max_close_reached']['ratio'] = (record_of_today['close'] - investment['purchase_price']) / investment['purchase_price']
        if record_of_today['close'] < investment['tracking']['min_close_reached']['price']:
            investment['tracking']['min_close_reached']['price'] = record_of_today['close']
            investment['tracking']['min_close_reached']['date'] = record_of_today['date']
            investment['tracking']['min_close_reached']['ratio'] = (record_of_today['close'] - investment['purchase_price']) / investment['purchase_price']




    # ========================================================
    # Main steps:
    # ========================================================


    def is_invest_settings_valid(self) -> bool:
        # 验证策略配置
        is_valid, validation_errors = HistoricLowService.validate_strategy_settings(strategy_settings)

        if not is_valid:
            logger.error("❌ 策略配置验证失败:")
            for error in validation_errors:
                logger.error(f"  - {error}")
            raise ValueError("策略配置无效，请检查上述错误")
        logger.info("✅ 策略配置验证通过")

        return is_valid

    def get_stock_list_by_test_mode(self) -> List[Dict[str, Any]]:
        stock_list = []
        if self.strategy.strategy_settings.get('test_mode',{}).get('test_problematic_stocks_only', False):
            stock_list = self.strategy.strategy_settings.get('problematic_stocks', {}).get('list', [])
            logger.info(f"🔍 测试模式: 问题股票，共{len(stock_list)}只股票")

        else:

            stock_list = self.strategy.required_tables["stock_index"].load_filtered_index()

            test_amount = self.strategy.strategy_settings.get('test_mode', {}).get('max_test_stocks', None)

            if test_amount:
                start_idx = self.strategy.strategy_settings.get('test_mode', {}).get('start_idx', 0)
                end_idx = start_idx + test_amount
                stock_list = stock_list[start_idx : end_idx]
                logger.info(f"🔍 测试模式: 部分模式，共{len(stock_list)}只股票")
            else:
                logger.info(f"🔍 测试模式: 全量模式，共{len(stock_list)}只股票")

        return stock_list


    def consolidate_summaries(self, stock_idx: List[Dict[str, Any]], results: List[Dict[str, Any]]) -> None:
        stock_summaries = self.consolidate_stock_summaries(results)
        session_summary =  HistoricLowEntity.to_session_summary(results)
        self._record_all_summaries(stock_idx, stock_summaries, session_summary)



    def consolidate_stock_summaries(self, stock_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        stock_summaries = {}
        for stock_result in stock_results:
            summary = HistoricLowEntity.to_stock_summary(stock_result)  
            stock_summaries[summary['stock_id']] = summary
        return stock_summaries


    






    # ========================================================
    # Workers:
    # ========================================================

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

        return actual_results


    # because the python does not share the class instance, we need to use static method to simulate the single stock
    @classmethod
    def simulate_single_stock(cls, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        类方法：独立的模拟函数，可以安全地用于多进程
        不依赖实例状态，避免pickle问题
        """

        # 在子进程内按需加载复权后的日线
        daily_data = cls.load_qfq_daily(job_data['id'])

        min_required_daily_records = strategy_settings.get('daily_data_requirements', {}).get('min_required_daily_records')

        if len(daily_data) < min_required_daily_records:
            return {
                'stock_info': job_data,
                'investments': {}
            }

        # 本地tracker
        tracker: Dict[str, Any] = {
            'investing': {},
            'settled': {}
        }


        # 累积分发K线，模拟
        current_daily_data: List[Dict[str, Any]] = []

        for record_of_today in daily_data:
            current_daily_data.append(record_of_today)
            if len(current_daily_data) < min_required_daily_records:
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











    # ========================================================
    # Utils:
    # ========================================================

    @staticmethod
    def load_qfq_daily(stock_id: str) -> List[Dict[str, Any]]:
        """
        加载指定股票的前复权日线
        """
        from utils.db.db_manager import get_db_manager
        db = get_db_manager()
        kline_table = db.get_table_instance('stock_kline')
        adj_table = db.get_table_instance('adj_factor')
        raw = kline_table.get_all_k_lines_by_term(stock_id, 'daily')
        factors = adj_table.get_stock_factors(stock_id)

        daily_data = DataSourceService.to_qfq(raw, factors)

        daily_data = HistoricLowService.filter_out_negative_records(daily_data)

        return daily_data

    @staticmethod
    def is_meet_strategy_requirements(daily_data: List[Dict[str, Any]]) -> bool:
        min_required = strategy_settings.get('daily_data_requirements', {}).get('min_required_daily_records', 2000)
        return len(daily_data) >= min_required

















    
    @staticmethod
    def get_stage_info(stage: Dict[str, Any]) -> Dict[str, Any]:
        """从stage配置中提取统一的信息"""
        name = stage.get('name', '')
        ratio = float(stage.get('ratio', 0.0))
        sell_ratio = float(stage.get('sell_ratio', 1.0))
        close_invest = stage.get('close_invest', False)  # 是否清仓
        set_stop_loss = stage.get('set_stop_loss', None)
        
        return {
            'name': name,
            'ratio': ratio,
            'sell_ratio': sell_ratio,
            'close_invest': close_invest,
            'set_stop_loss': set_stop_loss,
            'is_dynamic': name == 'dynamic',
            'is_stop_loss': ratio <= 0,
            'is_take_profit': ratio > 0
        }
        

    





    def _record_all_summaries(self, stocks: List[Dict[str, Any]], stock_summaries: Dict[str, Dict[str, Any]], session_summary: Dict[str, Any]):
        """记录所有汇总结果到investment_recorder"""
        # 从session_results中获取每只股票的原始数据
        for stock_result in self.session_results:
            stock = stock_result['stock_info']
            investments = stock_result['investments']
            
            # 转换为investment_recorder期望的格式
            investment_history = []
            for investment in investments.values():
                # 直接使用结算期望格式（包含targets等新字段）
                settlement_record = investment.get('settlement_record')
                if settlement_record:
                    investment_history.append(settlement_record)
            
            # 只有当股票有投资记录时才生成文件
            if investment_history:
                self.invest_recorder.to_record(stock, investment_history)
        
        # 记录会话汇总
        self.invest_recorder._save_session_summary(session_summary)
        
        # 更新meta文件
        self.invest_recorder._update_meta_file()
        
        # 模拟完成后更新黑名单
        self._update_blacklist_after_simulation()

    def _update_blacklist_after_simulation(self):
        """模拟完成后更新黑名单"""
        try:
            from .strategy_analysis import HistoricLowAnalysis
            
            # 创建分析器实例
            analyzer = HistoricLowAnalysis()
            
            # 获取最新的模拟结果目录
            latest_session_dir = analyzer.get_latest_session_dir()
            
            # 加载投资数据
            investments = analyzer.load_investment_data(latest_session_dir)
            
            if not investments:
                print("⚠️  没有找到投资数据，跳过黑名单更新")
                return
            
            # 定义新的黑名单（使用更合理的标准）
            new_blacklist = analyzer.define_blacklist(
                investments=investments,
                min_investments=3,  # 最少3次投资
                max_win_rate=30.0,  # 胜率低于30%（更严格）
                max_avg_profit=-5.0  # 平均收益低于-5%（更严格）
            )
            
            # 获取当前黑名单
            current_blacklist = strategy_settings.get('problematic_stocks', {}).get('list', [])
            
            # 分析黑名单变化
            changes = analyzer.analyze_blacklist_changes(current_blacklist, new_blacklist)
            
            # 打印黑名单更新报告
            report = {
                'changes': changes,
                'new_blacklist': new_blacklist,
                'current_blacklist': current_blacklist,
                'criteria': {
                    'min_investments': 3,
                    'max_win_rate': 30.0,
                    'max_avg_profit': -5.0
                },
                'summary': {
                    'current_count': len(current_blacklist),
                    'new_count': len(new_blacklist),
                    'removed_count': len(changes.get('removed', [])),
                    'added_count': len(changes.get('added', [])),
                    'kept_count': len(changes.get('kept', []))
                }
            }
            analyzer.print_blacklist_report(report)
            
            # 更新配置文件中的黑名单
            self._update_blacklist_in_settings(new_blacklist)
            
            print(f"✅ 黑名单更新完成！新黑名单包含 {len(new_blacklist)} 只股票")
            
        except Exception as e:
            print(f"❌ 黑名单更新失败: {e}")
            import traceback
            traceback.print_exc()

    def _update_blacklist_in_settings(self, new_blacklist: List[str]):
        """更新配置文件中的黑名单"""
        try:
            # 读取当前配置文件
            settings_file = "app/analyzer/strategy/historicLow/strategy_settings.py"
            
            with open(settings_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 构建新的黑名单配置
            blacklist_lines = []
            blacklist_lines.append('        "list": [')
            
            for i, stock in enumerate(new_blacklist):
                # 获取股票名称（如果有的话）
                stock_name = self._get_stock_name(stock)
                comment = f"  # {stock_name}" if stock_name else ""
                comma = "," if i < len(new_blacklist) - 1 else ""
                blacklist_lines.append(f'            "{stock}"{comma}{comment}')
            
            blacklist_lines.append('        ],')
            blacklist_lines.append(f'        "count": {len(new_blacklist)},  # 问题股票总数')
            blacklist_lines.append('        "description": "基于最新模拟结果自动更新的黑名单"')
            
            new_blacklist_config = '\n'.join(blacklist_lines)
            
            # 替换黑名单配置
            import re
            pattern = r'"problematic_stocks":\s*\{[^}]*\}'
            replacement = f'"problematic_stocks": {{\n{new_blacklist_config}\n    }}'
            
            new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)
            
            # 写回文件
            with open(settings_file, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            print(f"📝 已更新配置文件中的黑名单")
            
        except Exception as e:
            print(f"❌ 更新配置文件失败: {e}")

    def _get_stock_name(self, stock_id: str) -> str:
        """获取股票名称（简化版本）"""
        # 这里可以扩展为从数据库或API获取股票名称
        # 目前返回空字符串
        return ""

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


    def present_investment_summary(self, results: List[Dict[str, Any]]) -> None:
        """打印投资记录摘要"""
        # 获取投资结果统计信息（从session_results中获取）
        results_summary = {}
        if results:
            # 使用统一的会话级汇总
            results_summary = HistoricLowEntity.to_session_summary(results)
        
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
    def settle_result(result_value: str, stock: Dict[str, Any], opportunity: Dict[str, Any], record_of_today: Dict[str, Any], tracker: Dict[str, Any]) -> None:
        try:
            start_date = opportunity['invest_start_date']
            end_date = record_of_today['date']
            invest_duration_days = AnalyzerService.get_duration_in_days(start_date, end_date)
            
            # 计算综合收益（已实现收益 + 未实现收益）
            purchase_price = opportunity['goal']['purchase']
            current_close = record_of_today['close']
            
            # 检查价格是否有效，防止除零错误
            if purchase_price <= 0 or current_close <= 0:
                logger.error(f"❌ {stock['id']} 价格数据无效: purchase_price={purchase_price}, current_close={current_close}")
                return
            staged_exit = opportunity.get('staged_exit', {})
            total_realized_profit = staged_exit.get('total_realized_profit', 0.0)
            remaining_position_ratio = staged_exit.get('current_position_ratio', 1.0)
            
            # 确保剩余仓位不为负数
            remaining_position_ratio = max(0.0, remaining_position_ratio)
            
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
            
            # 计算投资开始时的斜率 + 记录前10日日度涨跌情况
            freeze_data = opportunity.get('freeze_data', [])
            slope_ratio = 0.0
            pre_invest_series = {}
            if len(freeze_data) >= 10:
                from app.analyzer.strategy.historicLow.strategy_service import HistoricLowService
                recent_10 = freeze_data[-10:]
                start_price = float(recent_10[0]['close'])
                end_price = float(recent_10[-1]['close'])
                change_ratio = (end_price - start_price) / start_price if start_price != 0 else 0.0
                # 直接使用价格变化率
                slope_ratio = change_ratio

                # 记录最近10天的收盘价与日度涨跌（相对前一日）
                closes = [round(float(r.get('close', 0.0)), 4) for r in recent_10]
                dates = [r.get('date') for r in recent_10]
                day_changes_pct = []
                for i in range(1, len(recent_10)):
                    prev = float(recent_10[i-1].get('close', 0.0))
                    cur = float(recent_10[i].get('close', 0.0))
                    pct = ((cur - prev) / prev * 100.0) if prev != 0 else 0.0
                    day_changes_pct.append(round(pct, 2))
                pre_invest_series = {
                    'start_date': dates[0],
                    'end_date': dates[-1],
                    'closes': closes,
                    'day_changes_pct': day_changes_pct
                }
            
            # 生成targets（先止盈，后止损）
            targets: List[Dict[str, Any]] = []
            start_date_str = opportunity['invest_start_date']
            
            # 1. 先填入已实现的止盈targets
            exits = (staged_exit.get('exits') or [])
            for ex in exits:
                sell_date = ex.get('sell_date') or end_date
                duration_days_for_target = AnalyzerService.get_duration_in_days(start_date_str, sell_date)
                targets.append(HistoricLowEntity.to_target(
                    target_name=ex.get('name') or '0%',
                    is_achieved=True,
                    profit=round(float(ex.get('profit') or 0.0), 4),
                    profit_rate=float(ex.get('profit_rate') or 0.0),
                    profit_weight=0.0,  # 结算后统一回填
                    duration=int(duration_days_for_target or 0),
                    sell_date=sell_date,
                    sell_price=round(float(ex.get('sell_price') or record_of_today.get('close') or 0.0), 4)
                ))

            # 2. 检查是否触及止损，如果是则添加止损target
            is_stop_loss_triggered = False
            stop_loss_price = None
            stop_loss_type = None
            
            # 检查是否触及动态止损
            if staged_exit.get('dynamic_trailing_enabled', False):
                trailing_stop_price = staged_exit.get('trailing_stop_price')
                if current_close <= trailing_stop_price:
                    is_stop_loss_triggered = True
                    stop_loss_price = trailing_stop_price
                    stop_loss_type = 'dynamic'
            
            # 检查是否触及普通止损
            elif current_close <= loss_price:
                is_stop_loss_triggered = True
                stop_loss_price = current_close
                stop_loss_type = 'normal'
            
            # 如果触及止损，添加止损target
            if is_stop_loss_triggered and remaining_position_ratio > 0:
                duration_days_for_target = AnalyzerService.get_duration_in_days(start_date_str, end_date)
                stop_loss_profit_rate = (stop_loss_price / purchase_price) - 1.0 if purchase_price != 0 else 0.0
                
                if stop_loss_type == 'dynamic':
                    targets.append(HistoricLowEntity.to_target(
                        target_name='dynamic',
                        is_achieved=True,
                        profit=round((stop_loss_price - purchase_price) * remaining_position_ratio, 4),
                        profit_rate=round(stop_loss_profit_rate, 6),
                        profit_weight=0.0,
                        duration=int(duration_days_for_target or 0),
                        sell_date=end_date,
                        sell_price=round(stop_loss_price, 4)
                    ))
                else:
                    # 使用记录的当前止损阶段名称
                    target_name = staged_exit.get('current_stop_loss_stage', '-20%')
                    
                    targets.append(HistoricLowEntity.to_target(
                        target_name=target_name,
                        is_achieved=True,
                        profit=round((stop_loss_price - purchase_price) * remaining_position_ratio, 4),
                        profit_rate=round(stop_loss_profit_rate, 6),
                        profit_weight=0.0,
                        duration=int(duration_days_for_target or 0),
                        sell_date=end_date,
                        sell_price=round(stop_loss_price, 4)
                    ))
            
            # 3. 如果没有任何targets且是loss，添加初始止损target
            if not targets and actual_result == 'loss':
                duration_days_for_target = AnalyzerService.get_duration_in_days(start_date_str, end_date)
                loss_profit_rate = (current_close / purchase_price) - 1.0 if purchase_price != 0 else 0.0
                
                # 使用记录的当前止损阶段名称
                target_name = staged_exit.get('current_stop_loss_stage', '-20%')
                
                targets.append(HistoricLowEntity.to_target(
                    target_name=target_name,
                    is_achieved=True,
                    profit=round((current_close - purchase_price) * 1.0, 4),
                    profit_rate=round(loss_profit_rate, 6),
                    profit_weight=0.0,
                    duration=int(duration_days_for_target or 0),
                    sell_date=end_date,
                    sell_price=round(current_close, 4)
                ))

            # 回填profit_weight（基于总综合收益，如果为0则全部为0）
            if abs(total_profit) > 0:
                for t in targets:
                    t['profit_weight'] = round((float(t.get('profit') or 0.0) / total_profit), 6)
            else:
                for t in targets:
                    t['profit_weight'] = 0.0

            # historic_low_ref（term/date/price + 原始detail）
            hl_ref = {}
            try:
                low_point = opportunity.get('valley_ref') or {}
                op_record = opportunity.get('opportunity_record') or {}
                low_point_price = float(low_point.get('lowest_price') or low_point.get('low_point_price') or low_point.get('min') or purchase_price)
                low_point_date = low_point.get('date') or op_record.get('date') or start_date
                # term 直接取 low_point['term']（几年前的低点）
                term_years = int(low_point.get('term') or 0)
                # 过滤掉不需要的字段（如 min/max/avg）
                filtered_detail = {}
                try:
                    filtered_detail = {k: v for k, v in (low_point or {}).items() if k not in ['min', 'max', 'avg']}
                except Exception:
                    filtered_detail = low_point

                hl_ref = {
                    'term': term_years,
                    'date': low_point_date,
                    'price': round(low_point_price, 4)
                }
            except Exception:
                hl_ref = {}

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
                # 综合收益率（小数，例如 0.33 表示 33%）
                'overall_profit_rate': round(total_profit_rate, 6),
                # 轨迹信息
                'tracks': {
                    'max_close_reached': { 'price': period_max_close, 'date': period_max_close_date, 'ratio': round(max_close_rate, 6) },
                    'min_close_reached': { 'price': period_min_close, 'date': period_min_close_date, 'ratio': round(min_close_rate, 6) }
                },
                # 斜率信息
                'slope_info': {
                    'slope_ratio': round(slope_ratio, 4),
                    'price_change_ratio': round(change_ratio, 4) if len(freeze_data) >= 10 else 0.0,
                    'start_price': round(start_price, 4) if len(freeze_data) >= 10 else 0.0,
                    'end_price': round(end_price, 4) if len(freeze_data) >= 10 else 0.0
                },
                # 投资前10天涨跌信息
                'pre_invest_series': pre_invest_series,
                # 投资条目（用于输出targets）
                'investment': {
                    'purchase_price': round(purchase_price, 4),
                    'targets': targets
                },
                # 历史低点引用
                'historic_low_ref': hl_ref,
                # 仅保留必要字段
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
            logger.info(f" {result_dot} {stock['id']} investment {actual_result} (综合收益 {total_profit_rate*100:.1f}%), duration: {invest_duration_days} days, slope: {slope_ratio*100:.1f}%")
            
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
        current_profit_rate = (current_close - purchase_price) / purchase_price if purchase_price != 0 else 0.0
        
        staged_exit = investment.get('staged_exit', {})
        exited_stages = staged_exit.get('exited_stages', [])
        
        # 使用新的 goal 配置构造阶段
        goal_cfg = strategy_settings.get('goal', {})
        take_profit_stages = (goal_cfg.get('take_profit') or {}).get('stages') or []
        stop_loss_stages = (goal_cfg.get('stop_loss') or {}).get('stages') or []
        stages = []
        
        # 1) 移动止损至不亏不赚：这个动作应该由止盈阶段触发，而不是作为独立阶段
        # 移除独立的break_even阶段，因为它会在价格下跌时错误触发
        # break_even止损移动应该通过take_profit阶段的set_stop_loss="break_even"来触发
        
        # 2) 分段止盈
        for s in take_profit_stages:
            info = HLSimulator.get_stage_info(s)
            stages.append({ 
                'profit_rate': info['ratio'], 
                'action': 'partial_exit', 
                'exit_ratio': info['sell_ratio'], 
                'close_invest': info['close_invest'],
                'name': info['name'],
                'set_stop_loss': info['set_stop_loss']
            })
        
        # 检查是否已经启动动态止损
        if staged_exit.get('dynamic_trailing_enabled', False):
            # 如果已经启动动态止损，只更新动态止损价格
            HLSimulator.update_trailing_stop(stock, investment, record_of_today)
            return
        
        # 按顺序检查每个阶段
        for i, stage in enumerate(stages):
            profit_rate = stage.get('profit_rate', 0)
            action = stage.get('action', '')
            # 使用 action+阈值 作为唯一键，避免 0.30 的部分平仓与动态止损互相覆盖
            stage_key = f"{action}:{profit_rate:.2f}"
            
            # 检查是否已经执行过这个阶段
            if stage_key in exited_stages:
                continue
            
            # 检查是否达到这个阶段的触发条件
            # 对于止盈阶段(profit_rate > 0)，检查 current_profit_rate >= profit_rate
            # 对于止损阶段(profit_rate <= 0)，检查 current_profit_rate <= profit_rate
            if (profit_rate > 0 and current_profit_rate >= profit_rate) or (profit_rate <= 0 and current_profit_rate <= profit_rate):
                # 执行当前阶段动作
                HLSimulator.execute_stage_action(stock, investment, stage, record_of_today, tracker)
                exited_stages.append(stage_key)
                staged_exit['exited_stages'] = exited_stages
                
                # 如果是动态止损阶段，启动动态止损
                if stage.get('action') == 'dynamic_trailing_stop':
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
        
        # 获取动态止损比例（来自goal.stop_loss.stages的loss_ratio）
        trailing_stop_ratio = float(stage.get('trail_ratio') or 0.10)
        
        staged_exit = investment.get('staged_exit', {})
        
        # 设置动态止损价格
        trailing_stop_price = current_close * (1 - trailing_stop_ratio)
        staged_exit['trailing_stop_price'] = trailing_stop_price
        staged_exit['last_close_price'] = current_close
        staged_exit['highest_close_since_trail'] = current_close
        staged_exit['trail_ratio'] = trailing_stop_ratio
        staged_exit['first_dynamic_start_close'] = current_close
        
        # 更新止损价格
        investment['goal']['loss'] = trailing_stop_price
        
        # logger.info(f"🎯 {stock['id']} 涨幅{profit_rate*100:.0f}%: 启动动态止损，highest_close={current_close:.4f}, trailing_stop_price={trailing_stop_price:.4f}")
    
    @staticmethod
    def update_trailing_stop(stock: Dict[str, Any], investment: Dict[str, Any], record_of_today: Dict[str, Any]) -> None:
        """
        更新动态止损价格
        """
        current_close = float(record_of_today['close'])
        staged_exit = investment.get('staged_exit', {})
        last_close_price = staged_exit.get('last_close_price', current_close)
        trailing_stop_price = staged_exit.get('trailing_stop_price', current_close)
        highest_close = staged_exit.get('highest_close_since_trail', current_close)
        trail_ratio = float(staged_exit.get('trail_ratio') or 0.10)
        
        # 如果当前价格更高，更新动态止损价格
        # 若出现新的更高收盘价，则提高最高价并上调止损（只上不下）
        if current_close > highest_close:
            highest_close = current_close
            staged_exit['highest_close_since_trail'] = highest_close
            new_trailing_stop_price = highest_close * (1 - trail_ratio)
            if new_trailing_stop_price > trailing_stop_price:
                trailing_stop_price = new_trailing_stop_price
                staged_exit['trailing_stop_price'] = trailing_stop_price
                investment['goal']['loss'] = trailing_stop_price
                # logger.info(f"🎯 {stock['id']} 更新动态止损: {trailing_stop_price:.4f}")
    
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
            # 将止损移到不亏不赚 - 这只是止损价调整，不记录target
            investment['goal']['loss'] = purchase_price
            # logger.info(f"🎯 {stock['id']} 涨幅{profit_rate*100:.0f}%: 止损移到不亏不赚 {purchase_price:.4f}")
            
        elif action == 'partial_exit':
            # 部分平仓 - sell_ratio始终代表卖出总仓位的比例
            exit_ratio = stage.get('exit_ratio', 0.2)
            close_invest = stage.get('close_invest', False)
            staged_exit = investment.get('staged_exit', {})
            current_position_ratio = staged_exit.get('current_position_ratio', 1.0)
            
            if close_invest:
                # 清仓：卖出所有剩余仓位
                actual_exit_ratio = current_position_ratio
                remaining_position_ratio = 0.0
            else:
                # 部分平仓：卖出总仓位的比例
                actual_exit_ratio = exit_ratio
                remaining_position_ratio = current_position_ratio - exit_ratio
            
            # 计算平仓收益 - 基于实际平仓比例计算
            exit_profit = (current_close - purchase_price) * actual_exit_ratio
            
            # 更新累计已实现收益
            total_realized_profit = staged_exit.get('total_realized_profit', 0.0) + exit_profit
            total_realized_profit_rate = total_realized_profit / purchase_price if purchase_price != 0 else 0.0
            staged_exit['total_realized_profit'] = total_realized_profit
            staged_exit['total_realized_profit_rate'] = total_realized_profit_rate
            
            # 更新持仓比例
            staged_exit['current_position_ratio'] = remaining_position_ratio
            
            # 记录本次分段平仓的target明细（只有真正的分段平仓才记录）
            exits = staged_exit.get('exits', [])
            stage_name = stage.get('name', str(profit_rate))
            exits.append(HistoricLowEntity.to_target(
                target_name=stage_name,
                is_achieved=True,
                profit=round(exit_profit, 4),
                profit_rate=round((current_close / purchase_price) - 1.0, 6) if purchase_price != 0 else 0.0,
                profit_weight=0.0,  # 结算时统一回填
                duration=0,  # 结算时统一计算
                sell_date=record_of_today.get('date'),
                sell_price=round(current_close, 4)
            ))
            staged_exit['exits'] = exits

            # 记录部分平仓
            # logger.info(f"🎯 {stock['id']} 涨幅{profit_rate*100:.0f}%: 平仓总仓位{exit_ratio*100:.0f}%, 收益{exit_profit:.4f}, 累计收益{total_realized_profit:.4f}({total_realized_profit_rate*100:.1f}%), 剩余持仓{remaining_position_ratio*100:.0f}%")
            
            # 检查是否需要设置止损策略
            set_stop_loss = stage.get('set_stop_loss')
            if set_stop_loss == 'break_even':
                investment['goal']['loss'] = purchase_price
                staged_exit['current_stop_loss_stage'] = 'break_even'
                # logger.info(f"🎯 {stock['id']} {stage_name}止盈后：止损移到保本位置 {purchase_price:.4f}")
            elif set_stop_loss == 'dynamic':
                # 启动动态止损
                HLSimulator.start_dynamic_trailing_stop(stock, investment, stage, record_of_today)
                staged_exit['dynamic_trailing_enabled'] = True
                staged_exit['current_stop_loss_stage'] = 'dynamic'
                # logger.info(f"🎯 {stock['id']} {stage_name}止盈后：启动动态止损")
            
            # 如果剩余持仓为0，完全平仓
            if remaining_position_ratio <= 0:
                HLSimulator.settle_result('win', stock, investment, record_of_today, tracker)
                
        elif action == 'dynamic_trailing_stop':
            # 动态止盈 - 现在由专门的方法处理
            pass

    def simulate_capital_flow_from_results(self, session_dir: str, initial_capital: float, start_date: str = "20240101", min_shares: int = 1000, use_kelly: bool = False) -> Dict[str, Any]:
        pool_capital: float = float(initial_capital)
        invested_cost: float = 0.0
        positions: Dict[Tuple[str, str], Dict[str, Any]] = {}

        if not os.path.isdir(session_dir):
            raise FileNotFoundError(f"session_dir not found: {session_dir}")

        buy_events: List[Tuple[str, str, float]] = []
        sell_events: List[Tuple[str, str, float, float, str, str]] = []
        partial_sell_events: List[Tuple[str, str, str, float, float]] = []  # (sell_date, stock_id, start_date, exit_ratio, sell_price)
        # 历史统计（用于凯利）
        history: Dict[str, List[Tuple[float, str]]] = {}  # stock_id -> list of (overall_profit_rate, status) for s_date < start_date

        for filename in os.listdir(session_dir):
            if not filename.endswith('.json') or filename == 'session_summary.json':
                continue
            stock_id = filename[:-5]
            file_path = os.path.join(session_dir, filename)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except Exception:
                continue

            results = data.get('results', [])
            if not isinstance(results, list):
                continue

            for item in results:
                s_date = item.get('start_date') or ""
                e_date = item.get('end_date') or ""
                try:
                    purchase_price = float(item.get('purchase_price') or 0.0)
                    profit_rate = float(item.get('overall_profit_rate') or 0.0)
                except Exception:
                    continue
                status = str(item.get('status') or "")
                if not purchase_price:
                    continue
                if s_date and s_date >= start_date:
                    buy_events.append((s_date, stock_id, purchase_price))
                    if e_date:
                        sell_events.append((e_date, stock_id, purchase_price, profit_rate, status, s_date))

                    # 解析分段平仓targets，生成部分卖出事件
                    inv_obj = item.get('investment') or {}
                    targets = inv_obj.get('targets') or []
                    for t in targets:
                        try:
                            sell_date = t.get('sell_date') or ""
                            sell_price = float(t.get('sell_price') or 0.0)
                            tgt_profit = float(t.get('profit') or 0.0)
                            # 通过 profit = (sell_price - purchase_price) * exit_ratio 推导 exit_ratio
                            denom = (sell_price - float(purchase_price))
                            if sell_date and sell_price > 0 and abs(denom) > 0:
                                exit_ratio = tgt_profit / denom
                                # 过滤异常数值
                                if exit_ratio > 0 and exit_ratio <= 1.0001:
                                    partial_sell_events.append((sell_date, stock_id, s_date, float(exit_ratio), sell_price))
                        except Exception:
                            continue
                elif s_date:
                    # 收集历史（用于凯利）
                    try:
                        history.setdefault(stock_id, []).append((float(item.get('overall_profit_rate') or 0.0), str(status)))
                    except Exception:
                        pass

        buy_events.sort(key=lambda x: (x[0], x[1]))
        sell_events.sort(key=lambda x: (x[0], x[1]))

        # 同步处理：买入、部分卖出、最终卖出，按日期归并
        partial_sell_events.sort(key=lambda x: (x[0], x[1]))
        bi = 0
        si = 0
        psi = 0
        while bi < len(buy_events) or si < len(sell_events) or psi < len(partial_sell_events):
            next_buy_date = buy_events[bi][0] if bi < len(buy_events) else '99999999'
            next_partial_sell_date = partial_sell_events[psi][0] if psi < len(partial_sell_events) else '99999999'
            next_sell_date = sell_events[si][0] if si < len(sell_events) else '99999999'

            if next_buy_date <= next_partial_sell_date and next_buy_date <= next_sell_date:
                b_date, b_stock, b_price = buy_events[bi]
                # 计算凯利倍数（仅支持1倍或2倍）
                shares_multiple = 1
                if use_kelly:
                    hist = history.get(b_stock, [])
                    wins = [r for r, st in hist if (st or (r > 0)) in ['win'] or r > 0]
                    losses = [abs(r) for r, st in hist if (st or (r <= 0)) in ['loss'] or r <= 0]
                    p = (len(wins) / len(hist)) if hist else 0.5
                    avg_win = sum(wins) / len(wins) if wins else 0.1
                    avg_loss = sum(losses) / len(losses) if losses else 0.1
                    b_ratio = (avg_win / avg_loss) if avg_loss > 0 else 1.0
                    f_star = p - (1 - p) / b_ratio
                    # 简化映射：f* >= 0.5 -> 2倍，否则1倍
                    if f_star >= 0.5:
                        shares_multiple = 2
                required_capital = float(min_shares * shares_multiple) * float(b_price)
                if pool_capital >= required_capital:
                    pool_capital -= required_capital
                    invested_cost += required_capital
                    positions[(b_stock, b_date)] = {
                        'shares': min_shares * shares_multiple,
                        'cost': required_capital,
                        'purchase_price': b_price,
                    }
                bi += 1
            elif next_partial_sell_date <= next_sell_date:
                ps_date, ps_stock, ps_start, ps_ratio, ps_sell_price = partial_sell_events[psi]
                key = (ps_stock, ps_start)
                pos = positions.get(key)
                if pos and ps_ratio > 0:
                    # 以分段比例卖出对应份额
                    shares_to_sell = float(pos['shares']) * float(ps_ratio)
                    cost_to_remove = float(pos['cost']) * float(ps_ratio)
                    cash_inflow = shares_to_sell * float(ps_sell_price)
                    pool_capital += cash_inflow
                    invested_cost -= cost_to_remove
                    # 更新持仓剩余
                    pos['shares'] = float(pos['shares']) - shares_to_sell
                    pos['cost'] = float(pos['cost']) - cost_to_remove
                    if pos['shares'] <= 1e-6:
                        del positions[key]
                psi += 1
            else:
                s_date, s_stock, s_price, s_profit_rate, s_status, s_start = sell_events[si]
                key = (s_stock, s_start)
                pos = positions.get(key)
                if pos:
                    sell_price = float(s_price) * (1.0 + float(s_profit_rate))
                    sell_amount = float(pos['shares']) * sell_price
                    pool_capital += sell_amount
                    invested_cost -= float(pos['cost'])
                    del positions[key]
                si += 1

        return {
            'initial_capital': float(initial_capital),
            'ending_pool': round(pool_capital, 2),
            'ending_invested_cost': round(invested_cost, 2),
            'ending_total_assets': round(pool_capital + invested_cost, 2),
            'open_positions': len(positions),
        }