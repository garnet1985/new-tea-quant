#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
基础 Renewer 类
提供所有默认实现，子类可以重写需要的方法
"""

import time
from datetime import datetime
from typing import Dict, List, Any, Optional
from loguru import logger
from abc import ABC

from utils.worker.multi_thread.futures_worker import FuturesWorker, ExecutionMode
from utils.icon.icon_service import IconService


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
        
        # 初始化组件
        self._init_rate_limiter()
        self._init_multithread_config()
        
    # ==================== 主要入口方法 ====================
    
    def renew(self, latest_market_open_day: str = None):
        """
        主要更新入口 - 子类通常不需要重写
        
        Args:
            latest_market_open_day: 最新市场开放日
            
        Returns:
            更新结果
        """
        start_date = self.should_renew(latest_market_open_day, latest_market_open_day)
        if not start_date:
            logger.info(f"⏭️ {self.config['table_name']} 无需更新")
            return None
        
        if self.config['job_mode'] == 'simple':
            return self._renew_simple(start_date, latest_market_open_day)
        elif self.config['job_mode'] == 'multithread':
            return self._renew_multithread(start_date, latest_market_open_day)
        else:
            raise ValueError(f"不支持的作业模式: {self.config['job_mode']}")
    
    # ==================== 可重写的方法 ====================
    
    def should_renew(self, start_date: str = None, end_date: str = None) -> Optional[str]:
        """
        判断是否需要更新 - 子类可重写
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            str: 开始日期，如果不需要更新返回 None
        """
        table_name = self.config['table_name']
        date_field = self.config.get('date_field', 'date')
        
        # 获取最新数据日期
        latest_date = self._get_latest_date(table_name, date_field)
        
        # 默认逻辑：如果最新日期早于结束日期，则需要更新
        if end_date and latest_date < end_date:
            return latest_date
        
        return None
    
    def build_jobs(self, start_date: str, end_date: str) -> List[Dict]:
        """
        构建任务列表 - 子类可以重写（如果是 multithread 模式）
        简单模式不需要此方法，默认返回空列表
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            List[Dict]: 任务列表（简单模式返回空列表）
        """
        return []
    
    def combine_apis_data(self, api_results: Dict[str, Any]) -> Any:
        """
        合并多个 API 数据 - 子类可重写
        
        Args:
            api_results: API 结果字典
            
        Returns:
            合并后的数据
        """
        if len(api_results) == 1:
            return list(api_results.values())[0]
        
        # 默认合并逻辑：简单拼接
        combined_data = []
        for result in api_results.values():
            if result is None:
                continue
            if hasattr(result, 'to_dict'):
                combined_data.extend(result.to_dict('records'))
            else:
                combined_data.extend(result)
        
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
    
    def process_data_before_save(self, data: Any) -> Any:
        """
        数据保存前的处理 - 子类可重写
        
        Args:
            data: 原始数据
            
        Returns:
            处理后的数据
        """
        return data
    
    def get_renew_mode(self) -> str:
        """
        获取更新模式 - 子类可重写
        
        Returns:
            str: 'upsert' | 'incremental' | 'overwrite'
        """
        return self.config.get('renew_mode', 'upsert')
    
    
    # ==================== 内部实现方法 ====================
    
    def _init_rate_limiter(self):
        """初始化限流器"""
        rate_limit_config = self.config.get('rate_limit')
        if rate_limit_config:
            from .rate_limiter import APIRateLimiter
            # buffer自动使用max_workers，确保多线程环境下的限流安全
            buffer = self.config.get('multithread', {}).get('max_workers', 10)
            self.rate_limiter = APIRateLimiter(
                max_per_minute=rate_limit_config.get('max_per_minute', 200),
                api_name=self.config['table_name'],
                buffer=buffer
            )
        else:
            self.rate_limiter = None
    
    def _init_multithread_config(self):
        """初始化多线程配置"""
        self.multithread_config = self.config.get('multithread', {})
        self.max_workers = self.multithread_config.get('workers', 4)
    
    def _renew_simple(self, start_date: str, end_date: str):
        """简单模式更新"""
        logger.info(f"🔄 开始更新 {self.config['table_name']}")
        
        # 1. 解析依赖关系
        api_execution_order = self._resolve_dependencies()
        
        # 2. 按顺序执行 API
        api_results = {}
        for api_config in api_execution_order:
            if self.should_execute_api(api_config, api_results):
                result = self._execute_single_api(api_config, start_date, end_date, api_results)
                api_results[api_config['name']] = result
        
        # 3. 合并数据
        combined_data = self.combine_apis_data(api_results)
        
        # 4. 处理数据
        processed_data = self.process_data_before_save(combined_data)
        
        # 5. 保存数据
        return self._save_data(processed_data)
    
    def _renew_multithread(self, start_date: str, end_date: str):
        """多线程模式更新"""
        logger.info(f"🔄 开始多线程更新 {self.config['table_name']}")
        
        # 1. 构建任务
        jobs = self.build_jobs(start_date, end_date)
        
        # 2. 执行多线程任务
        return self._execute_multithread_jobs(jobs)
    
    def _resolve_dependencies(self):
        """解析 API 依赖关系"""
        if 'apis' not in self.config:
            return []
        
        api_map = {api['name']: api for api in self.config['apis']}
        in_degree = {name: 0 for name in api_map}
        
        # 计算入度
        for api in self.config['apis']:
            for dep in api.get('depends_on', []):
                in_degree[api['name']] += 1
        
        # 拓扑排序
        queue = [name for name, degree in in_degree.items() if degree == 0]
        result = []
        
        while queue:
            current = queue.pop(0)
            result.append(api_map[current])
            
            # 更新依赖此 API 的其他 API
            for api in self.config['apis']:
                if current in api.get('depends_on', []):
                    in_degree[api['name']] -= 1
                    if in_degree[api['name']] == 0:
                        queue.append(api['name'])
        
        return result
    
    def _execute_single_api(self, api_config: Dict, start_date: str, end_date: str, previous_results: Dict):
        """执行单个 API"""
        try:
            # 准备参数
            params = self.prepare_api_params(api_config, start_date, end_date, previous_results)
            
            # 应用限流
            if self.rate_limiter:
                self.rate_limiter.acquire()
            
            # 调用 API
            api_method = getattr(self.api, api_config['method'])
            return api_method(**params)
            
        except Exception as e:
            logger.error(f"❌ API 调用失败 {api_config['name']}: {e}")
            return None
    
    def _check_api_condition(self, condition: str, previous_results: Dict) -> bool:
        """检查 API 执行条件"""
        if condition == 'if_adj_needed':
            # 检查是否有复权事件
            check_result = previous_results.get('check_adj')
            if check_result is None:
                return False
            # 安全的 DataFrame 空检查
            if hasattr(check_result, 'empty'):
                return not check_result.empty
            return bool(check_result)
        
        return True
    
    def _execute_multithread_jobs(self, jobs: List[Dict]):
        """执行多线程任务"""
        if not jobs:
            return True
        
        # 创建多线程工作器（使用智能超时机制）
        worker = FuturesWorker(
            max_workers=self.max_workers,
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
                
                # 根据数据类型显示不同的进度信息
                if stock_name and stock_id:
                    logger.info(f"股票 {stock_id} ({stock_name})更新完毕 - progress: {progress_percent:.1f}%")
                else:
                    # 非股票数据的进度显示
                    task_name = job.get('api_method', self.config['table_name'])
                    logger.info(f"{task_name} 任务完成 - progress: {progress_percent:.1f}%")
            return result
        
        # 初始化进度计数器
        import threading
        import time
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
    
    def _execute_single_job(self, job: Dict) -> bool:
        """执行单个多线程任务"""
        try:
            # 应用限流
            if self.rate_limiter:
                self.rate_limiter.acquire()
            
            # 获取数据
            api_data = self._fetch_job_data(job)
            if api_data is None:
                logger.error(f"❌ 多线程任务API调用失败")
                return False
            
            # 检查DataFrame是否为空
            if hasattr(api_data, 'empty') and api_data.empty:
                return True  # 没有新数据是正常的业务情况
            
            # 处理需要合并的数据（如price_indexes）
            if hasattr(self, 'combine_apis_data') and callable(self.combine_apis_data):
                # 对于需要合并的数据，将单个API结果包装成字典
                api_name = job.get('api_method', 'unknown')
                api_results = {api_name: api_data}
                processed_data = self.combine_apis_data(api_results)
            else:
                processed_data = api_data
            
            # 保存数据
            return self._save_data(processed_data)
            
        except Exception as e:
            logger.error(f"❌ 多线程任务执行失败: {e}")
            return False
    
    
    def _fetch_job_data(self, job: Dict):
        """从任务中获取数据"""
        api_method_name = job.get('api_method', self.config.get('api_method', 'unknown'))
        api_method = getattr(self.api, api_method_name)
        
        # 使用任务中的参数
        api_params = job.get('api_params', {})
        
        # 确保所有参数都是可序列化的字符串
        serialized_params = {}
        for key, value in api_params.items():
            if hasattr(value, 'strftime'):  # datetime对象
                serialized_params[key] = value.strftime('%Y%m%d')
            elif isinstance(value, (int, float)):
                serialized_params[key] = str(value)
            else:
                serialized_params[key] = str(value)
        
        try:
            return api_method(**serialized_params)
        except Exception as e:
            msg = str(e)
            if any(k in msg for k in ["查询数据失败", "无数据", "no data", "空数据", "not found"]):
                try:
                    import pandas as pd
                    return pd.DataFrame()
                except:
                    return []
            else:
                logger.error(f"❌ API调用失败: {e}")
                return None
    
    def _save_data(self, data: Any) -> bool:
        """保存数据到数据库"""
        # 安全的 None 检查，避免 DataFrame 的布尔判断错误
        if data is None:
            return True
        
        # 检查 DataFrame 是否为空
        if hasattr(data, 'empty') and data.empty:
            logger.info(f"ℹ️ {self.config['table_name']} 数据为空，跳过保存")
            return True
        
        try:
            # 获取表实例
            table_name = self.config['table_name']
            table_instance = self.db.get_table_instance(table_name)
            
            if table_instance is None:
                logger.error(f"❌ 无法获取表实例: {table_name}")
                return False
            
            # 将 DataFrame 转换为列表（如果需要）
            if hasattr(data, 'to_dict'):
                # DataFrame 转换为字典列表
                data_list = data.to_dict('records')
                
                # 处理 DataFrame 中的 NaN 值
                import pandas as pd
                for record in data_list:
                    for key, value in record.items():
                        if pd.isna(value):
                            # 对于数值字段，将 NaN 转换为 0.0
                            if isinstance(value, (int, float)) or (isinstance(value, str) and value.replace('.', '').replace('-', '').isdigit()):
                                record[key] = 0.0
                            else:
                                record[key] = None
            elif isinstance(data, list):
                # 已经是列表
                data_list = data
            else:
                # 其他类型，尝试转换为列表
                data_list = list(data) if data else []
            
            # 应用字段映射（如果有配置且不是简单模式）
            # 简单模式下，combine_apis_data 已经处理了字段映射，不需要再次应用
            if self.config.get('job_mode') != 'simple':
                data_list = self._apply_field_mapping(data_list)
            
            # 根据插入模式保存数据
            renew_mode = self.get_renew_mode()
            
            # 否则从数据库API中自动获取主键
            primary_key = self.db.get_table_description(table_name)["primaryKey"]
            # 处理单个主键和复合主键的情况
            if isinstance(primary_key, str):
                unique_keys = [primary_key]
            elif isinstance(primary_key, list):
                unique_keys = primary_key
            else:
                raise ValueError(f"表 {table_name} 的主键格式不正确: {primary_key}")
            
            if renew_mode == 'overwrite':
                # 覆盖模式：清空表，写入全量新数据
                # 先清空表
                table_instance.execute_raw_update(f"DELETE FROM {table_name}")
                # 然后插入新数据
                return table_instance.insert(data_list)
            elif renew_mode == 'incremental':
                # 增量模式：追加数据，不删除现有数据
                return table_instance.insert(data_list)
            else:
                # 默认upsert模式：基于唯一键更新或插入
                return table_instance.replace(data_list, unique_keys=unique_keys)
                
        except Exception as e:
            logger.error(f"❌ {self.config['table_name']}数据保存失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")
            return False
    
    def _apply_field_mapping(self, data_list: List[Dict]) -> List[Dict]:
        """应用字段映射"""
        if not data_list:
            return data_list
        
        # 获取第一个 API 的映射配置
        apis = self.config.get('apis', [])
        if not apis or 'mapping' not in apis[0]:
            return data_list
        
        mapping = apis[0]['mapping']
        mapped_data = []
        
        for record in data_list:
            mapped_record = {}
            for db_field, api_field in mapping.items():
                if callable(api_field):
                    # 如果是函数，调用函数进行转换
                    value = api_field(record)
                elif isinstance(api_field, str):
                    # 如果是字符串，直接映射
                    value = record.get(api_field)
                else:
                    # 其他情况，直接使用原值
                    value = api_field
                
                mapped_record[db_field] = value
            
            mapped_data.append(mapped_record)
        return mapped_data
    
    def _get_latest_date(self, table_name: str, date_field: str = 'date') -> str:
        """获取最新数据日期"""
        try:
            table_instance = self.db.get_table_instance(table_name)
            if table_instance and hasattr(table_instance, 'get_latest_date'):
                return table_instance.get_latest_date()
            else:
                return "20080101"  # 默认开始日期
        except Exception as e:
            logger.warning(f"❌ 获取最新日期失败: {e}")
            return "20080101"