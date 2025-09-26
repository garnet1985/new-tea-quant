"""
通用数据更新器
支持简单模式和多线程模式，通过配置驱动
"""
from typing import Dict, List, Any, Optional, Callable, Union
from datetime import datetime, timedelta
from loguru import logger
from app.data_source.providers.tushare.base_renewer import BaseRenewer
from app.data_source.providers.tushare.main_service import TushareService
from utils.worker import FuturesWorker, ThreadExecutionMode
from utils.icon.icon_service import IconService


class UniversalRenewer(BaseRenewer):
    """通用数据更新器"""
    
    def __init__(
        self,
        db,
        api,
        storage,
        config: Dict[str, Any],
        is_verbose: bool = False
    ):
        super().__init__(db, api, storage, is_verbose)
        self.config = config
        self._validate_config()
    
    def _validate_config(self):
        """验证配置参数"""
        required_fields = ['table_name', 'api_method', 'field_mapping', 'primary_keys']
        for field in required_fields:
            if field not in self.config:
                raise ValueError(f"配置中缺少必需字段: {field}")
        
        # 验证API方法
        if not hasattr(self.api, self.config['api_method']):
            raise ValueError(f"API中不存在方法: {self.config['api_method']}")
    
    def renew(self, latest_market_open_day: str = None):
        """
        通用数据更新方法
        
        Args:
            latest_market_open_day: 最新交易日
            
        Returns:
            bool: 是否更新成功
        """
        mode = self.config.get('mode', 'simple')
        
        if mode == 'simple':
            return self._renew_simple(latest_market_open_day)
        elif mode == 'multithread':
            return self._renew_multithread(latest_market_open_day)
        else:
            raise ValueError(f"不支持的模式: {mode}")
    
    def _renew_simple(self, latest_market_open_day: str = None):
        """简单模式更新"""
        logger.info(f"开始更新 {self.config['table_name']}")
        
        # 1. 检查最新数据，决定renew的start date
        start_date = self._get_start_date(latest_market_open_day)
        if start_date is None:
            logger.info(f"{IconService.get('check')} {self.config['table_name']} 无新数据")
            # 检查是否需要返回数据
            if self.config.get('return_data', False):
                return self._get_return_data()
            return True
        
        # 2. 访问API获取数据
        logger.info(f"{self.config['table_name']} 更新中")
        api_data = self._fetch_api_data(start_date, latest_market_open_day)
        if api_data is None:
            logger.error(f"{IconService.get('cross')} API调用失败，无法获取{self.config['table_name']}数据")
            return False
        
        # 检查DataFrame是否为空
        if hasattr(api_data, 'empty') and api_data.empty:
            logger.info(f"{IconService.get('check')} {self.config['table_name']} 无新数据")
            # 检查是否需要返回数据
            if self.config.get('return_data', False):
                return self._get_return_data()
            return True  # 没有新数据是正常的业务情况，返回True表示成功
        
        # 3. 完成entity的build，写入数据库
        return self._save_data(api_data)
    
    def _renew_multithread(self, latest_market_open_day: str = None):
        """多线程模式更新"""
        logger.info(f"开始更新 {self.config['table_name']}")
        
        # 1. 检查最新数据，决定renew的start date
        start_date = self._get_start_date(latest_market_open_day)
        if start_date is None:
            logger.info(f"{IconService.get('check')} {self.config['table_name']} 无新数据")
            return True
        
        # 2. 构建多线程任务
        jobs = self._build_multithread_jobs(start_date, latest_market_open_day)
        if not jobs:
            logger.info(f"{IconService.get('check')} {self.config['table_name']} 无新数据")
            return True
        
        # 3. 执行多线程任务
        logger.info(f"{self.config['table_name']} 更新中")
        return self._execute_multithread_jobs(jobs)
    
    def _get_start_date(self, latest_market_open_day: str) -> Optional[str]:
        """
        检查最新数据，决定renew的start date
        
        Returns:
            str: 开始日期，如果不需要更新则返回None
        """
        table_name = self.config['table_name']
        date_field = self.config.get('date_field', 'date')
        
        # 获取现有数据的最新日期
        latest_date = self.get_latest_date_from_table(table_name, date_field)
        
        # 判断是否需要更新
        should_renew, start_date = self.should_renew_data(latest_date, latest_market_open_day)
        
        if not should_renew:
            return None
        
        return start_date
    
    def _fetch_api_data(self, start_date: str, end_date: str):
        """
        访问API获取数据
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            API返回的数据
        """
        api_method_name = self.config['api_method']
        api_method = getattr(self.api, api_method_name)
        
        # 构建API参数
        api_params = self._build_api_params(start_date, end_date)
        
        try:
            return api_method(**api_params)
        except Exception as e:
            msg = str(e)
            if any(k in msg for k in ["查询数据失败", "无数据", "no data", "空数据", "not found"]):
                try:
                    import pandas as pd
                    return pd.DataFrame()
                except Exception:
                    return []
            logger.error(f"❌ API调用失败: {e}")
            return None
    
    def _build_api_params(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """
        构建API参数
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            API参数字典
        """
        # 基础参数
        params = {
            'start_date': start_date,
            'end_date': end_date
        }
        
        # 添加配置中的额外参数
        if 'api_params' in self.config:
            params.update(self.config['api_params'])
        
        # 处理特殊参数
        if 'date_param_mapping' in self.config:
            mapping = self.config['date_param_mapping']
            if 'start' in mapping:
                params[mapping['start']] = start_date
                del params['start_date']
            if 'end' in mapping:
                params[mapping['end']] = end_date
                del params['end_date']
        
        return params
    
    def _save_data(self, api_data) -> bool:
        """
        完成entity的build，写入数据库
        
        Args:
            api_data: API返回的数据
            
        Returns:
            bool: 是否保存成功
        """
        if api_data is None:
            return False
        
        # 处理DataFrame的情况
        if hasattr(api_data, 'empty'):
            if api_data.empty:
                return False
        elif isinstance(api_data, list) and len(api_data) == 0:
            return False
        
        # 转换数据
        converted_data = self._convert_data(api_data)
        if not converted_data:
            logger.info(f"ℹ️ {self.config['table_name']}数据转换后为空，没有有效数据需要保存")
            return True  # 转换后为空可能是正常的业务情况
        
        # 保存到数据库
        try:
            table = self.db.get_table_instance(self.config['table_name'])
            primary_keys = self.config['primary_keys']
            table.replace(converted_data, primary_keys)
            logger.info(f"{IconService.get('success')} {self.config['table_name']} 更新完毕")
            
            # 检查是否需要返回数据
            if self.config.get('return_data', False):
                return self._get_return_data()
            return True
        except Exception as e:
            logger.error(f"❌ {self.config['table_name']}数据保存失败: {e}")
            return False
    
    def _convert_data(self, api_data) -> List[Dict]:
        """
        转换API数据为数据库格式
        
        Args:
            api_data: API返回的数据
            
        Returns:
            转换后的数据列表
        """
        # 如果配置中有自定义的data_converter，优先使用
        if 'data_converter' in self.config:
            try:
                converter_func = self.config['data_converter']
                return converter_func(api_data)
            except Exception as e:
                logger.warning(f"使用自定义转换器失败: {e}")
        
        # 默认转换逻辑
        # 确保数据是列表格式
        if hasattr(api_data, 'to_dict'):
            data_list = api_data.to_dict('records')
        elif isinstance(api_data, list):
            data_list = api_data
        else:
            data_list = [api_data]
        
        field_mapping = self.config['field_mapping']
        converted_data = []
        
        for item in data_list:
            try:
                converted_item = {}
                for target_field, source_field in field_mapping.items():
                    if callable(source_field):
                        # 如果source_field是函数，则调用函数处理
                        converted_item[target_field] = source_field(item)
                    else:
                        # 直接映射字段
                        converted_item[target_field] = item.get(source_field, '')
                
                # 应用数据过滤
                if 'data_filter' in self.config:
                    filter_func = self.config['data_filter']
                    if not filter_func(converted_item):
                        continue
                
                converted_data.append(converted_item)
                
            except Exception as e:
                logger.warning(f"转换数据时出错: {e}")
                continue
        
        return converted_data
    
    def _build_multithread_jobs(self, start_date: str, end_date: str) -> List[Dict]:
        """
        构建多线程任务
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            任务列表
        """
        # 这里需要根据具体的数据类型来实现
        # 例如：股票K线数据需要为每只股票创建任务
        # 企业财务数据需要为每只股票每个季度创建任务
        
        if 'job_builder' in self.config:
            job_builder = self.config['job_builder']
            return job_builder(start_date, end_date)
        else:
            # 默认简单任务
            return [{
                'start_date': start_date,
                'end_date': end_date,
                'api_method': self.config['api_method'],
                'api_params': self.config.get('api_params', {})
            }]
    
    def _execute_multithread_jobs(self, jobs: List[Dict]) -> bool:
        """
        执行多线程任务
        
        Args:
            jobs: 任务列表
            
        Returns:
            bool: 是否执行成功
        """
        if not jobs:
            return True
        
        # 创建多线程工作器
        worker = FuturesWorker(
            max_workers=self.config.get('max_workers', 4),
            execution_mode=ThreadExecutionMode.PARALLEL
        )
        
        # 设置任务执行器
        worker.set_job_executor(self._execute_single_job)
        
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
        """
        执行单个任务
        
        Args:
            job: 任务配置
            
        Returns:
            bool: 是否执行成功
        """
        try:
            # 获取数据
            api_data = self._fetch_api_data(job['start_date'], job['end_date'])
            if api_data is None:
                logger.error(f"❌ 多线程任务API调用失败")
                return False
            
            # 检查DataFrame是否为空
            if hasattr(api_data, 'empty') and api_data.empty:
                logger.info(f"ℹ️ 多线程任务在指定日期范围内没有新数据")
                return True  # 没有新数据是正常的业务情况
            
            # 保存数据
            return self._save_data(api_data)
            
        except Exception as e:
            logger.error(f"执行任务失败: {e}")
            return False
    
    def _get_return_data(self):
        """
        获取返回数据（用于需要返回数据的场景）
        """
        # 检查是否有自定义的返回数据获取器
        if 'return_data_getter' in self.config:
            getter_func = self.config['return_data_getter']
            return getter_func(self)
        
        # 默认从数据库加载数据
        try:
            table = self.db.get_table_instance(self.config['table_name'])
            # 这里可以根据需要实现具体的数据获取逻辑
            return table.load_all()
        except Exception as e:
            logger.error(f"❌ 获取返回数据失败: {e}")
            return None
    
    def _load_stock_index_data(self):
        """
        加载股票指数数据（用于stock_index的返回数据获取）
        """
        try:
            # 从main_storage获取数据
            from app.data_source.providers.tushare.main_storage import TushareStorage
            storage = TushareStorage(self.db)
            return storage.load_stock_index()
        except Exception as e:
            logger.error(f"❌ 加载股票指数数据失败: {e}")
            return None
