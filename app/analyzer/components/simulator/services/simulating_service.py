#!/usr/bin/env python3
"""
SimulatingService - 多进程模拟服务
"""
from typing import Dict, List, Any, Optional
from loguru import logger
from app.analyzer.analyzer_service import AnalyzerService
from app.analyzer.enums import InvestmentResult
from app.analyzer.components.investment.investment_goal_manager import InvestmentGoalManager
from app.analyzer.components.base_strategy import BaseStrategy
from utils.icon.icon_service import IconService
from utils.worker.multi_process.process_worker import ProcessWorker


class SimulatingService:
    """静态模拟方法，支持多进程"""

    @staticmethod
    def build_jobs(stock_list: List[Dict[str, Any]], strategy_class: Any, settings: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        构建多进程模拟任务 - 基于股票列表的简化版本
        每个进程按需加载K线数据和计算指标，避免内存爆炸
        
        Args:
            stock_list: 股票列表
            settings: 完整的策略设置
            simulate_one_day_func: 子类的单日模拟函数
            
        Returns:
            List[Dict]: 任务列表
        """
        jobs = []

        for i, stock in enumerate(stock_list):
            stock_id = stock['id']
            job = {
                'id': f"stock_{i}_{stock_id}",
                'payload': {
                    'stock': stock,
                    'settings': settings,
                    'strategy_class': strategy_class
                }
            }
            jobs.append(job)
        
        return jobs
    

    

    @staticmethod
    def run_multiprocess_simulation(jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        使用多进程执行模拟任务
        
        Args:
            jobs: 任务列表
            
        Returns:
            List[Dict]: 模拟结果列表
        """
        if not jobs:
            logger.warning(f"{IconService.get('warning')} 没有模拟任务需要执行")
            return []
        
        worker = ProcessWorker(
            job_executor=SimulatingService.single_stock_simulator,
        )
        
        worker.run_jobs(jobs)
        
        # 获取成功的结果
        successful_results = worker.get_successful_results()
        
        # 提取实际的结果数据
        results = []
        for job_result in successful_results:
            if job_result.result:
                results.append(job_result.result)
        
        logger.info(f"{IconService.get('rocket')} 多进程模拟完成，总投资过的股票数: {len(results)}")
        return results
    

    @staticmethod
    def single_stock_simulator(payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        模拟单只股票 - 从配置数据中提取参数
        
        Args:
            payload: 包含股票ID、设置和策略类信息的数据
            
        Returns:
            Dict: 该股票的模拟结果
        """
        try:
            stock = payload['stock']
            settings = payload['settings']
            strategy_class = payload['strategy_class']

            from app.data_loader import DataLoader
            loader = DataLoader()
            data = loader.prepare_data(stock, settings)

            # 执行模拟 - 直接调用子类的simulate_one_day方法
            result = SimulatingService._execute_simulation(
                stock, data, settings, strategy_class
            )

            return result

        except Exception as e:
            logger.exception("❌ 子进程内部异常 | stock_id={} | error={}", stock['id'], str(e))
            return {}

    @staticmethod
    def _execute_simulation(stock_info: Dict[str, Any], required_data: Dict[str, Any], settings: Dict[str, Any], strategy_class: Any) -> Dict[str, Any]:
        """
        使用单日模拟函数执行模拟
        
        Args:
            stock_info: 股票信息
            required_data: 所需数据
            strategy_class: 策略类
            
        Returns:
            Dict: 模拟结果
        """
        # 获取模拟执行周期数据
        simulate_base_term = settings.get('klines', {}).get('simulate_base_term')
        base_records = required_data['klines'][simulate_base_term]

        # 初始化单只股票投资状态
        tracker = {
            'stock': stock_info,
            'passed_dates': [],
            'investing': None,
            'settled': [],
        }

        min_required_kline = settings.get('klines').get('min_required_kline', 0)

        # 逐个base term的日期进行模拟
        last_record_of_today: Dict[str, Any] = None
        for i, current_record in enumerate(base_records):
            virtual_date_of_today = current_record['date']
            tracker['passed_dates'].append(virtual_date_of_today)
            
            # 如果未达到最小所需K线数，则跳过
            if len(tracker['passed_dates']) < min_required_kline:
                continue

            data_of_today = SimulatingService.get_data_of_today(virtual_date_of_today, required_data, settings)

            SimulatingService._execute_single_day(tracker, current_record, stock_info, data_of_today, settings, strategy_class)
            last_record_of_today = current_record
        
        # 回测结束清算未结投资
        SimulatingService.settle_open_investment(tracker, last_record_of_today, strategy_class)

        # 清理临时数据
        del tracker['passed_dates']
        del tracker['investing']
        # 清理信号缓存数据
        if '_cached_signal_result' in tracker:
            del tracker['_cached_signal_result']
        if '_last_signal_data_key' in tracker:
            del tracker['_last_signal_data_key']
        # 返回结果

        return tracker

    @staticmethod
    def _get_cached_or_compute_signal(tracker: Dict[str, Any], stock_info: Dict[str, Any], 
                                     required_data: Dict[str, Any], settings: Dict[str, Any], 
                                     strategy_class: Any) -> Optional[Dict[str, Any]]:
        """
        智能信号检测：使用缓存避免重复计算
        
        当信号检测基于较长周期（如周线）时，避免在相同周期内重复计算相同的信号
        """
        # 获取信号检测周期
        signal_term = settings.get('klines', {}).get('signal_base_term', 'daily')
        
        # 获取信号数据
        signal_data = required_data.get('klines', {}).get(signal_term, [])
        
        if not signal_data:
            # 没有信号数据，直接执行信号检测
            return strategy_class.scan_opportunity(stock_info, required_data, settings)
        
        # 检查信号数据是否变化
        if SimulatingService._is_signal_data_unchanged(tracker, signal_data, signal_term):
            # 使用缓存的信号结果
            return tracker.get('_cached_signal_result')
        
        # 信号数据已变化，执行新的信号检测
        opportunity = strategy_class.scan_opportunity(stock_info, required_data, settings)
        
        # 缓存结果
        tracker['_cached_signal_result'] = opportunity
        tracker['_last_signal_data_key'] = SimulatingService._get_signal_data_key(signal_data)
        
        return opportunity

    @staticmethod
    def _is_signal_data_unchanged(tracker: Dict[str, Any], signal_data: List[Dict[str, Any]], 
                                 signal_term: str) -> bool:
        """
        检查信号数据是否未变化
        """
        if not signal_data:
            return False
        
        current_key = SimulatingService._get_signal_data_key(signal_data)
        last_key = tracker.get('_last_signal_data_key')
        
        return current_key == last_key

    @staticmethod
    def _get_signal_data_key(signal_data: List[Dict[str, Any]]) -> tuple:
        """
        生成信号数据的关键标识，用于检测数据变化
        """
        if not signal_data:
            return None
        
        # 获取最新信号数据的关键字段
        latest_signal = signal_data[-1]
        signal_key = (
            latest_signal.get('date'),
            latest_signal.get('close'),
            latest_signal.get('volume'),
            latest_signal.get('amount'),
            latest_signal.get('ma5'),
            latest_signal.get('ma10'),
            latest_signal.get('ma20'),
            latest_signal.get('ma60'),
            latest_signal.get('rsi'),
        )
        
        return signal_key

    @staticmethod
    def _execute_single_day(tracker: Dict[str, Any], record_of_today: str, stock_info: Dict[str, Any], required_data: Dict[str, Any], settings: Dict[str, Any], strategy_class: Any) -> None:
        investment = tracker['investing']

        if investment:

            SimulatingService.update_investment_max_min_close(investment, record_of_today)

            is_settled, settled_investment = InvestmentGoalManager.is_investment_settled(record_of_today, investment, required_data, settings, strategy_class)

            if is_settled:
                # settled_investment = BaseStrategy.to_settled_investment(investment)
                tracker['settled'].append(settled_investment)
                tracker['investing'] = None

        else:
            # 智能信号检测：使用缓存避免重复计算
            opportunity = SimulatingService._get_cached_or_compute_signal(
                tracker, stock_info, required_data, settings, strategy_class
            )
            if opportunity:
                # 使用 BaseStrategy 统一构建投资实体
                investment = BaseStrategy.create_investment(record_of_today, opportunity, settings)
                # 开仓当日即刻初始化 tracking（计入第一天）
                SimulatingService.update_investment_max_min_close(investment, record_of_today)
                tracker['investing'] = investment


            # 检查是否有细粒度的customized
            # is_customized_stop_loss = BaseStrategy.is_customized_stop_loss(settings)
            # is_customized_take_profit = BaseStrategy.is_customized_take_profit(settings)

            
            # if is_customized_stop_loss or is_customized_take_profit:
            #     # 细粒度customized - 先检查传统目标，再检查customized目标, customized goal will be passed to process in check targets
            #     is_settled, investment = InvestmentGoalManager.check_targets(investment, record_of_today, strategy_class)
                
            #     # 如果传统目标没有触发，检查customized目标
            #     if not is_settled and investment.get('targets_tracking', {}).get('investment_ratio_left', 0) > 0:
            #         # 检查customized止盈 — 由策略自行定义
            #         if is_customized_take_profit:
            #             is_take_profit, investment = strategy_class.should_take_profit(
            #                 stock_info, record_of_today, investment, required_data, settings
            #             )
            #             if is_take_profit:
            #                 is_settled = True
                    
            #         # 检查customized止损 — 由策略自行定义
            #         if not is_settled and is_customized_stop_loss:
            #             is_stop_loss, investment = strategy_class.should_stop_loss(
            #                 stock_info, record_of_today, investment, required_data, settings
            #             )
            #             if is_stop_loss:
            #                 is_settled = True
            # else:
            #     # 传统目标检查
            #     # InvestmentGoalManager.check_targets(investment, record_of_today, strategy_class)
            




        



    @staticmethod
    def get_data_of_today(date_of_today: str, all_data: Dict[str, Any], settings: Dict[str, Any]) -> Dict[str, Any]:
        """
        增量式获取指定日期（含）前的数据，仅对有时间效应的键进行分发。
        - 有时间效应的键来自 settings['klines']['terms']（如 ['daily','weekly',...]）。
        - 在 all_data 内部维护一个隐藏状态 all_data['__state__']：{ term: { 'cursor': int, 'acc': list } }
        - 每次调用仅将新增（date <= date_of_today）的记录 append 到 acc，避免切片复制
        - 返回仅包含这些 term 的字典；若 term 不存在或无数据则返回空列表
        """
        # 读取需要分发的时间序列键（klines）
        kl_cfg = settings.get('klines', {}) if isinstance(settings, dict) else {}
        terms = kl_cfg.get('terms', []) or []
        if not isinstance(terms, list):
            terms = []
        
        # 预留状态容器，存放每个周期的游标与已累积数据
        state = all_data.get('__state__')
        if state is None or not isinstance(state, dict):
            state = {}
            all_data['__state__'] = state
        
        result: Dict[str, Any] = {}
        for term in terms:
            records = (all_data.get('klines') or {}).get(term)
            if not isinstance(records, list) or not records:
                st = state.get(term)
                if st is None:
                    st = {'cursor': -1, 'acc': []}
                    state[term] = st
                result[term] = st['acc']
                continue
            
            st = state.get(term)
            if st is None:
                st = {'cursor': -1, 'acc': []}
                state[term] = st
            
            cursor = st['cursor']
            acc = st['acc']
            
            i = cursor + 1
            n = len(records)
            while i < n:
                rec = records[i]
                d = rec.get('date') if isinstance(rec, dict) else None
                if not d or d > date_of_today:
                    break
                acc.append(rec)
                i += 1
            st['cursor'] = i - 1
            result[term] = acc
        
        data_today: Dict[str, Any] = { 'klines': result }

        # 可选：指数指标（以 categories 列表为键）
        idx_cfg = settings.get('index_indicators') or {}
        idx_cats = idx_cfg.get('categories') if isinstance(idx_cfg, dict) else None
        if isinstance(idx_cats, list) and len(idx_cats) > 0 and isinstance(all_data.get('index_indicators'), dict):
            if '__state__' not in all_data:
                all_data['__state__'] = {}
            idx_state = all_data['__state__'].setdefault('index_indicators', {})
            idx_today = {}
            for cat in idx_cats:
                series = (all_data['index_indicators'] or {}).get(cat) or []
                st = idx_state.get(cat)
                if st is None:
                    st = {'cursor': -1, 'acc': []}
                    idx_state[cat] = st
                i = st['cursor'] + 1
                acc = st['acc']
                n = len(series)
                while i < n:
                    rec = series[i]
                    d = rec.get('date') if isinstance(rec, dict) else None
                    if not d or d > date_of_today:
                        break
                    acc.append(rec)
                    i += 1
                st['cursor'] = i - 1
                idx_today[cat] = acc
            data_today['index_indicators'] = idx_today

        # 可选：行业资金流（全部一组，键'all'）
        icf_cfg = settings.get('industry_capital_flow') or {}
        if isinstance(icf_cfg, dict) and all_data.get('industry_capital_flow'):
            icf_series = (all_data['industry_capital_flow'] or {}).get('all') or []
            icf_state = all_data['__state__'].setdefault('industry_capital_flow', {'cursor': -1, 'acc': []})
            i = icf_state['cursor'] + 1
            acc = icf_state['acc']
            n = len(icf_series)
            while i < n:
                rec = icf_series[i]
                d = rec.get('date') if isinstance(rec, dict) else None
                if not d or d > date_of_today:
                    break
                acc.append(rec)
                i += 1
            icf_state['cursor'] = i - 1
            data_today['industry_capital_flow'] = acc

        # 可选：公司财务（分组类别）
        cf_cfg = settings.get('corporate_finance') or {}
        cf_cats = cf_cfg.get('categories') if isinstance(cf_cfg, dict) else None
        if isinstance(cf_cats, list) and len(cf_cats) > 0 and isinstance(all_data.get('corporate_finance'), dict):
            cf_state = all_data['__state__'].setdefault('corporate_finance', {})
            cf_today = {}
            for cat in cf_cats:
                series = (all_data['corporate_finance'] or {}).get(cat) or []
                st = cf_state.get(cat)
                if st is None:
                    st = {'cursor': -1, 'acc': []}
                    cf_state[cat] = st
                i = st['cursor'] + 1
                acc = st['acc']
                n = len(series)
                while i < n:
                    rec = series[i]
                    d = rec.get('quarter') or rec.get('date')
                    if not d or d > date_of_today:
                        break
                    acc.append(rec)
                    i += 1
                st['cursor'] = i - 1
                cf_today[cat] = acc
            data_today['corporate_finance'] = cf_today

        # 可选：股票标签（按日期获取当日标签）
        if isinstance(all_data.get('stock_labels'), dict):
            labels_data = all_data['stock_labels']
            
            # 获取排序后的日期列表
            sorted_dates = sorted(labels_data.keys())
            
            # 找到当日或最近的标签（现在所有日期都是YYYYMMDD格式）
            today_labels = []
            for date in sorted_dates:
                if date <= date_of_today:
                    today_labels = labels_data[date]  # 直接返回标签ID列表
                else:
                    break
            
            data_today['labels'] = today_labels

        return data_today

    @staticmethod
    def settle_open_investment(tracker: Dict[str, Any], last_record_of_today: Dict[str, Any], strategy_class: Any) -> None:
        """
        回测结束时清算未结投资：按最后一个交易日价格结算剩余仓位，并转为settled结构。
        """
        if not tracker or not isinstance(tracker.get('investing'), dict) or not isinstance(last_record_of_today, dict):
            return

        inv = tracker['investing']
        remaining = float(inv.get('targets_tracking', {}).get('investment_ratio_left', 0) or 0.0)
        final_close = float(last_record_of_today.get('close') or 0.0)
        final_date = last_record_of_today.get('date')
        purchase_price = float(inv.get('purchase_price') or 0.0)
        if remaining > 0 and final_date:
            # 先更新 tracking，确保最后一天计入最高/最低
            SimulatingService.update_investment_max_min_close(inv, last_record_of_today)
            final_target = {
                'name': 'final_settlement',
                'sell_ratio': remaining,
                'profit': (final_close - purchase_price) * remaining,
                'exit_price': final_close,
                'exit_date': final_date,
                'is_achieved': True,
            }
            inv['targets_tracking']['completed'].append(final_target)
            inv['targets_tracking']['investment_ratio_left'] = 0
            inv['end_date'] = final_date

        settled_investment = BaseStrategy.to_settled_investment(last_record_of_today, inv, is_open=True)
        # expose to strategy class to add any extra fields
        tracker['settled'].append(settled_investment)
        tracker['investing'] = None

    @staticmethod
    def update_investment_max_min_close(investment: Dict[str, Any], record_of_today: Dict[str, Any]) -> None:
        # 更新最高价
        if record_of_today['close'] > investment['amplitude_tracking']['max_close_reached']['price']:
            investment['amplitude_tracking']['max_close_reached']['price'] = record_of_today['close']
            investment['amplitude_tracking']['max_close_reached']['date'] = record_of_today['date']
            investment['amplitude_tracking']['max_close_reached']['ratio'] = (record_of_today['close'] - investment['purchase_price']) / investment['purchase_price']
        
        # 更新最低价
        current_min_price = investment['amplitude_tracking']['min_close_reached']['price']
        if current_min_price == 0 or record_of_today['close'] < current_min_price:
            investment['amplitude_tracking']['min_close_reached']['price'] = record_of_today['close']
            investment['amplitude_tracking']['min_close_reached']['date'] = record_of_today['date']
            investment['amplitude_tracking']['min_close_reached']['ratio'] = (record_of_today['close'] - investment['purchase_price']) / investment['purchase_price']


    # to_settled_investment moved to BaseStrategy