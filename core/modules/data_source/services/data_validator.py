"""
Data Validator Service

数据验证 Service，负责验证数据是否符合 schema。
"""
from typing import Dict, Any, List, Optional
from loguru import logger


class DataValidator:
    """
    数据验证 Service
    
    职责：
    - 验证数据是否符合 schema
    - 类型检查和转换
    - 错误信息收集
    """
    
    @staticmethod
    def validate(data: Dict, schema) -> bool:
        """
        验证数据是否符合 schema
        
        Args:
            data: 标准化后的数据，通常是 {"data": [...]} 格式
            schema: Schema 对象（用于验证）
        
        Returns:
            bool: 是否符合规范
        """
        if not schema:
            return True
        
        # 如果数据是 {"data": [...]} 格式，验证列表中的每个记录
        if isinstance(data, dict) and "data" in data:
            data_list = data.get("data", [])
            if not isinstance(data_list, list):
                logger.error(f"数据验证失败: data 字段不是列表类型")
                return False
            
            # 验证列表中的每个记录
            for idx, record in enumerate(data_list):
                if not DataValidator.validate_record(record, schema):
                    return False
            return True
        
        # 如果数据不是 {"data": [...]} 格式，直接验证整个字典
        return schema.validate(data)
    
    @staticmethod
    def validate_record(record: Dict[str, Any], schema) -> bool:
        """
        验证单条记录
        
        Args:
            record: 单条记录（字典）
            schema: Schema 对象
        
        Returns:
            bool: 是否符合规范
        """
        if not isinstance(record, dict):
            logger.error(f"数据验证失败: 记录不是字典类型")
            return False
        
        if not schema.validate(record):
            # 收集所有错误信息
            errors = DataValidator.collect_errors(record, schema)
            if errors:
                logger.error(f"数据验证失败: 缺少或无效的字段: {', '.join(errors)}")
            return False
        
        return True
    
    @staticmethod
    def collect_errors(record: Dict[str, Any], schema) -> List[str]:
        """
        收集所有验证错误
        
        Args:
            record: 单条记录（字典）
            schema: Schema 对象
        
        Returns:
            List[str]: 错误信息列表
        """
        errors = []
        
        for field_name, field_def in schema.schema.items():
            if field_def.required and field_name not in record:
                errors.append(f"{field_name}(缺失)")
            elif field_name in record and record[field_name] is not None:
                value = record[field_name]
                expected_type = field_def.type
                if not DataValidator.check_type(value, expected_type):
                    errors.append(f"{field_name}(类型错误: {type(value).__name__} != {expected_type.__name__})")
        
        return errors
    
    @staticmethod
    def check_type(value: Any, expected_type: type) -> bool:
        """
        检查类型（支持类型转换）
        
        Args:
            value: 值
            expected_type: 期望的类型
        
        Returns:
            bool: 是否符合类型（或可以转换）
        """
        if isinstance(value, expected_type):
            return True
        
        # 尝试类型转换
        try:
            if expected_type == int and isinstance(value, (float, str)):
                int(value)
                return True
            elif expected_type == float and isinstance(value, (int, str)):
                float(value)
                return True
            elif expected_type == str:
                str(value)
                return True
        except (ValueError, TypeError):
            return False
        
        return False
