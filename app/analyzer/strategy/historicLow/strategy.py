#!/usr/bin/env python3
"""
HistoricLow 策略 - 寻找股票的历史低点，识别可能的买入机会
"""
from doctest import debug
import time
from typing import Dict, List, Any, Tuple, Optional
from loguru import logger

from app.analyzer.libs.simulator.simulator import Simulator
from ...libs.base_strategy import BaseStrategy
from .strategy_service import HistoricLowService
from .strategy_entity import HistoricLowEntity
from .strategy_settings import strategy_settings
from app.analyzer.libs.investment import InvestmentRecorder
from app.data_source.data_source_service import DataSourceService

class HistoricLowStrategy(BaseStrategy):
    """HistoricLow 策略实现"""
    
    # 策略启用状态
    is_enabled = True
    
    def __init__(self, db, is_verbose=False):
        description = "历史低价策略: 使用某个周期前的历史最低点作为投资参考点，使用分段止盈来完成盈利"
        name = "Historic Low"
        abbreviation = "HL"

        super().__init__(
            db=db,
            is_verbose=is_verbose,
            name=name,
            abbreviation=abbreviation,
            description=description
        )
        
        # 加载策略设置
        self.strategy_settings = strategy_settings
        
        # 初始化投资记录器
        self.invest_recorder = InvestmentRecorder("historicLow")

        self.simulator = Simulator()


    def initialize(self):
        self._initialize_tables()

    def _initialize_tables(self):
        self.required_tables = {
            "stock_index": self.db.get_table_instance("stock_index"),
            "stock_kline": self.db.get_table_instance("stock_kline"),
            "adj_factor": self.db.get_table_instance("adj_factor"),
            # todo: will add storage later, for now use file system.
            # "meta": HLMetaModel(self.db),
            # "opportunity_history": HLOpportunityHistoryModel(self.db),
            # "strategy_summary": HLStrategySummaryModel(self.db)
        }

    # ========================================================
    # External (Bridge) APIs:
    # ========================================================
    async def scan(self) -> List[Dict[str, Any]]:
        stock_idx = self.required_tables["stock_index"].load_filtered_index()

        if not stock_idx:
            return []

        opportunities = self._scan_stocks_with_worker(stock_idx)

        self.report(opportunities)

        return opportunities

    def simulate(self) -> Dict[str, Any]:
        # 运行模拟 - 传递单日模拟函数和自定义汇总函数
        result = self.simulator.run(
            settings=strategy_settings,
            on_simulate_one_day=HistoricLowStrategy.simulate_single_day,
            on_single_stock_summary=HistoricLowStrategy.summarize_single_stock,
            on_session_summary=HistoricLowStrategy.summarize_session,
            on_simulate_complete=HistoricLowStrategy.present_final_report
        )
        return result


    # ========================================================
    # Core logic:
    # ========================================================

    @staticmethod
    def scan_single_stock(stock: Dict[str, Any], daily_records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """寻找投资机会"""

        freeze_records, history_records = HistoricLowStrategy.split_daily_data(daily_records)

        low_points = HistoricLowStrategy.find_low_points(history_records)

        opportunity = HistoricLowStrategy.find_opportunity_from_low_points(stock, low_points, freeze_records, history_records)

        return opportunity

    @staticmethod
    def split_daily_data(daily_records: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        分割日线数据为冻结期和历史期
        
        Args:
            daily_data: 完整的日线数据列表
            
        Returns:
            freeze_records: 投资冻结期的数据
            history_records: 可以用来寻找机会的日线数据
        """
        # 获取配置参数
        freeze_days = strategy_settings['daily_data_requirements']['freeze_period_days']
        
        # 分割数据
        freeze_records = daily_records[-freeze_days:]  # 最近200个交易日（冻结期）
        history_records = daily_records[:-freeze_days]  # 之前的数据（历史期）

        return freeze_records, history_records


    @staticmethod
    def find_low_points(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        low_points = []
        
        # 检查数据是否为空
        if not records:
            return low_points
            
        target_years = strategy_settings['daily_data_requirements']['low_points_ref_years']
        date_of_today = records[-1]['date']
        
        # 解析今天的日期
        from datetime import datetime, timedelta
        today = datetime.strptime(date_of_today, '%Y%m%d')
        
        for years_back in target_years:
            # 计算时间区间的开始日期（往前推years_back年）
            start_date = today - timedelta(days=years_back * 365)
            start_date_str = start_date.strftime('%Y%m%d')
            
            # 找到该时间区间内的所有记录
            period_records = [record for record in records 
                            if record['date'] >= start_date_str and record['date'] < date_of_today]
            
            if not period_records:
                continue
                
            # 找到该时间区间内的最低价格
            min_record = min(period_records, key=lambda x: float(x['close']))
            
            low_points.append(HistoricLowEntity.to_low_point(years_back, min_record))
        
        return low_points

    @staticmethod
    def find_opportunity_from_low_points(stock: Dict[str, Any], low_points: List[Dict[str, Any]], freeze_data: List[Dict[str, Any]], history_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """从历史低点寻找投资机会"""
        record_of_today = freeze_data[-1]

        # 检查当前价格是否在投资范围内
        for low_point in low_points:
            if HistoricLowService.is_in_invest_range(record_of_today, low_point, freeze_data):
                # logger.info(f"股票 {stock['id']} 历史低点 {low_point['date']} 在投资范围内")
                if (HistoricLowService.has_no_new_low_during_freeze(freeze_data)
                    and HistoricLowService.is_amplitude_sufficient(freeze_data)
                    and HistoricLowService.is_slope_sufficient(freeze_data)
                    and HistoricLowService.is_out_of_continuous_limit_down(freeze_data)
                    # and HistoricLowService.is_wave_completed(freeze_data + history_data, low_point)
                ):
                    # logger.info(f"且没有出现新低，且振幅足够，且斜率足够，且不在连续跌停，且波段完成")
                    opportunity = HistoricLowEntity.to_opportunity(stock, record_of_today, low_point)
                    return opportunity

        return None

    


    # ========================================================
    # Simulation:
    # ========================================================

    @staticmethod
    def simulate_single_day(stock_id: str, current_date: str, current_record: Dict[str, Any], 
                           all_data: List[Dict[str, Any]], current_investment: Optional[Dict[str, Any]], settings: Dict[str, Any]) -> Dict[str, Any]:

        """
        模拟单日交易逻辑
        
        Args:
            stock_id: 股票ID
            current_date: 当前日期
            current_record: 当前日K线数据
            all_data: 所有数据（包含当前日及之前的所有数据）
            current_investment: 当前投资状态
            
        Returns:
            Dict[str, Any]: 包含以下字段的结果
                - new_investment: 新的投资（如果有）
                - settled_investments: 结算的投资列表
                - current_investment: 更新后的当前投资状态
        """

        
        new_investment = None
        settled_investments = []
        
        # 如果有投资，先检查是否需要结算
        if current_investment:
            # 更新投资的最大最小值跟踪
            HistoricLowStrategy._update_investment_tracking(current_investment, current_record)
            
            # 检查止盈止损目标
            should_settle, updated_investment = HistoricLowStrategy._check_investment_targets(current_investment, current_record)
            
            if should_settle:
                # 结算投资
                HistoricLowStrategy._settle_investment(updated_investment)
                settled_investments.append(updated_investment)
                
                # 显示投资结果（模拟原HL simulator的行为）
                result = updated_investment.get('result', 'unknown')
                profit_rate = updated_investment.get('overall_profit_rate', 0) * 100
                duration_days = updated_investment.get('invest_duration_days', 0)
                
                if result == 'win':
                    if profit_rate >= 20:
                        result_dot = "🟢"
                        result_text = "盈利"
                    else:
                        result_dot = "🟡"
                        result_text = "微盈"
                elif result == 'loss':
                    if profit_rate > -20:
                        result_dot = "🟠"
                        result_text = "微损"
                    else:
                        result_dot = "🔴"
                        result_text = "亏损"
                else:
                    result_dot = "⚪️"
                    result_text = "平仓"
                
                logger.info(f"🔍 投资结束: {stock_id} {result_dot} {result_text} | 收益率: {profit_rate:+.2f}% | 时长: {duration_days}天")
                
                current_investment = None  # 清空当前投资
            else:
                current_investment = updated_investment
        
        # 如果没有当前投资，尝试扫描机会
        if current_investment is None:
            # 检查数据是否足够
            min_required_daily_records = strategy_settings['daily_data_requirements']['min_required_daily_records']
            if len(all_data) >= min_required_daily_records:
                # 构建股票信息
                stock_info = {'id': stock_id}
                # 直接使用所有数据进行扫描（包含当前日）
                opportunity = HistoricLowStrategy.scan_single_stock(stock_info, all_data)
                if opportunity:
                    # 创建投资
                    new_investment = HistoricLowEntity.to_investment(opportunity)
                    if new_investment:
                        new_investment['start_date'] = current_date
        
        # 如果有新投资，更新当前投资状态
        if new_investment:
            current_investment = new_investment
        
        return {
            'new_investment': new_investment,
            'settled_investments': settled_investments,
            'current_investment': current_investment
        }
    
    @staticmethod
    def _update_investment_tracking(investment: Dict[str, Any], current_record: Dict[str, Any]) -> None:
        """更新投资的最大最小值跟踪"""
        current_price = current_record['close']
        tracking = investment['tracking']
        
        # 更新最大价格
        if current_price > tracking['max_close_reached']['price']:
            tracking['max_close_reached']['price'] = current_price
            tracking['max_close_reached']['date'] = current_record['date']
            tracking['max_close_reached']['ratio'] = (current_price - investment['purchase_price']) / investment['purchase_price']
        
        # 更新最小价格
        if current_price < tracking['min_close_reached']['price'] or tracking['min_close_reached']['price'] == 0:
            tracking['min_close_reached']['price'] = current_price
            tracking['min_close_reached']['date'] = current_record['date']
            tracking['min_close_reached']['ratio'] = (current_price - investment['purchase_price']) / investment['purchase_price']
    
    @staticmethod
    def _check_investment_targets(investment: Dict[str, Any], current_record: Dict[str, Any]) -> tuple:
        """检查投资目标，返回是否需要结算和更新后的投资"""
        from .strategy_simulator import HLSimulator
        return HLSimulator.check_targets(investment, current_record)
    
    @staticmethod
    def _settle_investment(investment: Dict[str, Any]) -> None:
        """结算投资"""
        from .strategy_simulator import HLSimulator
        HLSimulator.settle_investment(investment)
    
    @staticmethod
    def summarize_single_stock(result: Dict[str, Any]) -> Dict[str, Any]:
        """
        单股票汇总 - 从备份版本迁移
        
        Args:
            result: 单股票模拟结果
            
        Returns:
            Dict: 单股票汇总信息
        """
        stock_id = result.get('stock_id', 'unknown')
        investments = result.get('investments', [])
        settled_investments = result.get('settled_investments', [])
        
        
        # 统计投资数据
        total_investments = len(settled_investments)  # 只统计已结算的投资
        success_count = 0
        fail_count = 0
        open_count = len(investments)  # 未结算的投资
        total_profit = 0.0
        total_duration_days = 0
        total_roi = 0.0
        total_annual_return = 0.0
        
        # 处理已结算的投资
        for investment in settled_investments:
            result_type = investment.get('result', '')
            if result_type == 'win':
                success_count += 1
            elif result_type == 'loss':
                fail_count += 1
            
            # 累计收益和持续时间
            total_profit += investment.get('overall_profit', 0.0)
            total_duration_days += investment.get('invest_duration_days', 0)
            total_roi += investment.get('overall_profit_rate', 0.0)
            
            # 计算年化收益率
            duration_days = investment.get('invest_duration_days', 1)
            profit_rate = investment.get('overall_profit_rate', 0.0)
            # TODO: 实现年化收益率计算
            annual_return = profit_rate * 365 / duration_days if duration_days > 0 else 0.0
            total_annual_return += annual_return
        
        # 计算平均值
        avg_profit = total_profit / total_investments if total_investments > 0 else 0.0
        avg_duration_days = total_duration_days / total_investments if total_investments > 0 else 0.0
        avg_roi = (total_roi / total_investments * 100) if total_investments > 0 else 0.0
        avg_annual_return = total_annual_return / total_investments if total_investments > 0 else 0.0
        
        # 计算胜率
        settled_count = success_count + fail_count
        win_rate = (success_count / settled_count * 100) if settled_count > 0 else 0.0
        
        return {
            'total_investments': total_investments,
            'success_count': success_count,
            'fail_count': fail_count,
            'open_count': open_count,
            'win_rate': round(win_rate, 1),
            'total_profit': round(total_profit, 2),
            'avg_profit': round(avg_profit, 2),
            'avg_duration_days': round(avg_duration_days, 1),
            'avg_roi': round(avg_roi, 2),
            'avg_annual_return': round(avg_annual_return, 2),
            'investments': settled_investments  # 包含所有投资记录，供to_session_summary使用
        }
    
    @staticmethod
    def summarize_session(stock_summaries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        会话汇总 - 使用原来的HistoricLowEntity.to_session_summary逻辑
        
        Args:
            stock_summaries: 股票汇总列表
            
        Returns:
            Dict: 会话汇总信息
        """
        from .strategy_entity import HistoricLowEntity
        
        # 构建session_results格式
        session_results = []
        for stock_summary in stock_summaries:
            session_results.append({
                'investments': stock_summary.get('summary', {}).get('investments', [])
            })
        
        return HistoricLowEntity.to_session_summary(session_results)
    
    @staticmethod
    def present_final_report(final_report: Dict[str, Any]) -> None:
        """
        呈现最终报告 - 使用原来的HL simulator格式
        
        Args:
            final_report: 最终报告
        """
        session_summary = final_report.get('session_summary', {})
        
        print("\n" + "="*60)
        print("📊 HistoricLow 策略回测结果汇总")
        print("="*60)
        
        # 显示投资结果统计
        if session_summary:
            win_rate = session_summary.get('win_rate', 0)
            annual_return = session_summary.get('annual_return', 0)
            
            # 使用绿色点显示胜率（胜率超过60%显示绿色）
            win_rate_dot = "🟢" if win_rate >= 60 else "🔴"
            print(f"🎯 胜率: {win_rate_dot} {win_rate}%")
            
            # 使用绿色点显示年化收益率（年化收益率超过10%显示绿色）
            annual_return_dot = "🟢" if annual_return >= 15 else "🔴"
            print(f"📈 平均年化收益率: {annual_return_dot} {annual_return}%")
            
            print(f"⏱️  平均投资时长: {session_summary.get('avg_duration_days', 0)} 天")
            print(f"💰 平均ROI: {session_summary.get('avg_roi', 0)}%")
            
            # 添加投资数量统计
            print(f"📊 总投资次数: {session_summary.get('total_investments', 0)}")
            print(f"✅ 成功次数: {session_summary.get('win_count', 0)}")
            print(f"❌ 失败次数: {session_summary.get('loss_count', 0)}")

            print("<------------------------------------------->")
            
            # 添加颜色点统计
            green_count = session_summary.get('green_dot_count', 0)
            yellow_count = session_summary.get('yellow_dot_count', 0)
            orange_count = session_summary.get('orange_dot_count', 0)
            red_count = session_summary.get('red_dot_count', 0)
            green_rate = session_summary.get('green_dot_rate', 0)
            yellow_rate = session_summary.get('yellow_dot_rate', 0)
            orange_rate = session_summary.get('orange_dot_rate', 0)
            red_rate = session_summary.get('red_dot_rate', 0)
            
            print(f"🟢 盈利次数: {green_count} ({green_rate}%)")
            print(f"🟡 微盈次数: {yellow_count} ({yellow_rate}%)")
            print(f"🟠 微损次数: {orange_count} ({orange_rate}%)")
            print(f"🔴 亏损次数: {red_count} ({red_rate}%)")
        else:
            print("📊 投资结果统计: 暂无数据")
        
        print("="*60)
    
    def report(self, opportunities: List[Dict[str, Any]]) -> None:
        reports = self.to_presentable_report(opportunities)
        
        print("\n📊 HistoricLow 策略投资报告")
        print("=" * 60)
        
        self.print_investment_operations()
        for report in reports:
            self.present_report(report)




    # ========================================================
    # Result presentation:
    # ========================================================

    def to_presentable_report(self, opportunities: List[Dict[str, Any]]) -> None:
        """
        将投资机会转换为可呈现的报告格式
        
        Args:
            opportunities: 投资机会列表
        """
        from .strategy_settings import strategy_settings
        
        # 获取黑名单
        blacklist = set(strategy_settings['problematic_stocks']['list'])
        
        # 遍历机会并添加模拟结果信息
        for opportunity in opportunities:
            stock_id = opportunity.get('stock', {}).get('id', '')
            
            # 检查是否在黑名单中
            opportunity['is_in_blacklist'] = stock_id in blacklist
            
            # 获取该股票的完整模拟结果数据
            stock_data = self.invest_recorder.get_stock_data(stock_id)
            
            if stock_data:
                # 将模拟结果summary附加到机会上
                opportunity['simulation_summary'] = stock_data.get('summary', {})
                # 将投资记录附加到机会上
                opportunity['investments'] = stock_data.get('investments', [])
            else:
                opportunity['simulation_summary'] = None
                opportunity['investments'] = []

        return opportunities

    def print_investment_operations(self) -> None:
        """
        打印投资操作说明，从settings中动态获取策略信息
        """
        goal_settings = strategy_settings.get('goal', {})
        stop_loss_settings = goal_settings.get('stop_loss', {})
        take_profit_settings = goal_settings.get('take_profit', {})
        
        print(f"📍 投资策略说明:")
        
        # 初始止损
        loss20_stage = stop_loss_settings.get('stages', [{}])[0]
        loss20_ratio = loss20_stage.get('ratio', -0.2) * 100
        print(f"   1. 初始投资止损: {loss20_ratio:.0f}%")
        
        # 止盈阶段
        take_profit_stages = take_profit_settings.get('stages', [])
        for i, stage in enumerate(take_profit_stages, 2):
            stage_name = stage.get('name', '')
            ratio = stage.get('ratio', 0) * 100
            sell_ratio = stage.get('sell_ratio', 0) * 100
            set_stop_loss = stage.get('set_stop_loss', '')
            
            if stage_name == 'win10%':
                print(f"   {i}. 盈利{ratio:.0f}%后: 卖出{sell_ratio:.0f}%仓位，止损调整为买入价格(保本)")
            elif stage_name == 'win20%':
                print(f"   {i}. 盈利{ratio:.0f}%后: 卖出{sell_ratio:.0f}%仓位")
            elif stage_name == 'win30%':
                print(f"   {i}. 盈利{ratio:.0f}%后: 卖出{sell_ratio:.0f}%仓位")
            elif stage_name == 'win40%':
                print(f"   {i}. 盈利{ratio:.0f}%后: 卖出{sell_ratio:.0f}%仓位，启动动态止损")
        
        # 动态止损说明
        dynamic_stop_loss = stop_loss_settings.get('dynamic', {})
        dynamic_ratio = dynamic_stop_loss.get('ratio', -0.1) * 100
        print(f"   6. 动态止损: 止损位置为之后日线出现过的最高值的下方{abs(dynamic_ratio):.0f}%")
        print("============================================================")

    

    def present_report(self, report: Dict[str, Any]) -> None:
        """
        呈现投资报告
        
        Args:
            report: 单个投资机会报告
        """
        # 获取股票基本信息
        stock = report.get('stock', {})
        stock_id = stock.get('id', '')
        stock_name = stock.get('name', '')
        current_close = report.get('price', 0)  # 从opportunity的price字段获取收盘价
        
        # 获取低点参考信息
        low_point_ref = report.get('low_point_ref', {})
        low_point_price = low_point_ref.get('low_point_price', 0)
        invest_upper_bound = low_point_ref.get('invest_upper_bound', 0)
        invest_lower_bound = low_point_ref.get('invest_lower_bound', 0)
        
        # 获取模拟结果
        simulation_summary = report.get('simulation_summary', {})
        
        # 检查收盘价数据
        if current_close <= 0:
            print(f"\n📈 股票: {stock_id} - {stock_name}")
            print(f"💰 最新收盘价: {current_close:.2f} (数据异常)")
            print("⚠️  收盘价数据异常，无法进行投资分析")
            return
        
        # 计算当前价格在参考区间的百分比位置和投资建议
        investment_comment = ""
        if invest_upper_bound > invest_lower_bound > 0:
            price_position = ((current_close - invest_lower_bound) / (invest_upper_bound - invest_lower_bound)) * 100
            
            # 判断投资时机
            if price_position < 33:
                investment_comment = "当前买入成本较低，是投资的好机会"
            elif price_position > 66:
                investment_comment = "当前买入成本较高，可能会削弱盈利，谨慎投资"
            else:
                investment_comment = "当前买入成本适中，是投资机会"
        else:
            investment_comment = "投资参考区间数据异常"
        
        # 检查是否在黑名单中
        blacklist_status = ""
        if report.get('is_in_blacklist', False):
            blacklist_status = "此股票在当前策略的黑名单中，强烈建议谨慎投资！"
        else:
            blacklist_status = "此股票不在当前策略的黑名单中，可以考虑投资。"
        
        # 显示股票信息和结论
        print(f"📍 建议:")
        print(f"      - {blacklist_status}")
        print(f"      - {investment_comment}")
        
        # 显示详细数据
        print(f"\n📈 股票: {stock_id} - {stock_name}")
        print(f"💰 最新收盘价: {current_close:.2f}")
        
        # 获取期数信息
        term = low_point_ref.get('term', 0)
        print(f"📍 历史低点: {low_point_price:.2f} （{term}年期）")
        print(f"📍 投资参考区间: {invest_lower_bound:.2f} - {invest_upper_bound:.2f}")
        
        if invest_upper_bound > invest_lower_bound > 0:
            print(f"📍 当前价格位置: {price_position:.1f}%")
        else:
            print("📍 投资参考区间: 数据异常")
        
        # 呈现模拟结果
        if simulation_summary:
            total_investments = simulation_summary.get('total_investments', 0)
            success_count = simulation_summary.get('success_count', 0)
            fail_count = simulation_summary.get('fail_count', 0)
            open_count = simulation_summary.get('open_count', 0)
            win_rate = simulation_summary.get('win_rate', 0)
            avg_duration_days = simulation_summary.get('avg_duration_days', 0)
            avg_roi = simulation_summary.get('avg_roi', 0)
            avg_annual_return = simulation_summary.get('avg_annual_return', 0)
            
            print(f"\n📊 历史模拟结果:")
            print(f"   📈 总投资次数: {total_investments}")
            print(f"   ✅ 成功次数: {success_count}")
            print(f"   ❌ 失败次数: {fail_count}")
            print(f"   ⏳ 未结束次数: {open_count}")
            print(f"   🎯 投资成功率: {win_rate:.1f}%")
            print(f"   ⏰ 平均投资时间: {avg_duration_days:.1f}天")
            print(f"   💰 平均投资收益: {avg_roi:.2f}%")
            print(f"   📅 平均年化收益: {avg_annual_return:.2f}%")
            
            # 计算盈利分布 - 从investments中统计
            investments = report.get('investments', [])
            if investments:
                green_count = 0    # 盈利 > 20%
                yellow_count = 0  # 微盈 0-20%
                orange_count = 0  # 微损 -20% to 0
                red_count = 0     # 亏损 < -20%
                
                for investment in investments:
                    overall_profit = investment.get('overall_profit', 0)
                    purchase_price = investment.get('purchase_price', 0)
                    
                    if purchase_price > 0:
                        profit_rate = (overall_profit / purchase_price) * 100
                        
                        if profit_rate > 20:
                            green_count += 1
                        elif profit_rate >= 0:
                            yellow_count += 1
                        elif profit_rate > -20:
                            orange_count += 1
                        else:
                            red_count += 1
                
                if total_investments > 0:
                    green_rate = (green_count / total_investments) * 100
                    yellow_rate = (yellow_count / total_investments) * 100
                    orange_rate = (orange_count / total_investments) * 100
                    red_rate = (red_count / total_investments) * 100
                    
                    print(f"\n🎨 投资结果分布:")
                    print(f"   🟢 盈利(>20%): {green_count}次 ({green_rate:.1f}%)")
                    print(f"   🟡 微盈(0-20%): {yellow_count}次 ({yellow_rate:.1f}%)")
                    print(f"   🟠 微损(-20%-0%): {orange_count}次 ({orange_rate:.1f}%)")
                    print(f"   🔴 亏损(<-20%): {red_count}次 ({red_rate:.1f}%)")
                else:
                    print(f"\n🎨 投资结果分布: 无投资记录")
            else:
                print(f"\n🎨 投资结果分布: 无投资记录")
        else:
            print("\n📊 历史模拟结果: 无数据")
        
        print("-" * 60)
       
    # ========================================================
    # Workers:
    # ========================================================

    def _scan_stocks_with_worker(self, stock_idx: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        opportunities = []
        
        # 使用单线程处理，避免数据库连接冲突
        total_stocks = len(stock_idx)
        logger.info(f"开始扫描 {total_stocks} 只股票...")
        
        start_time = time.time()

        for i, stock in enumerate(stock_idx, 1):
            try:
                # 直接调用原有的扫描方法
                opportunity = self.scan_opportunity_job_for_single_stock(stock)
                progress = (i / total_stocks * 100)
                if opportunity:
                    opportunities.extend(opportunity)
                    logger.info(f"🔍 扫描股票 {stock['id']} {stock['name']} - ✅ 发现投资机会 {i}/{total_stocks} ({progress:.1f}%)")
                else:
                    logger.info(f"🔍 扫描股票 {stock['id']} {stock['name']} - 没有投资机会 {i}/{total_stocks} ({progress:.1f}%)")
                    
            except Exception as e:
                logger.error(f"扫描股票 {stock['id']} 失败: {e}")
                continue
        
        logger.info(f"✅ 股票扫描完成: 共扫描 {total_stocks} 只股票，发现 {len(opportunities)} 个投资机会, 共耗时 {time.time() - start_time:.2f} 秒")
        return opportunities

    def scan_opportunity_job_for_single_stock(self, stock: Dict[str, Any]) -> List[Dict[str, Any]]:
        """扫描单只股票的投资机会"""
        daily_k_lines_count = self.required_tables["stock_kline"].count("id = %s AND term = %s", (stock['id'], 'daily'))
        min_required_daily_records = self.strategy_settings['daily_data_requirements']['min_required_daily_records']
        
        if daily_k_lines_count < min_required_daily_records:
            return []
        
        formatted_daily_records = self.acquire_qfq_daily_records(stock)

        opportunity = self.scan_single_stock(stock, formatted_daily_records)
        
        # 返回列表格式以保持接口兼容性
        if opportunity:
            return [opportunity]
        else:
            return []
            
    def acquire_qfq_daily_records(self, stock: Dict[str, Any]) -> List[Dict[str, Any]]:
        raw_daily_records = self.required_tables["stock_kline"].get_all_k_lines_by_term(stock['id'], 'daily')
        qfq_factors = self.required_tables["adj_factor"].get_stock_factors(stock['id'])
        qfq_daily_records = DataSourceService.to_qfq(raw_daily_records, qfq_factors)
        daily_records = HistoricLowService.filter_out_negative_records(qfq_daily_records)

        return daily_records