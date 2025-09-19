#!/usr/bin/env python3
"""
SimulatingService - 多进程模拟服务
"""
from typing import Callable, Dict, List, Any, Optional
from loguru import logger
from utils.worker.multi_process.process_worker import ProcessWorker


class SimulatingService:
    """静态模拟方法，支持多进程"""

    @staticmethod
    def build_jobs(stock_list: List[Dict[str, Any]], module_info: Dict[str, Any], settings: Dict[str, Any]) -> List[Dict[str, Any]]:
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
                    'module_info': module_info
                }
            }
            jobs.append(job)
        
        return jobs
    

    

    @staticmethod
    def run_multiprocess_simulation(jobs: List[Dict[str, Any]], module_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        使用多进程执行模拟任务
        
        Args:
            jobs: 任务列表
            
        Returns:
            List[Dict]: 模拟结果列表
        """
        if not jobs:
            logger.warning("⚠️ 没有模拟任务需要执行")
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
        
        logger.info(f"✅ 多进程模拟完成，结果数: {len(results)}")
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
            module_info = payload['module_info']

            from app.analyzer.components.data_loader import DataLoader
            data = DataLoader.load_stock_data_in_child_process(stock['id'], settings)

            # 执行模拟 - 直接调用子类的simulate_one_day方法
            result = SimulatingService._execute_simulation(
                stock, data, settings, module_info
            )

            return result

        except Exception as e:
            logger.exception("❌ 子进程内部异常 | stock_id={} | error={}", stock['id'], str(e))
            return {}

    @staticmethod
    def _execute_simulation(stock_info: Dict[str, Any], required_data: Dict[str, Any], settings: Dict[str, Any], module_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        使用单日模拟函数执行模拟
        
        Args:
            stock_info: 股票信息
            required_data: 所需数据
            module_info: 模块信息
            
        Returns:
            Dict: 模拟结果
        """
        # 获取基础K线数据
        simulate_base_term = settings.get('klines').get('base_term')

        base_records = required_data[simulate_base_term]

        # 初始化投资状态
        tracker = {
            'passed_dates': [],
        }
        
        # current_investment = None
        # settled_investments = []

        min_required_kline = settings.get('klines').get('min_required_kline', 0)

        # 逐个base term的日期进行模拟
        for i, current_record in enumerate(base_records):
            virtual_today = current_record['date']
            tracker['passed_dates'].append(virtual_today)
            
            # 如果未达到最小所需K线数，则跳过
            if len(tracker['passed_dates']) < min_required_kline:
                continue

            data_of_today = SimulatingService.get_data_of_today(virtual_today, required_data, settings)

            SimulatingService._execute_single_day(tracker, stock_info, data_of_today, settings, module_info)
            
        # 返回结果
        return
        return {
            'stock': stock_info,
            'investments': [current_investment] if current_investment else [],
            'settled_investments': settled_investments
        }


    @staticmethod
    def _execute_single_day(tracker: Dict[str, Any], stock_info: Dict[str, Any], required_data: Dict[str, Any], settings: Dict[str, Any], module_info: Dict[str, Any]) -> Dict[str, Any]:
        
        investment = tracker['investing'].get(stock_info['id'], None)

        import importlib
        strategy_class_name = module_info.get('strategy_class_name', '')
        strategy_class = importlib.import_module(strategy_class_name)

        if investment:
            is_settled, settled_investment = SimulatingService.settle_investment(investment, required_data)
            if is_settled:
                settled_investment = strategy_class.to_settled_investment(settled_investment)
                tracker['settled'].append(settled_investment)
                del tracker['investing'][stock_info['id']]
            else:
                SimulatingService.update_investment_max_min_close(settled_investment, required_data)
        else:
            opportunity = strategy_class.scan_single_stock(stock_info, required_data)
            if opportunity:
                investment = SimulatingService.to_investment(opportunity)
                investment = strategy_class.to_investment(investment)
                tracker['investing'][stock_info['id']] = investment
        return tracker;


    @staticmethod
    def get_data_of_today(date_of_today: str, all_data: Dict[str, Any], settings: Dict[str, Any]) -> Dict[str, Any]:
        """
        增量式获取指定日期（含）前的数据，仅对有时间效应的键进行分发。
        - 有时间效应的键来自 settings['klines']['terms']（如 ['daily','weekly',...]）。
        - 在 all_data 内部维护一个隐藏状态 all_data['__state__']：{ term: { 'cursor': int, 'acc': list } }
        - 每次调用仅将新增（date <= date_of_today）的记录 append 到 acc，避免切片复制
        - 返回仅包含这些 term 的字典；若 term 不存在或无数据则返回空列表
        """
        # 读取需要分发的时间序列键
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
            records = all_data.get(term)
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
        
        return result