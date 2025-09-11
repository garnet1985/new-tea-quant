import stat
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

        self.generate_summary(stock_idx, results)
        
        # self.present_investment_summary(results)   



    # ========================================================
    # Core logic:
    # ========================================================
    @staticmethod
    def simulate_one_day(stock: Dict[str, Any], daily_k_lines: List[Dict[str, Any]], tracker: Dict[str, Any]) -> None:
        record_of_today = daily_k_lines[-1]

        investment = tracker['investing'].get(stock['id'])

        # if there is an investing opportunity on going, try to settle it firstly
        if investment:
            HLSimulator.update_investment_max_min_close(investment, record_of_today)
            
            is_investment_ended, investment = HLSimulator.check_targets(investment, record_of_today)

            if is_investment_ended:
                HLSimulator.settle_investment(investment)
                tracker['settled'].append(investment)  # 直接添加到数组中
                del tracker['investing'][stock['id']]

        # if no investment, scan to find an investment opportunity
        else:

            from app.analyzer.strategy.historicLow.strategy import HistoricLowStrategy
            from app.analyzer.strategy.historicLow.strategy import HistoricLowEntity

            opportunity = HistoricLowStrategy.scan_single_stock(stock, daily_k_lines)

            if opportunity:
                tracker['investing'][stock['id']] = HistoricLowEntity.to_investment(opportunity)


    @staticmethod
    def check_targets(investment: Dict[str, Any], record_of_today: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        is_investment_ended = False

        # warning: order is important!!! - take profit will drive stop loss strategy, so take profit need to go first
        investment = HLSimulator.check_take_profit_target(investment, record_of_today)

        investment = HLSimulator.check_stop_loss_target(investment, record_of_today)
        
        # the invest run out of invested money, need to settle the result
        if investment['targets']['investment_ratio_left'] <= 0:
            is_investment_ended = True
            investment['end_date'] = record_of_today['date']

        return is_investment_ended, investment

    @staticmethod
    def check_take_profit_target(investment: Dict[str, Any], record_of_today: Dict[str, Any]) -> Dict[str, Any]:
        price_today = record_of_today['close']
        purchase_price = investment['purchase_price']
        targets = investment['targets']['all']['take_profit']
        
        for target in targets:
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
                    investment['targets']['last_highest_close'] = price_today

        return investment
    


    @staticmethod
    def check_stop_loss_target(investment: Dict[str, Any], record_of_today: Dict[str, Any]) -> Dict[str, Any]:
        price_today = record_of_today['close']
        purchase_price = investment['purchase_price']
        stop_loss_config = investment['targets']['all']['stop_loss']

        # 根据当前状态检查对应的止损目标
        if investment['targets']['is_dynamic_stop_loss']:
            # 更新最高价
            if 'last_highest_close' not in investment['targets']:
                investment['targets']['last_highest_close'] = price_today
            else:
                investment['targets']['last_highest_close'] = max(investment['targets']['last_highest_close'], price_today)
            
            # 检查dynamic止损
            dynamic_target = stop_loss_config['dynamic']
            if 'is_achieved' not in dynamic_target or not dynamic_target['is_achieved']:
                if price_today <= investment['targets']['last_highest_close'] * (1 + dynamic_target['ratio']):
                    sell_ratio = investment['targets']['investment_ratio_left'] if dynamic_target.get('close_invest') else dynamic_target['sell_ratio']
                    investment['targets']['investment_ratio_left'] = 0 if dynamic_target.get('close_invest') else investment['targets']['investment_ratio_left'] - dynamic_target['sell_ratio']
                    
                    target = HLSimulator.to_settable_target(dynamic_target, sell_ratio, price_today - purchase_price, price_today, record_of_today['date'])
                    investment['targets']['completed'].append(target)





        elif investment['targets']['is_breakeven']:
            # 检查break_even止损
            breakeven_target = stop_loss_config['break_even']
            if 'is_achieved' not in breakeven_target or not breakeven_target['is_achieved']:
                if price_today <= purchase_price:
                    sell_ratio = investment['targets']['investment_ratio_left'] if breakeven_target.get('close_invest') else breakeven_target['sell_ratio']
                    investment['targets']['investment_ratio_left'] = 0 if breakeven_target.get('close_invest') else investment['targets']['investment_ratio_left'] - breakeven_target['sell_ratio']
                    
                    target = HLSimulator.to_settable_target(breakeven_target, sell_ratio, price_today - purchase_price, price_today, record_of_today['date'])
                    investment['targets']['completed'].append(target)





        else:
            # 检查所有初始止损目标
            for target in stop_loss_config['stages']:
                if 'is_achieved' in target and target['is_achieved']:
                    continue

                if price_today <= purchase_price * (1 + target['ratio']):
                    sell_ratio = investment['targets']['investment_ratio_left'] if target.get('close_invest') else target['sell_ratio']
                    investment['targets']['investment_ratio_left'] = 0 if target.get('close_invest') else investment['targets']['investment_ratio_left'] - target['sell_ratio']
                    
                    target = HLSimulator.to_settable_target(target, sell_ratio, price_today - purchase_price, price_today, record_of_today['date'])
                    investment['targets']['completed'].append(target)
        
        return investment



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

    @staticmethod
    def settle_investment(investment: Dict[str, Any]) -> None:
        purchase_price = investment['purchase_price']
        achieved_targets = investment['targets']['completed']
        
        # 完成状态：基于已完成的止盈/止损计算收益
        overall_profit = 0
        for target in achieved_targets:
            overall_profit += target['profit'] * target['sell_ratio']

        if overall_profit > 0:
            investment['result'] = InvestmentResult.WIN.value
        else:
            investment['result'] = InvestmentResult.LOSS.value

        investment['overall_profit'] = overall_profit
        investment['overall_profit_rate'] = overall_profit / purchase_price

        # 计算目标权重和贡献
        for target in achieved_targets:
            target['weighted_profit'] = target['profit'] * target['sell_ratio']
            if overall_profit != 0:  # 避免除零
                target['profit_contribution'] = target['profit'] / overall_profit
            else:
                target['profit_contribution'] = 0

        investment['invest_duration_days'] = AnalyzerService.get_duration_in_days(investment['start_date'], investment['end_date'])

    @staticmethod
    def settle_open_investment(investment: Dict[str, Any], final_price: float) -> None:
        """结算Open状态的投资（模拟结束时仍在持仓）"""
        purchase_price = investment['purchase_price']
        achieved_targets = investment['targets']['completed']
        
        # 计算未实现收益（基于剩余仓位）
        remaining_ratio = investment['targets']['investment_ratio_left']
        unrealized_profit = remaining_ratio * (final_price - purchase_price)
        
        # 计算已实现收益
        realized_profit = 0
        for target in achieved_targets:
            realized_profit += target['profit'] * target['sell_ratio']
        
        overall_profit = realized_profit + unrealized_profit
        investment['result'] = InvestmentResult.OPEN.value
        investment['overall_profit'] = overall_profit
        investment['overall_profit_rate'] = overall_profit / purchase_price

        # 计算目标权重和贡献（只对已完成的目标）
        for target in achieved_targets:
            target['weighted_profit'] = target['profit'] * target['sell_ratio']
            if overall_profit != 0:  # 避免除零
                target['profit_contribution'] = target['profit'] / overall_profit
            else:
                target['profit_contribution'] = 0

        investment['invest_duration_days'] = AnalyzerService.get_duration_in_days(investment['start_date'], investment['end_date'])


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


    def generate_summary(self, stock_idx: List[Dict[str, Any]], simulation_results: List[Dict[str, Any]]) -> None:
        pprint(simulation_results)




        # stock_summaries = self.consolidate_stock_summaries(results)
        # session_summary =  HistoricLowEntity.to_session_summary(results)
        # self._record_all_summaries(stock_idx, stock_summaries, session_summary)



    # def consolidate_stock_summaries(self, stock_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    #     stock_summaries = {}
    #     for stock_result in stock_results:
    #         summary = HistoricLowEntity.to_stock_summary(stock_result)  
    #         stock_summaries[summary['stock_id']] = summary
    #     return stock_summaries


    






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

        # tracker is per stock
        tracker: Dict[str, Any] = {
            'investing': {},
            'settled': []  # 改为数组，存储该股票的所有投资记录
        }


        # 累积分发K线，模拟
        current_daily_data: List[Dict[str, Any]] = []

        for record_of_today in daily_data:
            current_daily_data.append(record_of_today)
            if len(current_daily_data) < min_required_daily_records:
                continue
            
            # 模拟每日交易
            cls.simulate_one_day(job_data, current_daily_data, tracker)
            

        # 清算未结持仓为 open（使用settle_open_investment方法）
        if job_data['id'] in tracker['investing']:
            inv = tracker['investing'][job_data['id']]
            # 使用最后一天的记录作为结算记录
            last_record = daily_data[-1] if daily_data else None
            if last_record:
                # 设置结束日期为最后一天
                inv['end_date'] = last_record['date']
                # 使用专门的settle_open_investment方法处理open状态
                cls.settle_open_investment(inv, final_price=last_record['close'])
                # 添加到settled数组
                tracker['settled'].append(inv)
                # 从investing中删除
                del tracker['investing'][job_data['id']]
        
        return {
            'stock_info': job_data,
            'investments': tracker['settled']  # 直接返回数组，无需转换
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