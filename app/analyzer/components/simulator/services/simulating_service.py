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
    def build_simulation_jobs_from_stock_list(stock_list: List[Dict[str, Any]], 
                                              settings: Dict[str, Any],
                                              simulate_one_day_func) -> List[Dict[str, Any]]:
        """
        构建多进程模拟任务 - 基于股票列表的简化版本
        每个进程按需加载K线数据和计算指标，避免内存爆炸
        
        Args:
            stock_list: 股票列表
            settings: 完整的策略设置
            simulate_one_day_func: 单日模拟函数
            
        Returns:
            List[Dict]: 任务列表
        """
        jobs = []
        
        for i, stock_info in enumerate(stock_list):
            stock_id = stock_info.get('id')
            if not stock_id:
                continue
            
            job = {
                'id': f"stock_{i}_{stock_id}",  # 添加必需的 id 字段
                'data': {  # ProcessWorker 期望的 data 字段
                    'stock_id': stock_id,
                    'settings': settings,
                    'simulate_one_day_func': simulate_one_day_func
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
            logger.warning("⚠️ 没有模拟任务需要执行")
            return []
        
        logger.info(f"🚀 开始多进程模拟，任务数: {len(jobs)}")
        
        worker = ProcessWorker(
            job_executor=SimulatingService.simulate_single_stock_from_config,
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
    def simulate_single_stock_from_config(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        模拟单只股票 - 从配置数据中提取参数
        
        Args:
            data: 包含股票ID、设置和策略类的数据
            
        Returns:
            Dict: 该股票的模拟结果
        """
        try:
            stock_id = data['stock_id']
            settings = data['settings']
            simulate_one_day_func = data['simulate_one_day_func']
            if not callable(simulate_one_day_func) and hasattr(simulate_one_day_func, '__func__'):
                simulate_one_day_func = simulate_one_day_func.__func__
            
            # 加载股票数据
            klines = SimulatingService._load_stock_data(stock_id, settings)
            if not klines:
                return SimulatingService._create_error_result(stock_id, 'No K-line data available')
            
            # 从设置中提取模拟基础周期
            simulation_config = settings.get('simulation', {})
            simulate_base_term = simulation_config.get('simulate_base_term', 'daily')
            
            # 执行模拟
            result = SimulatingService._execute_simulation_with_func(
                stock_id, klines, simulate_one_day_func, simulate_base_term, settings
            )
            
            return result
            
        except Exception as e:
            import traceback
            sid = data.get('stock_id', 'unknown')
            logger.exception("❌ 子进程内部异常 | stock_id={} | error={}", sid, str(e))
            return SimulatingService._create_error_result(sid, str(e))
    
    @staticmethod
    def _execute_simulation_with_func(stock_id: str, klines: Dict[str, Any], 
                                      simulate_one_day_func: Callable, simulate_base_term: str, settings: Dict[str, Any]) -> Dict[str, Any]:
        """
        使用单日模拟函数执行模拟
        
        Args:
            stock_id: 股票ID
            klines: K线数据
            simulate_one_day_func: 单日模拟函数
            simulate_base_term: 模拟基础周期
            
        Returns:
            Dict: 模拟结果
        """
        # 获取基础K线数据
        base_records = klines.get(simulate_base_term, [])
        
        if not base_records:
            return SimulatingService._create_error_result(stock_id, f'No {simulate_base_term} K-line data available')
        
        # 按日期排序
        base_records.sort(key=lambda x: x.get('date', ''))
        
        # 初始化投资状态
        current_investment = None
        settled_investments = []
        
        # 逐日模拟
        for i, current_record in enumerate(base_records):
            current_date = current_record.get('date', '')
            if not current_date:
                continue
            
            # 获取所有数据（包含当前日及之前的所有数据）
            all_data = base_records[:i+1]  # 包含当前记录
            
            # 调用单日模拟函数
            try:
                result = simulate_one_day_func(
                    stock_id, current_date, current_record, all_data, current_investment, settings
                )
                
                # 更新投资状态
                if result.get('new_investment'):
                    current_investment = result['new_investment']
                
                if result.get('settled_investments'):
                    settled_investments.extend(result['settled_investments'])
                    current_investment = result.get('current_investment')
                
            except Exception as e:
                import traceback
                func_name = getattr(simulate_one_day_func, '__name__', str(simulate_one_day_func))
                tb = traceback.format_exc()
                logger.error(
                    "❌ 单日模拟异常 | stock={} | date={} | func={} | record={} | current_investment_keys={} | error={}\n{}",
                    stock_id,
                    current_date,
                    func_name,
                    {k: current_record.get(k) for k in ('date','open','close','high','low','volume') if k in current_record},
                    list(current_investment.keys()) if isinstance(current_investment, dict) else type(current_investment).__name__,
                    str(e),
                    tb,
                )
                continue
        
        # 返回结果
        return {
            'stock_id': stock_id,
            'investments': [current_investment] if current_investment else [],
            'settled_investments': settled_investments
        }
    
    @staticmethod
    def _load_stock_data(stock_id: str, settings: Dict[str, Any]) -> Dict[str, Any]:
        """
        加载股票数据
        
        Args:
            stock_id: 股票ID
            settings: 策略设置
            
        Returns:
            Dict: 按时间周期分组的K线数据，格式为 {'daily': [...], 'weekly': [...]}
        """
        try:
            # 从数据库加载K线数据
            from utils.db.db_manager import DatabaseManager
            
            # 创建数据库连接
            db = DatabaseManager()
            db.initialize()
            
            # 获取K线表实例
            kline_table = db.get_table_instance('stock_kline')
            
            # 从设置中获取日期范围和时间周期（preprocess已验证）
            simulation_config = settings.get('simulation', {})
            start_date = simulation_config['start_date']
            end_date = simulation_config['end_date']
            
            # 获取需要加载的时间周期（从顶层klines配置读取）
            klines_config = settings.get('klines', {})
            terms = klines_config.get('terms', ['daily'])
            
            # 加载所有时间周期的数据
            all_data = {}
            for term in terms:
                # 构建查询条件
                if end_date:
                    # 有结束日期，使用范围查询
                    where_condition = "id = %s AND term = %s AND date >= %s AND date <= %s"
                    params = (stock_id, term, start_date, end_date)
                else:
                    # 没有结束日期，查询到最后
                    where_condition = "id = %s AND term = %s AND date >= %s"
                    params = (stock_id, term, start_date)
                
                # 查询K线数据
                term_data = kline_table.load(
                    condition=where_condition,
                    params=params,
                    order_by='date ASC'
                )
                all_data[term] = term_data
            
            # 返回按时间周期分组的数据
            return all_data
            
        except Exception as e:
            logger.error(f"❌ 加载股票 {stock_id} 数据失败: {e}")
            return {}
    
    @staticmethod
    def _create_error_result(stock_id: str, error_message: str) -> Dict[str, Any]:
        """
        创建错误结果
        
        Args:
            stock_id: 股票ID
            error_message: 错误信息
            
        Returns:
            Dict: 错误结果
        """
        return {
            'stock_id': stock_id,
            'error': error_message,
            'investments': [],
            'settled_investments': []
        }
