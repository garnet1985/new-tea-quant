#!/usr/bin/env python3
"""
Momentum策略实现
核心思想：基于均线动量，定期调仓，筛选前10%动量股票
"""

from operator import inv
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from loguru import logger
import pandas as pd
import numpy as np
from app.analyzer.components.entity.opportunity import Opportunity

from app.analyzer.components.base_strategy import BaseStrategy
from app.analyzer.components.entity.target import InvestmentTarget


class MomentumStrategy(BaseStrategy):
    """
    Momentum策略：动量投资策略
    
    核心逻辑：
    1. 在每个周期（月/季度/年）的第一天买入
    2. 买入时计算动量 = (MA短期 - MA长期) / MA长期
    3. 在周期最后一天卖出
    4. 后处理时按动能在同一天买入的股票中筛选前10%
    """
    
    def __init__(self, db=None, is_verbose=False, name="Momentum", description="Momentum策略：动量投资策略", key="Momentum"):
        # 先设置version，再调用父类__init__
        self.version = "1.0.0"
        super().__init__(db, is_verbose, name, description, key)
    
    @staticmethod
    def scan_opportunity(stock_info: Dict[str, Any], required_data: Dict[str, Any], settings: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        扫描投资机会 - 周期调仓策略
        
        只在周期第一天买入，在周期最后一天卖出
        
        Args:
            stock_info: 股票信息
            required_data: 所需数据
            settings: 策略设置
            
        Returns:
            Optional[Dict]: 投资机会，包含动量数据
        """
        try:
            # 获取K线数据
            klines = required_data.get('klines').get('daily', [])
            
            # 获取当前日期（最新K线记录的日期）
            current_date_str = klines[-1]['date']
            
            # 获取周期类型
            period_type = settings.get('core', {}).get('rebalance_period', 'quarterly')
            
            # 只在周期第一天买入
            if MomentumStrategy._is_first_day_of_period(current_date_str, period_type):
                # 计算动量
                momentum = MomentumStrategy._calculate_momentum(required_data, settings)
                
                if momentum is None:
                    return None
                
                # 买入并记录动能
                return Opportunity(
                    stock=stock_info,
                    record_of_today=klines[-1],  # 使用最新K线记录
                    extra_fields={
                        'momentum': momentum,
                        'is_momentum_strategy': True,
                        'rebalance_date': current_date_str
                    }
                )
            
            # 其他日子不做任何操作
            # 卖出由goal的take_profit在周期结束时触发
            else:
                return None
                
        except Exception as e:
            logger.error(f"Momentum扫描机会时出错: {e}")
            return None


    @staticmethod
    def create_customized_take_profit_targets(investment: Dict[str, Any], record_of_today: Dict[str, Any], extra_fields: Dict[str, Any]) -> List[Dict[str, Any]]:
        return [
            InvestmentTarget(
                target_type=InvestmentTarget.TargetType.TAKE_PROFIT,
                start_record=record_of_today,
                stage={
                    'name': 'customized_take_profit',
                    'ratio': 0,
                    'close_invest': True,
                },
                extra_fields=extra_fields,
            )
        ]


    @staticmethod
    def is_customized_take_profit_complete(
        investment: Dict[str, Any],
        record_of_today: Dict[str, Any],
        required_data: Dict[str, Any],
        remaining_investment_ratio: float,
        settings: Dict[str, Any],
    ) -> Tuple[bool, float]:
        """
        自定义止盈逻辑 - 在周期结束时卖出
        
        Args:
            investment: 投资对象
            record_of_today: 当前交易日记录
            required_data: 所需数据
            remaining_investment_ratio: 剩余投资比例
            settings: 策略设置
        Returns:
            (是否触发止盈, 更新后的投资对象)
        """
        current_date = record_of_today['date']
        period_type = settings.get('core', {}).get('rebalance_period', 'quarterly')

        if MomentumStrategy._is_last_day_of_period(current_date, period_type):
            # 周期最后一天：卖出所有持仓
            return True, remaining_investment_ratio

        return False, remaining_investment_ratio

            

    # @staticmethod
    # def should_take_profit(stock_info: Dict[str, Any], record_of_today: Dict[str, Any], 
    #                       investment: Dict[str, Any], required_data: Dict[str, Any], 
    #                       settings: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
    #     """
    #     自定义止盈逻辑 - 在周期结束时卖出
        
    #     Args:
    #         stock_info: 股票信息
    #         record_of_today: 当前交易日记录
    #         investment: 投资对象
    #         required_data: 所需数据
    #         settings: 策略设置
            
    #     Returns:
    #         (是否触发止盈, 更新后的投资对象)
    #     """
    #     try:
    #         current_date = record_of_today['date']
    #         current_price = record_of_today['close']

    #         # 获取周期类型
    #         period_type = settings.get('core', {}).get('rebalance_period', 'quarterly')

    #         # 仅在自定义止盈开启时返回 target_info
    #         is_customized_tp = BaseStrategy.is_customized_take_profit(settings)
    #         target_info = None
    #         if is_customized_tp:
    #             target_info = {
    #                 'target_price': current_price,
    #                 'current_price': current_price,
    #             }

    #         if MomentumStrategy._is_last_day_of_period(current_date, period_type):
    #             # 周期最后一天：卖出所有持仓
    #             exit_date = current_date
    #             settled = BaseStrategy.to_settled_investment(
    #                 investment=investment,
    #                 exit_price=current_price,
    #                 exit_date=exit_date,
    #                 sell_ratio=1.0,
    #                 target_info=target_info,
    #                 settings=settings,
    #             )
    #             # 仅在自定义时附带 next_target，便于前端/跟踪器展示
    #             if is_customized_tp and target_info is not None:
    #                 settled['next_target'] = {
    #                     'type': 'take_profit',
    #                     'info': target_info
    #                 }
    #             return True, settled

    #         # 未到周期末：不卖出；仅在自定义时添加 target_info/next_target
    #         investment = dict(investment)
    #         if is_customized_tp and target_info is not None:
    #             investment['target_info'] = target_info
    #             investment['next_target'] = {
    #                 'type': 'take_profit',
    #                 'info': target_info
    #             }
    #         return False, investment

    #     except Exception as e:
    #         logger.error(f"Momentum周期卖出检查出错: {e}")
    #         # 异常路径：仅在自定义止盈开启时补充 target_info
    #         try:
    #             is_customized_tp = BaseStrategy.is_customized_take_profit(settings)
    #         except Exception:
    #             is_customized_tp = False
    #         if not is_customized_tp:
    #             return False, investment
    #         safe_investment = dict(investment)
    #         try:
    #             price_fallback = (
    #                 record_of_today.get('close') if isinstance(record_of_today, dict) else None
    #             ) or safe_investment.get('purchase_price')
    #         except Exception:
    #             price_fallback = safe_investment.get('purchase_price')
    #         if price_fallback is not None:
    #             safe_investment['target_info'] = {
    #                 'target_price': price_fallback,
    #                 'current_price': price_fallback,
    #             }
    #         return False, safe_investment

    @staticmethod
    def _collect_investments_by_date(stock_summaries: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        收集所有投资记录，按调仓日期分组
        
        Args:
            stock_summaries: 所有股票的汇总结果
            
        Returns:
            Dict: {日期: [投资记录列表]}
        """
        investments_by_date = {}
        
        for stock_summary in stock_summaries:
            investments = stock_summary.get('investments', [])
            
            for investment in investments:
                entry_date = investment.get('entry_date') or investment.get('start_date')
                momentum = investment.get('extra_fields', {}).get('momentum')
                
                if entry_date and momentum is not None:
                    if entry_date not in investments_by_date:
                        investments_by_date[entry_date] = []
                    
                    investments_by_date[entry_date].append({
                        'investment': investment,
                        'momentum': momentum,
                        'stock_id': stock_summary.get('stock_id'),
                        'stock_name': stock_summary.get('stock_name')
                    })
        
        return investments_by_date
    
    @staticmethod
    def _calculate_filter_count(total: int, top_percentile: float, top_n_min: int, top_n_max: int) -> int:
        """
        计算筛选数量
        
        Args:
            total: 总投资数
            top_percentile: 顶部百分比
            top_n_min: 最小数量
            top_n_max: 最大数量
            
        Returns:
            int: 筛选数量
        """
        # 1. 按百分比计算
        n_by_percentile = max(1, int(total * top_percentile))
        
        # 2. 应用最小和最大限制
        n_filtered = max(top_n_min, min(top_n_max, n_by_percentile))
        
        # 3. 不能超过实际数量
        n_filtered = min(n_filtered, total)
        
        return n_filtered
    
    @staticmethod
    def _filter_top_momentum_investments(
        investments_by_date: Dict[str, List[Dict[str, Any]]],
        top_percentile: float,
        top_n_max: int,
        top_n_min: int
    ) -> tuple:
        """
        按日期筛选每期的前N只股票
        
        Args:
            investments_by_date: 按日期分组的投资记录
            top_percentile: 顶部百分比
            top_n_max: 最大数量
            top_n_min: 最小数量
            
        Returns:
            Tuple: (筛选后的投资列表, 原始总数, 筛选后总数)
        """
        filtered_investments = []
        total_original = 0
        total_filtered = 0
        
        for date, investments in sorted(investments_by_date.items()):
            total_original += len(investments)
            
            # 按动量排序（降序）
            sorted_investments = sorted(investments, key=lambda x: x['momentum'], reverse=True)
            
            # 计算筛选数量
            n_filtered = MomentumStrategy._calculate_filter_count(
                len(sorted_investments),
                top_percentile,
                top_n_min,
                top_n_max
            )
            
            # 获取前N只
            selected = sorted_investments[:n_filtered]
            total_filtered += len(selected)
            
            logger.info(
                f"📅 {date}: 原始{len(sorted_investments)}只 → 筛选后{len(selected)}只 "
                f"(动量范围: {selected[-1]['momentum']:.4f} ~ {selected[0]['momentum']:.4f})"
            )
            
            # 将选中的investment加入结果
            for item in selected:
                filtered_investments.append(item['investment'])
        
        return filtered_investments, total_original, total_filtered
    
    @staticmethod
    def _rebuild_stock_summaries(
        filtered_investments: List[Dict[str, Any]],
        stock_summaries: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        重建筛选后的股票汇总
        
        Args:
            filtered_investments: 筛选后的投资记录
            stock_summaries: 原始股票汇总
            
        Returns:
            List: 重建后的股票汇总列表
        """
        from app.analyzer.analyzer_service import AnalyzerService
        
        # 将筛选后的投资记录按股票分组
        filtered_investment_by_stock = {}
        
        for item in filtered_investments:
            found = False
            for stock_summary in stock_summaries:
                for inv in stock_summary.get('investments', []):
                    # 通过唯一标识符比较（entry_date或start_date + momentum）
                    item_date = item.get('entry_date') or item.get('start_date')
                    inv_date = inv.get('entry_date') or inv.get('start_date')
                    item_momentum = item.get('extra_fields', {}).get('momentum')
                    inv_momentum = inv.get('extra_fields', {}).get('momentum')
                    
                    if item_date == inv_date and item_momentum == inv_momentum:
                        stock_id = stock_summary.get('stock', {}).get('id')
                        if stock_id not in filtered_investment_by_stock:
                            filtered_investment_by_stock[stock_id] = {
                                'stock': stock_summary.get('stock'),
                                'investments': []
                            }
                        filtered_investment_by_stock[stock_id]['investments'].append(item)
                        found = True
                        break
                if found:
                    break
        
        # 对每个股票重新计算summary
        filtered_stock_summaries = []
        
        for stock_id, stock_data in filtered_investment_by_stock.items():
            investments = stock_data['investments']
            
            # 手动构建summary
            total = len(investments)
            total_win = sum(1 for inv in investments if inv.get('result') == 'win')
            total_loss = sum(1 for inv in investments if inv.get('result') == 'loss')
            total_open = sum(1 for inv in investments if inv.get('result') == 'open')
            
            total_roi = sum(inv.get('overall_profit_rate', 0) for inv in investments)
            total_duration = sum(inv.get('duration_in_days', 0) for inv in investments)
            
            avg_roi = total_roi / total if total > 0 else 0
            avg_duration = total_duration / total if total > 0 else 0
            
            win_rate = AnalyzerService.to_percent(total_win, total)
            annual_return = AnalyzerService.get_annual_return(avg_roi, avg_duration)
            annual_return_in_trading_days = AnalyzerService.get_annual_return(avg_roi, avg_duration, is_trading_days=True)
            
            filtered_summary = {
                'stock': stock_data['stock'],
                'investments': investments,
                'summary': {
                    'total_investments': total,
                    'total_win': total_win,
                    'total_loss': total_loss,
                    'total_open': total_open,
                    'win_rate': win_rate,
                    'avg_roi': avg_roi,
                    'avg_duration_in_days': avg_duration,
                    'annual_return': annual_return,
                    'annual_return_in_trading_days': annual_return_in_trading_days,
                }
            }
            
            filtered_stock_summaries.append(filtered_summary)
        
        return filtered_stock_summaries
    
    @staticmethod
    def _build_custom_session_summary(
        filtered_stock_summaries: List[Dict[str, Any]],
        total_original: int,
        total_filtered: int,
        top_percentile: float,
        top_n_max: int,
        top_n_min: int
    ) -> Dict[str, Any]:
        """
        构建自定义会话汇总
        
        Args:
            filtered_stock_summaries: 筛选后的股票汇总
            total_original: 原始总数
            total_filtered: 筛选后总数
            top_percentile: 顶部百分比
            top_n_max: 最大数量
            top_n_min: 最小数量
            
        Returns:
            Dict: 自定义会话汇总
        """
        from app.analyzer.components.simulator.services.postprocess_service import PostprocessService
        
        # 使用筛选后的数据重新计算session summary
        filtered_session_summary = PostprocessService.summarize_session_by_default_way(filtered_stock_summaries)
        
        # 添加筛选统计信息
        filtered_session_summary['momentum_filter_summary'] = {
            'total_original_investments': total_original,
            'total_filtered_investments': total_filtered,
            'filter_rate': total_filtered / total_original if total_original > 0 else 0,
            'top_percentile': top_percentile,
            'top_n_max': top_n_max,
            'top_n_min': top_n_min,
        }
        
        # 添加自定义模式标记
        filtered_session_summary['is_customized'] = True
        filtered_session_summary['custom_stock_summaries_file'] = '0_stock_summaries_custom.json'
        filtered_session_summary['custom_stock_summaries'] = filtered_stock_summaries
        
        return filtered_session_summary
    
    @staticmethod
    def on_summarize_session(base_session_summary: Dict[str, Any], stock_summaries: List[Dict[str, Any]], settings: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        整个会话汇总 - Momentum策略需要筛选前N只股票
        
        Args:
            base_session_summary: 默认的汇总结果
            stock_summaries: 所有股票的汇总结果
            settings: 策略设置
            
        Returns:
            Dict: 追加到默认session summary的字段
        """
        try:
            # 获取配置
            top_percentile = settings.get('core', {}).get('top_percentile', 0.10)
            top_n_max = settings.get('core', {}).get('top_n_max', 50)
            top_n_min = settings.get('core', {}).get('top_n_min', 1)
            
            logger.info(f"🎯 Momentum策略开始筛选：前{top_percentile*100}%，最少{top_n_min}只，最多{top_n_max}只")
            
            # 1. 收集所有投资记录，按日期分组
            investments_by_date = MomentumStrategy._collect_investments_by_date(stock_summaries)
            logger.info(f"📊 共找到 {len(investments_by_date)} 个调仓日期")
            
            # 2. 按日期筛选每期的前N只股票
            filtered_investments, total_original, total_filtered = MomentumStrategy._filter_top_momentum_investments(
                investments_by_date, top_percentile, top_n_max, top_n_min
            )
            logger.info(f"✅ Momentum筛选完成：原始{total_original}笔 → 筛选后{total_filtered}笔")
            
            # 3. 重建筛选后的股票汇总
            filtered_stock_summaries = MomentumStrategy._rebuild_stock_summaries(filtered_investments, stock_summaries)
            
            # 4. 构建自定义会话汇总
            if len(filtered_stock_summaries) > 0:
                return MomentumStrategy._build_custom_session_summary(
                    filtered_stock_summaries,
                    total_original,
                    total_filtered,
                    top_percentile,
                    top_n_max,
                    top_n_min
                )
            else:
                logger.warning("⚠️ Momentum筛选后没有找到任何投资记录")
                return base_session_summary
            
        except Exception as e:
            logger.error(f"Momentum汇总时出错: {e}")
            import traceback
            traceback.print_exc()
            return {}
    
    @staticmethod
    def present_extra_session_report(session_summary: Dict[str, Any], settings: Dict[str, Any] = None) -> None:
        """
        输出扩展报告 - 显示筛选统计信息
        """
        filter_summary = session_summary.get('momentum_filter_summary')
        if not filter_summary:
            return
        
        print("\n" + "="*60)
        print("🎯 Momentum策略筛选统计")
        print("="*60)
        print(f"📊 原始投资记录: {filter_summary.get('total_original_investments', 0)}笔")
        print(f"✅ 筛选后记录: {filter_summary.get('total_filtered_investments', 0)}笔")
        print(f"📉 筛选率: {filter_summary.get('filter_rate', 0)*100:.1f}%")
        print(f"🎯 筛选策略: 前{filter_summary.get('top_percentile', 0)*100:.0f}%，")
        print(f"   最少{filter_summary.get('top_n_min', 0)}只，最多{filter_summary.get('top_n_max', 0)}只")
        print("="*60)


    @staticmethod
    def _calculate_momentum(required_data: Dict[str, Any], settings: Dict[str, Any]) -> Optional[float]:
        """
        计算动量指标
        
        Args:
            required_data: 所需数据
            settings: 策略设置
            
        Returns:
            Optional[float]: 动量值（百分比），如果无法计算返回None
        """
        try:
            # 获取K线数据
            klines = required_data.get('klines', [])
            
            # 从klines字典中获取日线数据
            if isinstance(klines, dict):
                klines = klines.get('daily', [])
            
            if len(klines) < 60:  # 需要至少60天数据
                return None
            
            # 转换为DataFrame
            df = pd.DataFrame(klines)
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date')
            
            # 获取配置
            short_ma = settings.get('core', {}).get('short_ma', 20)
            long_ma = settings.get('core', {}).get('long_ma', 60)
            
            # 计算均线
            df[f'ma{short_ma}'] = df['close'].rolling(window=short_ma).mean()
            df[f'ma{long_ma}'] = df['close'].rolling(window=long_ma).mean()
            
            # 获取最新数据
            latest = df.iloc[-1]
            ma_short = latest[f'ma{short_ma}']
            ma_long = latest[f'ma{long_ma}']
            
            # 检查数据有效性
            if pd.isna(ma_short) or pd.isna(ma_long) or ma_long == 0:
                return None
            
            # 动量计算：(短期均线 - 长期均线) / 长期均线
            # 只计算上行趋势（短期 > 长期）
            if ma_short > ma_long:
                momentum = (ma_short - ma_long) / ma_long
                return momentum
            else:
                return None  # 下行趋势不计算动量
                
        except Exception as e:
            logger.error(f"计算动量时出错: {e}")
            return None
    
    @staticmethod
    def _is_first_day_of_period(date_str: str, period_type: str) -> bool:
        """
        判断是否是周期的第一天
        
        Args:
            date_str: 日期字符串 (YYYYMMDD)
            period_type: 周期类型 (monthly, quarterly, yearly)
            
        Returns:
            bool: 是否是周期第一天
        """
        try:
            date = datetime.strptime(date_str, '%Y%m%d')
            year, month, day = date.year, date.month, date.day
            
            if period_type == 'monthly':
                # 每个月第一天
                return day == 1
                
            elif period_type == 'quarterly':
                # 每个季度第一天: 1/1, 4/1, 7/1, 10/1
                return day == 1 and month in [1, 4, 7, 10]
                
            elif period_type == 'yearly':
                # 每年第一天
                return day == 1 and month == 1
                
            else:
                return False
                
        except Exception as e:
            logger.error(f"判断周期第一天时出错: {e}")
            return False
    
    @staticmethod
    def _is_last_day_of_period(date_str: str, period_type: str) -> bool:
        """
        判断是否是周期的最后一天
        
        Args:
            date_str: 日期字符串 (YYYYMMDD)
            period_type: 周期类型 (monthly, quarterly, yearly)
            
        Returns:
            bool: 是否是周期最后一天
        """
        try:
            date = datetime.strptime(date_str, '%Y%m%d')
            year, month, day = date.year, date.month, date.day
            
            # 计算下一天
            next_day = date + timedelta(days=1)
            
            if period_type == 'monthly':
                # 下一天是下个月第一天，今天就是本月最后一天
                return next_day.month != month
                
            elif period_type == 'quarterly':
                # 季度最后一天：3/31, 6/30, 9/30, 12/31
                return next_day.month != month and month in [3, 6, 9, 12]
                
            elif period_type == 'yearly':
                # 下一天是下一年的第一天，今天就是本年最后一天
                return next_day.month == 1 and next_day.day == 1
                
            else:
                return False
                
        except Exception as e:
            logger.error(f"判断周期最后一天时出错: {e}")
            return False
