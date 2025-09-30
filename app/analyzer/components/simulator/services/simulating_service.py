#!/usr/bin/env python3
"""
SimulatingService - 多进程模拟服务
"""
from typing import Dict, List, Any
from loguru import logger
from app.analyzer.analyzer_service import AnalyzerService
from app.analyzer.components.enum import InvestmentResult
from app.analyzer.components.investment.investment_goal_manager import InvestmentGoalManager
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

            from app.analyzer.components.data_loader import DataLoader
            data = DataLoader.prepare_data(stock, settings)

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
        # 获取基础K线数据
        simulate_base_term = settings.get('klines').get('base_term')

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

        del tracker['passed_dates']
        del tracker['investing']
        # 返回结果

        return tracker


    @staticmethod
    def _execute_single_day(tracker: Dict[str, Any], record_of_today: str, stock_info: Dict[str, Any], required_data: Dict[str, Any], settings: Dict[str, Any], strategy_class: Any) -> None:
        investment = tracker['investing']

        if investment:
            if settings.get('goal').get('is_customized', False):
                is_settled = strategy_class.should_settle_investment(stock_info, record_of_today, investment, required_data, settings)
            else:
                is_settled, investment = InvestmentGoalManager.check_targets(investment, record_of_today)
            if is_settled:
                settled_investment = SimulatingService.to_settled_investment(investment, strategy_class)
                tracker['settled'].append(settled_investment)
                tracker['investing'] = None
            else:
                SimulatingService.update_investment_max_min_close(investment, record_of_today)
        else:
            opportunity = strategy_class.scan_opportunity(stock_info, required_data, settings)
            if opportunity:
                investment = SimulatingService.to_investment(record_of_today, opportunity, settings)
                # expose to strategy class to add any extra fields
                investment = strategy_class.to_investment(investment)
                tracker['investing'] = investment



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

        return data_today

    @staticmethod
    def to_investment(record_of_today: Dict[str, Any], opportunity: Dict[str, Any], settings: Dict[str, Any]) -> Dict[str, Any]:
        """
        将机会转换为投资
        """
        investment = {
            'stock': opportunity['stock'],
            'opportunity_ref': {
                'date': opportunity['date'],
                'price': opportunity['price'],
                'lower_bound': opportunity['lower_bound'],
                'upper_bound': opportunity['upper_bound'],
            }
        }

        # 只在 opportunity 有 extra_fields 且不为空时才添加
        if 'extra_fields' in opportunity and opportunity['extra_fields']:
            investment['extra_fields'] = opportunity['extra_fields']

        # 基础字段
        investment['start_date'] = record_of_today['date']
        investment['purchase_price'] = record_of_today['close']

        # 目标结构（基于 settings['goal']）
        goal_cfg = settings.get('goal', {}) if isinstance(settings, dict) else {}
        targets = InvestmentGoalManager(goal_cfg).create_investment_targets()
        investment['targets'] = targets

        investment['tracking'] = {
            'max_close_reached': { 'price': 0, 'date': '', 'ratio': 0 },
            'min_close_reached': { 'price': 0, 'date': '', 'ratio': 0 },
        }

        return investment


    @staticmethod
    def settle_open_investment(tracker: Dict[str, Any], last_record_of_today: Dict[str, Any], strategy_class: Any) -> None:
        """
        回测结束时清算未结投资：按最后一个交易日价格结算剩余仓位，并转为settled结构。
        """
        if not tracker or not isinstance(tracker.get('investing'), dict) or not isinstance(last_record_of_today, dict):
            return

        inv = tracker['investing']
        remaining = float(inv.get('targets', {}).get('investment_ratio_left', 0) or 0.0)
        final_close = float(last_record_of_today.get('close') or 0.0)
        final_date = last_record_of_today.get('date')
        purchase_price = float(inv.get('purchase_price') or 0.0)
        if remaining > 0 and final_date:
            final_target = {
                'name': 'final_settlement',
                'sell_ratio': remaining,
                'profit': (final_close - purchase_price) * remaining,
                'exit_price': final_close,
                'exit_date': final_date,
                'is_achieved': True,
            }
            inv['targets']['completed'].append(final_target)
            inv['targets']['investment_ratio_left'] = 0
            inv['end_date'] = final_date

        settled_investment = SimulatingService.to_settled_investment(inv, strategy_class, is_open=True)
        # expose to strategy class to add any extra fields
        tracker['settled'].append(settled_investment)
        tracker['investing'] = None

    @staticmethod
    def update_investment_max_min_close(investment: Dict[str, Any], record_of_today: Dict[str, Any]) -> None:
        # 更新最高价
        if record_of_today['close'] > investment['tracking']['max_close_reached']['price']:
            investment['tracking']['max_close_reached']['price'] = record_of_today['close']
            investment['tracking']['max_close_reached']['date'] = record_of_today['date']
            investment['tracking']['max_close_reached']['ratio'] = (record_of_today['close'] - investment['purchase_price']) / investment['purchase_price']
        
        # 更新最低价
        current_min_price = investment['tracking']['min_close_reached']['price']
        if current_min_price == 0 or record_of_today['close'] < current_min_price:
            investment['tracking']['min_close_reached']['price'] = record_of_today['close']
            investment['tracking']['min_close_reached']['date'] = record_of_today['date']
            investment['tracking']['min_close_reached']['ratio'] = (record_of_today['close'] - investment['purchase_price']) / investment['purchase_price']


    @staticmethod
    def to_settled_investment(investment: Dict[str, Any], strategy_class: Any, is_open: bool = False) -> Dict[str, Any]:
        """
        将投资转换为已结算投资
        """
        completed_targets = investment['targets']['completed']
        overall_profit = 0.0

        for target in completed_targets:
            target['weighted_profit'] = target['profit'] * target['sell_ratio']
            target['profit_contribution'] = target['sell_ratio']
            overall_profit += target['weighted_profit']

        icon = "";

        if overall_profit >= 0:
            investment['result'] = InvestmentResult.WIN.value
            icon = IconService.get('check') + ' 投资成功'
        else:
            investment['result'] = InvestmentResult.LOSS.value
            icon = IconService.get('cross') + ' 投资失败'

        if is_open:
            investment['result'] = InvestmentResult.OPEN.value
            icon = IconService.get('ongoing') + ' 投资未完成'

        investment['overall_profit'] = overall_profit
        # ROI 统一使用小数格式存储（如 0.20 = 20%），使用 4 位精度避免小 ROI 被舍入为 0
        investment['overall_profit_rate'] = AnalyzerService.to_ratio(overall_profit, investment['purchase_price'], decimals=4)
        investment['invest_duration_days'] = AnalyzerService.get_duration_in_days(investment['start_date'], investment['end_date'])
        investment['overall_annual_return'] = AnalyzerService.get_annual_return(investment['overall_profit_rate'], investment['invest_duration_days'])

        logger.info(f"{icon}: {investment['stock']['name']} ({investment['stock']['id']}) - ROI: {investment['overall_profit_rate'] * 100:.2f}% in {investment['invest_duration_days']} days")

        return strategy_class.to_settled_investment(investment)