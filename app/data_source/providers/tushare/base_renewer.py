"""
Tushare数据更新基础类
提取公共的renew逻辑，简化代码重复
"""
from datetime import datetime, timedelta
from loguru import logger
from typing import Optional, Callable, Any, Dict, List
from abc import ABC, abstractmethod


class BaseRenewer(ABC):
    """数据更新基础类"""
    
    def __init__(self, db, api, storage, is_verbose: bool = False):
        self.db = db
        self.api = api
        self.storage = storage
        self.is_verbose = is_verbose
    
    def get_latest_date_from_table(self, table_name: str, date_field: str = 'date') -> Optional[str]:
        """
        从指定表获取最新日期
        
        Args:
            table_name: 表名
            date_field: 日期字段名
            
        Returns:
            最新日期字符串，格式为YYYYMMDD，如果没有数据则返回None
        """
        try:
            with self.db.get_sync_cursor() as cursor:
                cursor.execute(f'SELECT MAX({date_field}) as latest_date FROM {table_name}')
                result = cursor.fetchone()
                return result['latest_date'] if result and result['latest_date'] else None
        except Exception as e:
            logger.warning(f"获取{table_name}最新数据日期失败: {e}")
            return None
    
    def should_renew_data(self, latest_date: Optional[str], end_date: str) -> tuple[bool, Optional[str]]:
        """
        判断是否需要更新数据
        
        Args:
            latest_date: 数据库中的最新日期
            end_date: 目标结束日期
            
        Returns:
            (是否需要更新, 开始日期)
        """
        if not latest_date:
            # 没有现有数据，从默认开始日期获取
            start_date = self.get_default_start_date()
            return True, start_date
        
        # 特殊处理：季度格式如 2025Q2，不产生告警，直接按需要更新处理
        if isinstance(latest_date, str) and 'Q' in latest_date:
            return True, self.get_default_start_date()

        try:
            # 处理datetime对象
            if isinstance(latest_date, datetime):
                formatted_latest_date = latest_date
            else:
                formatted_latest_date = datetime.strptime(latest_date, '%Y%m%d')
            
            formatted_end_date = datetime.strptime(end_date, '%Y%m%d')
            
            if formatted_latest_date >= formatted_end_date:
                return False, None
            
            # 需要更新，从最新日期的下一天开始
            start_date = (formatted_latest_date + timedelta(days=1)).strftime('%Y%m%d')
            return True, start_date
            
        except ValueError as e:
            # 静默处理不符合YYYYMMDD的日期（如季度、月份等），避免打断统一日志风格
            return True, self.get_default_start_date()
    
    def get_default_start_date(self) -> str:
        """获取默认开始日期"""
        try:
            from app.conf.conf import data_default_start_date
            return data_default_start_date
        except Exception:
            return "20080101"
    
    def renew_simple_data(
        self, 
        table_name: str,
        api_method: Callable,
        data_converter: Callable,
        end_date: str,
        date_field: str = 'date',
        primary_keys: Optional[List[str]] = None,
        api_kwargs: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        简单的数据更新方法（适用于单表、单API调用的场景）
        
        Args:
            table_name: 目标表名
            api_method: API调用方法
            data_converter: 数据转换方法
            end_date: 结束日期
            date_field: 日期字段名
            primary_keys: 主键列表，用于upsert
            api_kwargs: API调用的额外参数
            
        Returns:
            是否更新成功
        """
        logger.info(f"📊 开始更新{table_name}数据，目标日期: {end_date}")
        
        # 获取现有数据的最新日期
        latest_date = self.get_latest_date_from_table(table_name, date_field)
        
        # 判断是否需要更新
        should_renew, start_date = self.should_renew_data(latest_date, end_date)
        
        if not should_renew:
            logger.info(f"⏭️ {table_name}数据已是最新，跳过更新")
            return True
        
        logger.info(f"🔄 更新{table_name}数据从 {start_date} 到 {end_date}")
        
        try:
            # 准备API调用参数
            api_params = {
                'start_date': start_date,
                'end_date': end_date
            }
            if api_kwargs:
                api_params.update(api_kwargs)
            
            # 调用API获取数据
            df_data = api_method(**api_params)
            
            if df_data is not None and not df_data.empty:
                # 转换数据
                converted_data = data_converter(df_data)
                
                if converted_data:
                    # 保存到数据库
                    table = self.db.get_table_instance(table_name)
                    if primary_keys:
                        table.replace(converted_data, primary_keys)
                    else:
                        # 如果没有指定主键，尝试使用date作为主键
                        table.replace(converted_data, [date_field])
                    
                    logger.info(f"✅ {table_name}数据更新完成，共 {len(converted_data)} 条记录")
                    return True
                else:
                    logger.warning(f"⚠️ {table_name}数据转换后为空")
                    return False
            else:
                logger.warning(f"⚠️ 没有获取到{table_name}数据")
                return False
                
        except Exception as e:
            logger.error(f"❌ 获取{table_name}数据失败: {e}")
            return False
    
    def renew_multi_table_data(
        self,
        table_configs: List[Dict[str, Any]],
        end_date: str
    ) -> bool:
        """
        多表数据更新方法（适用于需要更新多个相关表的场景）
        
        Args:
            table_configs: 表配置列表，每个配置包含table_name, api_method, data_converter等
            end_date: 结束日期
            
        Returns:
            是否全部更新成功
        """
        success_count = 0
        total_count = len(table_configs)
        
        for config in table_configs:
            try:
                success = self.renew_simple_data(
                    table_name=config['table_name'],
                    api_method=config['api_method'],
                    data_converter=config['data_converter'],
                    end_date=end_date,
                    date_field=config.get('date_field', 'date'),
                    primary_keys=config.get('primary_keys'),
                    api_kwargs=config.get('api_kwargs', {})
                )
                if success:
                    success_count += 1
            except Exception as e:
                logger.error(f"❌ 更新{config['table_name']}失败: {e}")
        
        logger.info(f"📊 多表数据更新完成: {success_count}/{total_count} 成功")
        return success_count == total_count
    
    @abstractmethod
    def renew(self, latest_market_open_day: str = None) -> bool:
        """
        抽象方法，子类必须实现具体的更新逻辑
        
        Args:
            latest_market_open_day: 最新交易日
            
        Returns:
            是否更新成功
        """
        pass


class SimpleDataRenewer(BaseRenewer):
    """简单数据更新器，适用于单表单API的场景"""
    
    def __init__(
        self, 
        db, 
        api, 
        storage, 
        table_name: str,
        api_method: Callable,
        data_converter: Callable,
        date_field: str = 'date',
        primary_keys: Optional[List[str]] = None,
        api_kwargs: Optional[Dict[str, Any]] = None,
        is_verbose: bool = False
    ):
        super().__init__(db, api, storage, is_verbose)
        self.table_name = table_name
        self.api_method = api_method
        self.data_converter = data_converter
        self.date_field = date_field
        self.primary_keys = primary_keys
        self.api_kwargs = api_kwargs or {}
    
    def renew(self, latest_market_open_day: str = None) -> bool:
        """实现简单数据更新"""
        return self.renew_simple_data(
            table_name=self.table_name,
            api_method=self.api_method,
            data_converter=self.data_converter,
            end_date=latest_market_open_day,
            date_field=self.date_field,
            primary_keys=self.primary_keys,
            api_kwargs=self.api_kwargs
        )


class MultiTableDataRenewer(BaseRenewer):
    """多表数据更新器，适用于需要更新多个相关表的场景"""
    
    def __init__(
        self, 
        db, 
        api, 
        storage, 
        table_configs: List[Dict[str, Any]],
        is_verbose: bool = False
    ):
        super().__init__(db, api, storage, is_verbose)
        self.table_configs = table_configs
    
    def renew(self, latest_market_open_day: str = None) -> bool:
        """实现多表数据更新"""
        return self.renew_multi_table_data(
            table_configs=self.table_configs,
            end_date=latest_market_open_day
        )
