#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
基础 Renewer 类
提供所有默认实现，子类可以重写需要的方法
"""

import time
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from loguru import logger
from abc import ABC

from app.data_source.data_source_service import DataSourceService
from utils.worker.multi_thread.futures_worker import FuturesWorker, ExecutionMode
from utils.icon.icon_service import IconService
from app.conf.conf import data_default_start_date


class BaseRenewer(ABC):
    """基础 Renewer 类，提供所有默认实现"""
    
    def __init__(self, db, api, storage, config: Dict[str, Any], is_verbose: bool = False):
        """
        初始化 BaseRenewer
        
        Args:
            db: 数据库管理器
            api: API 接口
            storage: 存储管理器
            config: 配置字典
            is_verbose: 是否详细日志
        """
        self.db = db
        self.api = api
        self.storage = storage
        self.config = config
        self.is_verbose = is_verbose
        
        # 初始化组件（注意顺序：先初始化multithread，因为rate_limiter依赖workers）
        self._init_multithread_config()
        self._init_rate_limiter()

    def _init_multithread_config(self):
        """
        初始化多线程配置
        
        workers默认值：4（可在config['multithread']['workers']中配置）
        """
        self.multithread_config = self.config.get('multithread', {})
        self.workers = self.multithread_config.get('workers', 4)  # 默认4个worker
    
    def _init_rate_limiter(self):
        """
        初始化限流器
        
        Buffer设计原理：
        - 多线程环境：当触发限流时，可能有N个线程的请求正在路上
        - Buffer = workers + 5（激进配置，追求高性能）
        - 简单模式：固定buffer=5（够用即可）
        """
        rate_limit_config = self.config.get('rate_limit')
        if rate_limit_config:
            from .rate_limiter import APIRateLimiter
            
            # 根据运行模式计算buffer
            if self.config.get('job_mode') == 'multithread':
                # 多线程：使用self.workers（已在_init_multithread_config中设置默认值）
                buffer = self.workers + 5
            else:
                # 简单模式：固定buffer
                buffer = 5
            
            self.rate_limiter = APIRateLimiter(
                max_per_minute=rate_limit_config.get('max_per_minute', 200),
                api_name=self.config['table_name'],
                buffer=buffer
            )
        else:
            self.rate_limiter = None
        
    # ==================== 主要入口方法 ====================
    
    def renew(self, latest_market_open_day: str, stock_list: list = None):
        """
        主要更新入口 - 子类通常不需要重写
        
        Args:
            latest_market_open_day: 最新市场开放日
            stock_list: 可选的股票列表（当需要基于股票的更新时传入；宏观无需）
            
        Returns:
            更新结果
        """
        # 判断是否需要更新，并构建任务列表
        jobs = self.should_renew(latest_market_open_day, stock_list)

        if len(jobs) > 0:
            logger.info(f"🔄 开始更新 {self.config['table_name']}，共 {len(jobs)} 个任务")
            
            if self.config['job_mode'].lower() == 'simple':
                return self._simple_renew(jobs)
            elif self.config['job_mode'].lower() == 'multithread':
                return self._multithread_renew(jobs)
            else:
                raise ValueError(f"不支持的作业模式: {self.config['job_mode']}")
        else:
            logger.info(f"⏭️  {self.config['table_name']} 无需更新")

    
    # ==================== 可重写的方法 ====================

    def build_jobs(self, latest_market_open_day: str, stock_list: list = None, db_records: list = None) -> List[Dict]:
        """
        构建任务列表 - 子类可以重写
        
        Args:
            latest_market_open_day: 最新市场开放日
            stock_list: 股票列表（可选，股票相关表需要）
            db_records: 数据库中的最新记录（可选，用于增量更新）
            
        Returns:
            List[Dict]: 任务列表，每个任务包含 start_date, end_date 和主键字段
            
        注意：
            - 子类可以在job中添加 '_log_vars' 字段（字典类型），
              用于为日志模板提供额外的变量（如股票名称、季度、地区等）
            - '_log_vars' 中的所有key-value会直接添加到日志变量中
            - 示例：{'stock_name': '平安银行', 'market': 'SZ'}
            - '_log_vars' 是内部字段，以下划线开头，本身不会暴露给日志变量
        """
        jobs = []
        date_field = self.config['date']['field']
        
        try:
            primary_keys = self.db.get_table_primary_keys(self.config['table_name'])
        except ValueError as e:
            logger.error(f"❌ 构建任务失败: {e}")
            return []
        
        renew_interval = self.config['date']['interval']

        # 场景1: 股票相关数据（K线、财务数据等）
        if stock_list:
            if db_records:
                # 有数据库记录：增量更新
                # 为每个股票检查是否需要更新
                db_records_map = {self._get_record_key(record, primary_keys): record for record in db_records}
                
                for stock in stock_list:
                    stock_key = self._get_record_key(stock, primary_keys)
                    
                    if stock_key in db_records_map:
                        # 股票在数据库中已存在，检查是否需要增量更新
                        latest_record = db_records_map[stock_key]
                        latest_date = latest_record[date_field]
                        
                        if DataSourceService.time_gap_by(renew_interval, latest_date, latest_market_open_day) > 0:
                            # 需要更新
                            job = {
                                'start_date': DataSourceService.to_next(renew_interval, latest_date),
                                'end_date': latest_market_open_day
                            }
                            for primary_key in primary_keys:
                                job[primary_key] = latest_record[primary_key]
                            jobs.append(job)
                    else:
                        # 新股票，从默认日期开始拉取
                        job = {
                            'start_date': data_default_start_date,
                            'end_date': latest_market_open_day
                        }
                        for primary_key in primary_keys:
                            job[primary_key] = stock[primary_key]
                        jobs.append(job)
            else:
                # 数据库无记录：全量拉取
                for stock in stock_list:
                    job = {
                        'start_date': data_default_start_date,
                        'end_date': latest_market_open_day
                    }
                    for primary_key in primary_keys:
                        job[primary_key] = stock[primary_key]
                    jobs.append(job)

        # 场景2: 宏观数据（GDP、利率等）
        else:
            if db_records and len(db_records) > 0:
                # 有数据库记录：增量更新
                latest_record = db_records[-1]
                latest_date = latest_record[date_field]
                
                if DataSourceService.time_gap_by(renew_interval, latest_date, latest_market_open_day) > 0:
                    # 需要更新
                    start_date = DataSourceService.to_next(renew_interval, latest_date)
                else:
                    # 已是最新，不需要更新
                    return jobs
            else:
                # 数据库无记录：全量拉取
                start_date = data_default_start_date
            
            # 宏观数据只有一个job
            job = {
                'start_date': start_date,
                'end_date': latest_market_open_day
            }
            jobs.append(job)

        return jobs

    def should_renew(self, latest_market_open_day: str = None, stock_list: list = None) -> List[Dict]:
        """
        判断是否需要更新并构建任务列表 - 子类可重写
        
        Args:
            latest_market_open_day: 最新市场开放日
            stock_list: 可选的股票列表（股票相关表需要）
            
        Returns:
            List[Dict]: 任务列表
            - 如果不需要更新，返回空列表 []
            - 如果需要更新，返回任务列表，每个任务包含 start_date, end_date 和主键字段
        """
        renew_mode = self.config['renew_mode'].lower()
        table = self.db.get_table_instance(self.config['table_name'])

        # overwrite/upsert 模式：总是从头开始更新
        if renew_mode in ['overwrite', 'upsert']:
            return self.build_jobs(latest_market_open_day, stock_list, db_records=None)

        # incremental 模式：根据数据库中的最新数据判断
        elif renew_mode == 'incremental':
            db_records = table.load_latest_records()
            return self.build_jobs(latest_market_open_day, stock_list, db_records)
        
        else:
            logger.warning(f"未知的renew_mode: {renew_mode}，默认使用增量模式")
            db_records = table.load_latest_records()
            return self.build_jobs(latest_market_open_day, stock_list, db_records)

    def prepare_data_for_save(self, api_results: Dict[str, Any], job: Dict = None) -> Any:
        """
        准备要保存的数据 - ⭐⭐⭐⭐⭐ 子类最常重写的方法
        
        职责：
        1. 合并多个API的数据（如果有多个）
        2. 数据清洗和验证
        3. 计算衍生字段
        4. 任何保存前的业务逻辑处理
        
        注意：
        - api_results 中的数据已经过字段映射，使用DB字段名
        - 适用于单API和多API场景
        - 这是保存前最后的数据处理机会
        
        Args:
            api_results: API结果字典 {api_name: mapped_data}
                        数据已映射为DB字段名
            
        Returns:
            准备好保存的数据（DataFrame或list）
            
        示例1: 单API + 数据清洗
            def prepare_data_for_save(self, api_results):
                import pandas as pd
                
                # 单个API，直接处理
                data = list(api_results.values())[0]
                df = pd.DataFrame(data)
                
                # 数据清洗
                df = df[df['price'] > 0]
                df = df.drop_duplicates(subset=['id', 'date'])
                
                return df
        
        示例2: 多API合并 + 计算
            def prepare_data_for_save(self, api_results):
                import pandas as pd
                
                # 合并多个API
                df_price = pd.DataFrame(api_results['price'])
                df_volume = pd.DataFrame(api_results['volume'])
                merged = pd.merge(df_price, df_volume, on=['date', 'id'])
                
                # 计算衍生字段
                merged['total_value'] = merged['close'] * merged['volume']
                
                # 数据清洗
                merged = merged.dropna()
                
                return merged
        
        示例3: 使用默认合并 + 自定义处理
            def prepare_data_for_save(self, api_results):
                # 使用基类的默认合并
                data = self._default_merge_api_results(api_results)
                
                # 自定义处理
                df = pd.DataFrame(data)
                df['processed_field'] = df['raw_field'] * 100
                
                return df
        """
        # 默认实现
        if len(api_results) == 1:
            # 单个API，直接返回
            return list(api_results.values())[0]
        
        # 多个API，使用默认合并逻辑
        return self.default_merge_api_results(api_results)
    
    def default_merge_api_results(self, api_results: Dict[str, Any]) -> Any:
        """
        默认的API合并逻辑（辅助方法，供子类调用）
        
        子类可以在 prepare_data_for_save 中调用此方法来使用默认合并
        
        Args:
            api_results: API结果字典
            
        Returns:
            简单拼接后的数据
        """
        combined_data = []
        for result in api_results.values():
            if result is None:
                continue
            combined_data.extend(self.to_records(result))
        
        return combined_data
    
    def should_execute_api(self, api_config: Dict, previous_results: Dict) -> bool:
        """
        判断是否执行特定 API - 子类可重写
        
        Args:
            api_config: API 配置
            previous_results: 之前的 API 结果
            
        Returns:
            bool: 是否执行
        """
        # 检查依赖条件
        if 'condition' in api_config:
            return self._check_api_condition(api_config['condition'], previous_results)
        
        return True
    
    def prepare_api_params(self, api_config: Dict, start_date: str, end_date: str, previous_results: Dict) -> Dict:
        """
        准备 API 参数 - 子类可重写
        
        Args:
            api_config: API 配置
            start_date: 开始日期
            end_date: 结束日期
            previous_results: 之前的 API 结果
            
        Returns:
            Dict: API 参数
        """
        params = api_config['params'].copy()
        
        # 替换日期变量
        for key, value in params.items():
            if isinstance(value, str):
                value = value.replace('{start_date}', start_date)
                value = value.replace('{end_date}', end_date)
                params[key] = value
        
        return params
    
    def get_renew_mode(self) -> str:
        """
        获取更新模式 - 子类可重写
        
        Returns:
            str: 'upsert' | 'incremental' | 'overwrite'
        """
        return self.config.get('renew_mode', 'upsert')
    
    
    # ==================== 辅助工具方法（供子类使用）====================
    
    def to_records(self, data: Any) -> List[Dict]:
        """
        将数据转换为字典列表
        
        Args:
            data: 数据（DataFrame或list）
            
        Returns:
            List[Dict]: 字典列表
        """
        if data is None:
            return []
        if isinstance(data, list):
            return data
        if hasattr(data, 'to_dict'):
            return data.to_dict('records')
        return []
    
    def to_df(self, data: Any) -> Any:
        """
        将数据转换为DataFrame
        子类重写prepare_data_for_save时常用
        
        Args:
            data: 数据（list或DataFrame）
            
        Returns:
            pd.DataFrame
        """
        import pandas as pd
        if data is None:
            return pd.DataFrame()
        if isinstance(data, list):
            return pd.DataFrame(data)
        if hasattr(data, 'to_dict'):
            return data
        return pd.DataFrame()
    
    # ==================== 内部实现方法 ====================
    
    def _get_record_key(self, record: Dict, primary_keys: List[str]) -> str:
        """
        根据主键生成记录的唯一标识
        
        Args:
            record: 记录字典
            primary_keys: 主键列表
            
        Returns:
            str: 记录的唯一标识
        """
        return '_'.join([str(record.get(key, '')) for key in primary_keys if key != self.config['date']['field']])
    

    
    def _simple_renew(self, jobs: List[Dict]):
        """
        简单模式更新
        适用于：宏观数据等无需并发的场景
        """
        logger.info(f"🔄 开始更新 {self.config['table_name']}")

        for job in jobs:
            # 1. 请求所有API并收集结果
            api_results = self._request_apis(job)
            
            if not api_results:
                logger.warning(f"⚠️  任务 {job} 未获取到数据")
                continue
            
            # 2. 准备要保存的数据（合并、清洗、计算等）
            data = self.prepare_data_for_save(api_results, job)
            
            # 3. 保存数据
            if data is not None:
                self.save_data(data)


    def _multithread_renew(self, jobs: List[Dict]):
        """
        多线程模式更新
        适用于：股票K线等需要大量并发请求的场景
        """
        logger.info(f"🔄 开始多线程更新 {self.config['table_name']}")

        if not jobs:
            return True
        
        # 创建多线程工作器（使用智能超时机制）
        worker = FuturesWorker(
            max_workers=self.workers,  # FuturesWorker的参数名是max_workers，传入我们的workers配置
            execution_mode=ExecutionMode.PARALLEL,
            enable_monitoring=True,
            timeout=3600,  # 设置一个很长的超时时间，实际超时由智能机制控制
            is_verbose=False  # 禁用多线程的详细progress日志
        )
        
        # 设置自定义任务执行器（带进度显示和智能超时监控）
        def job_executor_with_progress(job: Dict) -> bool:
            start_time = time.time()
            result = self._execute_single_job(job)
            execution_time = time.time() - start_time
            
            # 显示进度（使用线程安全的方式）
            with self._progress_lock:
                self._completed_jobs += 1
                progress_percent = (self._completed_jobs / self._total_jobs) * 100
                
                # 获取任务信息（区分股票数据和其他数据）
                stock_name = job.get('stock_name')
                stock_id = job.get('ts_code', job.get('id'))
                
                # 如果执行时间过长，记录警告
                if execution_time > 30:  # 超过30秒认为异常
                    if stock_name and stock_id:
                        logger.warning(f"股票 {stock_id} ({stock_name}) 执行时间过长: {execution_time:.1f}秒")
                    else:
                        logger.warning(f"任务执行时间过长: {execution_time:.1f}秒")
                
                # 输出可配置的日志（子类可重写）
                self.log_job_completion(job, result, progress_percent)
            return result
        
        # 初始化进度计数器
        import threading
        self._progress_lock = threading.Lock()
        self._completed_jobs = 0
        self._total_jobs = len(jobs)
        
        # 设置任务执行器
        worker.set_job_executor(job_executor_with_progress)
        
        # 添加任务
        for i, job in enumerate(jobs):
            worker.add_job(f"job_{i}", job)
        
        # 执行任务
        try:
            stats = worker.run_jobs()
            success_count = stats.get('completed_jobs', 0)
            total_count = stats.get('total_jobs', 0)
            
            logger.info(f"{IconService.get('success')} {self.config['table_name']} 更新完毕")
            return success_count == total_count
        except Exception as e:
            logger.error(f"❌ {self.config['table_name']}多线程执行失败: {e}")
            return False
    
    def log_job_completion(self, job: Dict, is_success: bool, progress_percent: float):
        """
        输出任务完成日志 - 子类可重写
        
        子类可以完全自定义日志输出逻辑，也可以调用log_default使用默认格式
        
        Args:
            job: 任务字典，包含所有任务参数和_log_vars
            is_success: 是否成功
            progress_percent: 进度百分比（保留原始数字，如3.333）
            
        何时重写：
            - 需要完全自定义日志格式
            - 需要根据特殊条件决定是否输出日志
            - 需要输出到其他日志系统
        """
        # 获取日志配置
        multithread_config = self.config.get('multithread', {})
        log_config = multithread_config.get('log', {})
        
        # 如果没有配置log或配置为空，使用默认日志
        if not log_config:
            self.log_default(job, is_success, progress_percent)
            return
        
        # 根据成功/失败选择日志模板
        log_template = None
        if is_success and 'success' in log_config:
            log_template = log_config['success']
        elif not is_success and 'failure' in log_config:
            log_template = log_config['failure']
        
        # 如果没有配置对应的日志模板，不输出日志
        if not log_template:
            return
        
        # 准备变量字典
        variables = self._extract_log_variables(job, progress_percent)
        
        # 替换变量并输出日志
        try:
            log_message = log_template.format(**variables)
            if is_success:
                logger.info(log_message)
            else:
                logger.error(log_message)
        except KeyError as e:
            logger.warning(f"⚠️  日志模板变量错误: {e}, 模板: {log_template}")
            self.log_default(job, is_success, progress_percent)
    
    def _extract_log_variables(self, job: Dict, progress_percent: float) -> Dict[str, Any]:
        """
        从job中提取日志变量（灵活设计，不hard code特殊字段）
        
        提供的变量：
        1. progress: 内置变量，格式化为 "N" (N保留1位小数，不含%符号)
        2. job中的所有字段（如 id, ts_code, start_date, end_date, term 等）
        3. _log_vars: 如果job中包含'_log_vars'字段（由build_jobs设置），
           会直接添加其中的所有变量
           例如: {'stock_name': '平安银行', 'quarter': '2024Q1'}
        
        Args:
            job: 任务字典
            progress_percent: 进度百分比
            
        Returns:
            Dict: 变量字典，用于日志模板替换
        """
        # 基础变量
        variables = {
            'progress': f"{progress_percent:.1f}",  # 内置变量（数字，不含%符号）
            'table_name': self.config.get('table_name', 'unknown'),
        }
        
        # 添加job中的所有字段作为变量（跳过内部字段）
        for key, value in job.items():
            if not key.startswith('_'):
                variables[key] = value
        
        # 添加自定义日志变量（由子类在build_jobs中设置）
        if '_log_vars' in job and isinstance(job['_log_vars'], dict):
            variables.update(job['_log_vars'])
        
        return variables
    
    def log_default(self, job: Dict, success: bool, progress_percent: float):
        """
        输出默认日志格式 - 子类可调用
        
        当子类重写log_job_completion时，可以调用此方法使用默认格式
        
        Args:
            job: 任务字典
            success: 是否成功
            progress_percent: 进度百分比（保留原始数字，如3.333）
        """
        # 提取常用信息
        ts_code = job.get('ts_code') or job.get('id')
        task_name = self.config['table_name']
        
        # 尝试从_log_vars中获取名称信息（适配多种数据类型）
        display_name = None
        if '_log_vars' in job and isinstance(job['_log_vars'], dict):
            # 优先查找常见的名称字段
            for name_key in ['stock_name', 'name', 'region', 'category']:
                if name_key in job['_log_vars']:
                    display_name = job['_log_vars'][name_key]
                    break
        
        # 输出日志
        if display_name and ts_code:
            # 有代码和名称
            if success:
                logger.info(f"{ts_code} ({display_name}) 更新完毕 - 进度: {progress_percent:.1f}%")
            else:
                logger.error(f"{ts_code} ({display_name}) 更新失败 - 进度: {progress_percent:.1f}%")
        elif ts_code:
            # 只有代码
            if success:
                logger.info(f"{ts_code} 更新完毕 - 进度: {progress_percent:.1f}%")
            else:
                logger.error(f"{ts_code} 更新失败 - 进度: {progress_percent:.1f}%")
        else:
            # 非股票数据（宏观数据等）
            if success:
                logger.info(f"{task_name} 任务完成 - 进度: {progress_percent:.1f}%")
            else:
                logger.error(f"{task_name} 任务失败 - 进度: {progress_percent:.1f}%")
        
    def _execute_single_job(self, job: Dict) -> bool:
        """
        执行单个任务（多线程模式下的单个job）
        
        Args:
            job: 任务字典，包含 start_date, end_date 和其他参数
            
        Returns:
            bool: 是否成功
        """
        try:
            # 应用限流
            if self.rate_limiter:
                self.rate_limiter.acquire()

            # 1. 请求所有API
            api_results = self._request_apis(job)

            if not api_results:
                return True  # 没有数据是正常情况
            
            # 2. 准备要保存的数据（合并、清洗、计算等）
            data = self.prepare_data_for_save(api_results, job)
            
            # 3. 保存数据
            if data is not None:
                return self.save_data(data)
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 任务执行失败: {e}")
            import traceback
            logger.debug(f"详细错误: {traceback.format_exc()}")
            return False

    def _request_apis(self, job: Dict) -> Dict[str, Any]:
        """
        执行所有配置的API并收集结果
        
        事务性原则：如果任何一个必需的API失败，整个job失败
        
        Args:
            job: 任务字典，包含API所需的参数
            
        Returns:
            Dict[str, Any]: API结果字典，格式为 {api_name: api_result}
            None: 如果有任何必需的API失败
        """
        apis = self.config.get('apis', [])
        api_results = {}
        failed_apis = []
        
        # 设置当前job信息（供should_execute_api使用）
        self._current_job = job
        
        for api in apis:
            api_name = api.get('name', api['method'])
            
            # 检查是否需要执行此API
            if not self.should_execute_api(api, api_results):
                continue
            
            result = self._request_single_api(job, api)
            
            # 检查API是否成功（返回有效数据）
            if result is None or (hasattr(result, 'empty') and result.empty):
                # API失败或返回空数据
                failed_apis.append(api_name)
                
                # 提取job信息用于日志
                job_id = job.get('ts_code') or job.get('id', 'unknown')
                job_info = f"[{job_id}]"
                if '_log_vars' in job and job['_log_vars'].get('stock_name'):
                    job_info = f"[{job_id} {job['_log_vars']['stock_name']}]"
                
                logger.warning(f"⚠️  {job_info} API [{api_name}] 失败或返回空数据")
            
            api_results[api_name] = result
        
        # 清理临时变量
        self._current_job = None
        
        # 如果有API失败，返回None（整个job失败）
        if failed_apis:
            # 提取job信息
            job_id = job.get('ts_code') or job.get('id', 'unknown')
            job_info = f"[{job_id}]"
            if '_log_vars' in job and job['_log_vars'].get('stock_name'):
                job_info = f"[{job_id} {job['_log_vars']['stock_name']}]"
            
            logger.warning(f"⚠️  {job_info} Job执行失败，以下API未成功: {', '.join(failed_apis)}，数据不会保存")
            return None
            
        return api_results

    def _request_single_api(self, job: Dict, api: Dict) -> Any:
        """
        执行单个API调用并映射字段
        
        Args:
            job: 任务字典，包含start_date, end_date, ts_code等参数
            api: API配置字典，包含method, params, mapping等
            
        Returns:
            Any: 映射后的数据（DB字段名）
        """
        try:
            # 1. 准备API参数
            api_params = self._prepare_api_params(job, api)
            
            # 2. 获取可调用的API方法
            api_method_name = api['method']
            api_method = getattr(self.api, api_method_name)
            
            # 3. 调用API（获取原始数据）
            result = api_method(**api_params)
            
            # 4. 立即映射字段 ✨
            if result is not None:
                result = self.map_api_data(result, api)
            
            return result
            
        except Exception as e:
            logger.error(f"❌ API调用失败 [{api.get('name', api['method'])}]: {e}")
            # 返回空DataFrame
            import pandas as pd
            return pd.DataFrame()
    
    def map_api_data(self, data: Any, api: Dict) -> Any:
        """
        映射单个API的数据 - 子类可重写
        
        这是方案A的核心：在API级别进行字段映射
        子类可以针对特定API自定义映射逻辑
        
        何时重写：
        - 需要在映射前使用原始字段计算衍生字段
        - 需要针对特定API的特殊处理
        - 需要访问API返回的所有原始字段（包括未配置mapping的字段）
        
        Args:
            data: 原始API数据（包含所有字段，使用API字段名）
            api: API配置字典（包含name, mapping等）
            
        Returns:
            映射后的数据（使用DB字段名）
            
        示例1: 使用默认行为（不重写）
            # 自动应用配置中的mapping
            
        示例2: 针对特定API自定义
            def map_api_data(self, data, api):
                api_name = api.get('name')
                
                if api_name == 'price':
                    # 访问原始字段
                    df = pd.DataFrame(data)
                    
                    # 使用原始字段计算（这些字段可能不在mapping中）
                    df['market_cap'] = df['close'] * df['total_share']
                    df['pe_ttm'] = df['pe']
                    
                    # 应用mapping
                    return self.apply_single_api_mapping(df, api['mapping'])
                
                elif api_name == 'volume':
                    df = pd.DataFrame(data)
                    df['turnover_rate'] = (df['vol'] / df['float_share']) * 100
                    return self.apply_single_api_mapping(df, api['mapping'])
                
                else:
                    # 其他API使用默认行为
                    return super().map_api_data(data, api)
        """
        mapping = api.get('mapping', {})
        if not mapping:
            logger.debug(f"API [{api.get('name')}] 未配置mapping，返回原始数据")
            return data
        
        # 默认行为：应用配置的mapping
        return self.apply_single_api_mapping(data, mapping)
    
    def apply_single_api_mapping(self, data: Any, mapping: Dict) -> Any:
        """
        为单个API的数据应用字段映射（辅助方法，供子类调用）
        
        Args:
            data: API返回的数据（DataFrame或list）
            mapping: 字段映射配置 {db_field: api_field_config}
            
        Returns:
            映射后的数据（保持原类型）
        """
        if not mapping:
            return data
        
        # 转换为列表格式处理
        data_list = self.to_records(data)
        if not data_list:
            return data
        
        # 应用映射
        mapped_list = []
        for record in data_list:
            mapped_record = {}
            for db_field, mapping_config in mapping.items():
                try:
                    value = self._map_single_field(record, db_field, mapping_config)
                    mapped_record[db_field] = value
                except Exception as e:
                    logger.warning(f"字段映射失败 [{db_field}]: {e}")
                    mapped_record[db_field] = None
            mapped_list.append(mapped_record)
        
        # 如果原数据是DataFrame，转回DataFrame
        if hasattr(data, 'to_dict'):
            try:
                import pandas as pd
                return pd.DataFrame(mapped_list)
            except Exception as e:
                logger.error(f"转换为DataFrame失败: {e}")
                return mapped_list
        
        return mapped_list

    def _prepare_api_params(self, job: Dict, api: Dict) -> Dict:
        """
        准备API参数
        
        Args:
            job: 任务字典
            api: API配置字典
            
        Returns:
            Dict: 准备好的API参数
        """
        # 从api配置中获取基础参数
        params = api.get('params', {}).copy()
        
        # 用job中的值替换参数中的变量
        for key, value in params.items():
            if isinstance(value, str):
                # 替换变量占位符
                value = value.replace('{start_date}', job.get('start_date', ''))
                value = value.replace('{end_date}', job.get('end_date', ''))
                value = value.replace('{ts_code}', job.get('ts_code', ''))
                params[key] = value
        
        # job中的参数可以直接覆盖（如果同名）
        for key in ['start_date', 'end_date', 'ts_code']:
            if key in job and key not in params:
                params[key] = job[key]
        
        return params
    
    def save_data(self, data: Any) -> bool:
        """
        保存数据到数据库 - 子类可重写
        
        默认行为：
        - overwrite: 删除表数据后插入
        - incremental: 直接插入（假设无冲突）
        - upsert: 基于主键更新或插入
        
        何时重写：
        - 需要特殊的保存逻辑（如stock_list的is_active更新）
        - 需要在保存前/后执行额外操作
        - 需要自定义冲突处理逻辑
        
        Args:
            data: 已映射和处理后的数据（DB字段名）
            
        Returns:
            bool: 是否保存成功
            
        示例1: 使用默认行为（不重写）
            # 根据renew_mode自动选择保存方式
            
        示例2: 特殊逻辑（如stock_list的is_active）
            def save_data(self, data):
                # 先保存新数据
                super().save_data(data)
                
                # 特殊逻辑：标记不活跃的股票
                table = self.db.get_table_instance(self.config['table_name'])
                new_codes = [r['ts_code'] for r in data]
                table.execute_raw_update(
                    f"UPDATE {self.config['table_name']} "
                    f"SET is_active = 0 "
                    f"WHERE ts_code NOT IN ({','.join(new_codes)})"
                )
                return True
        """
        # 安全检查
        if data is None:
            logger.info(f"ℹ️  {self.config['table_name']} 数据为空，跳过保存")
            return True
        
        # 检查DataFrame是否为空
        if hasattr(data, 'empty') and data.empty:
            logger.info(f"ℹ️  {self.config['table_name']} 数据为空，跳过保存")
            return True
        
        try:
            # 1. 获取表实例
            table_name = self.config['table_name']
            table = self.db.get_table_instance(table_name)
            
            if table is None:
                logger.error(f"❌ 无法获取表实例: {table_name}")
                return False
            
            # 2. 转换数据格式
            data_list = self._convert_to_list(data)
            if not data_list:
                logger.info(f"ℹ️  {self.config['table_name']} 转换后数据为空，跳过保存")
                return True
            
            # 3. 根据renew_mode保存数据
            renew_mode = self.get_renew_mode().lower()
            
            if renew_mode == 'overwrite':
                return self._save_with_overwrite(table, table_name, data_list)
            elif renew_mode == 'incremental':
                return self._save_with_incremental(table, data_list)
            else:  # upsert
                return self._save_with_upsert(table, table_name, data_list)
        
        except Exception as e:
            logger.error(f"❌ {self.config['table_name']} 数据保存失败: {e}")
            import traceback
            logger.error(f"详细错误: {traceback.format_exc()}")
            return False
    
    def _convert_to_list(self, data: Any) -> List[Dict]:
        """
        将数据转换为字典列表
        处理DataFrame的NaN值
        
        默认行为（根据表schema自动决定）：
        - 数值类型（float/double/int/bigint）→ 0
        - 字符串类型（varchar/text）→ ''
        - 其他类型 → None
        
        可配置项（config['nan_handling']）：
        - auto_convert: False → 关闭自动转换，所有NaN保留为None
        - allow_null_fields: [...] → 指定字段保留NULL
        - field_defaults: {field: value} → 指定字段的自定义默认值
        """
        # 转换为列表
        if isinstance(data, list):
            data_list = data
        elif hasattr(data, 'to_dict'):
            data_list = data.to_dict('records')
        else:
            data_list = list(data) if data else []
        
        # 获取NaN处理配置
        nan_config = self.config.get('nan_handling', {})
        auto_convert = nan_config.get('auto_convert', True)
        allow_null_fields = nan_config.get('allow_null_fields', [])
        field_defaults = nan_config.get('field_defaults', {})
        
        # 如果关闭自动转换，直接返回（保留所有NaN为None）
        if not auto_convert:
            return data_list
        
        # 获取字段类型映射（从schema）
        field_types = self._get_field_types_from_schema()
        
        # 处理NaN值
        import pandas as pd
        cleaned_list = []
        for record in data_list:
            cleaned_record = {}
            for key, value in record.items():
                if pd.isna(value):
                    # 检查是否允许NULL
                    if key in allow_null_fields:
                        # 允许NULL的字段，保留None
                        cleaned_record[key] = None
                    
                    # 检查是否有自定义默认值
                    elif key in field_defaults:
                        # 使用自定义默认值
                        cleaned_record[key] = field_defaults[key]
                    
                    # 使用schema类型决定默认值
                    else:
                        field_type = field_types.get(key, 'unknown').lower()
                        
                        if field_type in ['float', 'double', 'int', 'bigint', 'decimal']:
                            # 数值类型 → 0
                            cleaned_record[key] = 0
                        elif field_type in ['varchar', 'text']:
                            # 字符串类型 → 空字符串
                            cleaned_record[key] = ''
                        else:
                            # 其他类型 → None
                            cleaned_record[key] = None
                else:
                    cleaned_record[key] = value
            cleaned_list.append(cleaned_record)
        
        return cleaned_list
    
    def _get_field_types_from_schema(self) -> Dict[str, str]:
        """
        从表schema中获取字段类型映射
        
        Returns:
            Dict[str, str]: {field_name: field_type}
        """
        try:
            schema = self.db.get_table_description(self.config['table_name'])
            fields = schema.get('fields', [])
            
            field_types = {}
            for field in fields:
                field_name = field.get('name')
                field_type = field.get('type', 'unknown')
                if field_name:
                    field_types[field_name] = field_type
            
            return field_types
        except Exception as e:
            logger.warning(f"⚠️  无法获取schema字段类型: {e}")
            return {}
    
    def _save_with_overwrite(self, table, table_name: str, data_list: List[Dict]) -> bool:
        """
        覆盖模式：清空表后插入
        """
        logger.info(f"🔄 覆盖模式：清空表 {table_name}")
        
        # 先清空表
        table.execute_raw_update(f"DELETE FROM {table_name}")
        
        # 插入新数据
        return table.insert(data_list)
    
    def _save_with_incremental(self, table, data_list: List[Dict]) -> bool:
        """
        增量模式：直接插入（假设无冲突）
        """
        return table.insert(data_list)
    
    def _save_with_upsert(self, table, table_name: str, data_list: List[Dict]) -> bool:
        """
        Upsert模式：基于主键更新或插入
        """
        try:
            # 获取主键（可能抛出异常）
            primary_keys = self.db.get_table_primary_keys(table_name)
            
            # 使用replace方法（基于主键upsert）
            return table.replace(data_list, unique_keys=primary_keys)
        except ValueError as e:
            logger.error(f"❌ 获取表主键失败: {e}")
            return False
    
    def _map_single_field(self, record: Dict, db_field: str, mapping_config: Any) -> Any:
        """
        映射单个字段
        
        Args:
            record: 原始记录
            db_field: 数据库字段名
            mapping_config: 映射配置（可以是字符串、字典或函数）
            
        Returns:
            Any: 映射后的值
        """
        # 情况1: 简单字符串映射 'db_field': 'api_field'
        if isinstance(mapping_config, str):
            return record.get(mapping_config)
        
        # 情况2: 可调用函数 'db_field': lambda x: transform(x)
        elif callable(mapping_config):
            return mapping_config(record)
        
        # 情况3: 完整配置对象
        elif isinstance(mapping_config, dict):
            # 常量值
            if 'value' in mapping_config:
                return mapping_config['value']
            
            # 从source字段获取值
            source_field = mapping_config.get('source')
            if source_field:
                value = record.get(source_field)
                
                # 如果值为None或不存在，使用默认值
                if value is None and 'default' in mapping_config:
                    return mapping_config['default']
                
                # 应用转换函数
                if 'transform' in mapping_config and value is not None:
                    transform_func = mapping_config['transform']
                    if callable(transform_func):
                        return transform_func(value)
                
                return value
            
            # 如果没有source，但有default
            if 'default' in mapping_config:
                return mapping_config['default']
        
        # 默认返回None
        return None