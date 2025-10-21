#!/usr/bin/env python3
"""
设置验证器组件 - 验证策略设置的完整性和正确性
"""
from typing import Dict, List, Any, Optional, Tuple
from loguru import logger


class SettingsValidator:
    """设置验证器 - 验证策略设置的完整性和正确性"""
    
    def __init__(self):
        """初始化设置验证器"""
        self.required_fields = {
            # 支持新的配置结构：signal_base_term 和 simulate_base_term
            # 如果存在新配置，则不需要 base_term
        }
        
        self.optional_fields = {
            'klines.additional_terms': list,  # 额外周期，如 ['weekly', 'monthly']
            'goal': dict,                     # 投资目标配置
            'mode': dict,                     # 模式配置（向后兼容）
            'simulation': dict,               # 新的模拟配置
            'core': dict,                     # 核心策略参数
            'macro': dict,                    # 宏观经济数据配置
            'corporate_finance': dict,        # 公司财务数据配置
            'index_indicators': dict,         # 指数指标配置
            'industry_capital_flow': dict,    # 行业资本流动配置
        }
        
        from app.data_source.enums import KlineTerm
        self.valid_base_terms = [term.value for term in KlineTerm if term != KlineTerm.YEARLY]
        self.valid_additional_terms = [term.value for term in KlineTerm]
    
    def validate_settings(self, settings: Dict[str, Any], strategy_name: str = "Unknown") -> Tuple[bool, List[str]]:
        """
        验证策略设置
        
        Args:
            settings: 策略设置字典
            strategy_name: 策略名称（用于日志）
            
        Returns:
            Tuple[bool, List[str]]: (是否有效, 错误信息列表)
        """
        errors = []


        # step1: settings must be a dictionary variable called settings
        if not settings:
            errors.append(f"Settings is not set, need to create a file called settings.py in the strategy root folder.")
            return False, errors

        
        # step2: validate required fields
        errors.extend(self._validate_required_fields(settings))
        
        # step2.5: validate new klines configuration structure
        errors.extend(self._validate_klines_configuration(settings))
        
        # step3: validate field types and values
        errors.extend(self._validate_field_types(settings))
        errors.extend(self._validate_field_values(settings))
        
        # step4: validate field dependencies
        errors.extend(self._validate_field_dependencies(settings))
        
        is_valid = len(errors) == 0
        
        if is_valid:
            logger.info(f"✅ {strategy_name} 策略设置验证通过")
        else:
            logger.error(f"❌ {strategy_name} 策略设置验证失败:")
            for error in errors:
                logger.error(f"   - {error}")
        
        return is_valid, errors
    
    def _validate_required_fields(self, settings: Dict[str, Any]) -> List[str]:
        """验证必需字段"""
        errors = []
        
        for field_path, field_type in self.required_fields.items():
            if '.' in field_path:
                # 嵌套字段，如 'klines.signal_base_term'
                parent_key, child_key = field_path.split('.', 1)
                if parent_key not in settings:
                    errors.append(f"Missing required field: {parent_key}")
                elif not isinstance(settings[parent_key], dict):
                    errors.append(f"Field '{parent_key}' must be a dictionary")
                elif child_key not in settings[parent_key]:
                    errors.append(f"Missing required field: {field_path}")
            else:
                # 顶级字段
                if field_path not in settings:
                    errors.append(f"Missing required field: {field_path}")
        
        return errors
    
    def _validate_klines_configuration(self, settings: Dict[str, Any]) -> List[str]:
        """
        验证新的klines配置结构
        支持配置方式：signal_base_term + simulate_base_term
        """
        errors = []
        
        if 'klines' not in settings or not isinstance(settings['klines'], dict):
            return errors
        
        klines = settings['klines']
        has_new_config = 'signal_base_term' in klines or 'simulate_base_term' in klines
        
        # 检查是否有有效的配置，如果没有则设置默认值
        if not has_new_config:
            # 设置默认值
            klines['signal_base_term'] = 'daily'
            klines['simulate_base_term'] = 'daily'
        
        # 确保simulate_base_term有默认值
        if 'simulate_base_term' not in klines:
            klines['simulate_base_term'] = klines.get('signal_base_term', 'daily')
        
        # 验证signal_base_term
        signal_term = klines['signal_base_term']
        if not isinstance(signal_term, str):
            errors.append("klines.signal_base_term must be a string")
        elif signal_term not in self.valid_base_terms:
            errors.append(f"Invalid signal_base_term '{signal_term}', must be one of: {self.valid_base_terms}")
        
        # 验证simulate_base_term
        simulate_term = klines['simulate_base_term']
        if not isinstance(simulate_term, str):
            errors.append("klines.simulate_base_term must be a string")
        elif simulate_term not in self.valid_base_terms:
            errors.append(f"Invalid simulate_base_term '{simulate_term}', must be one of: {self.valid_base_terms}")
        
        # 验证signal_base_term和simulate_base_term必须在terms列表中
        terms = klines.get('terms', [])
        if not isinstance(terms, list):
            errors.append("klines.terms must be a list")
        else:
            if signal_term not in terms:
                errors.append(f"signal_base_term '{signal_term}' must be included in klines.terms: {terms}")
            if simulate_term not in terms:
                errors.append(f"simulate_base_term '{simulate_term}' must be included in klines.terms: {terms}")
        
        return errors
    
    def _validate_field_types(self, settings: Dict[str, Any]) -> List[str]:
        """验证字段类型"""
        errors = []
        
        # 验证必需字段类型
        for field_path, expected_type in self.required_fields.items():
            if '.' in field_path:
                parent_key, child_key = field_path.split('.', 1)
                if (parent_key in settings and 
                    isinstance(settings[parent_key], dict) and 
                    child_key in settings[parent_key]):
                    actual_value = settings[parent_key][child_key]
                    if not isinstance(actual_value, expected_type):
                        errors.append(f"Field '{field_path}' must be {expected_type.__name__}, got {type(actual_value).__name__}")
            else:
                if field_path in settings:
                    actual_value = settings[field_path]
                    if not isinstance(actual_value, expected_type):
                        errors.append(f"Field '{field_path}' must be {expected_type.__name__}, got {type(actual_value).__name__}")
        
        # 验证可选字段类型
        for field_path, expected_type in self.optional_fields.items():
            if '.' in field_path:
                parent_key, child_key = field_path.split('.', 1)
                if (parent_key in settings and 
                    isinstance(settings[parent_key], dict) and 
                    child_key in settings[parent_key]):
                    actual_value = settings[parent_key][child_key]
                    if not isinstance(actual_value, expected_type):
                        errors.append(f"Field '{field_path}' must be {expected_type.__name__}, got {type(actual_value).__name__}")
            else:
                if field_path in settings:
                    actual_value = settings[field_path]
                    if not isinstance(actual_value, expected_type):
                        errors.append(f"Field '{field_path}' must be {expected_type.__name__}, got {type(actual_value).__name__}")
        
        return errors
    
    def _validate_field_values(self, settings: Dict[str, Any]) -> List[str]:
        """验证字段值"""
        errors = []
        
        # 验证新的配置字段值
        if 'klines' in settings and isinstance(settings['klines'], dict):
            klines = settings['klines']
            
            if 'signal_base_term' in klines:
                signal_term = klines['signal_base_term']
                if signal_term not in self.valid_base_terms:
                    errors.append(f"Invalid signal_base_term '{signal_term}', must be one of: {self.valid_base_terms}")
            
            if 'simulate_base_term' in klines:
                simulate_term = klines['simulate_base_term']
                if simulate_term not in self.valid_base_terms:
                    errors.append(f"Invalid simulate_base_term '{simulate_term}', must be one of: {self.valid_base_terms}")
            
            # 验证additional_terms值
            if 'additional_terms' in klines and isinstance(klines['additional_terms'], list):
                for term in klines['additional_terms']:
                    if term not in self.valid_additional_terms:
                        errors.append(f"Invalid additional_term '{term}', must be one of: {self.valid_additional_terms}")
        return errors
    
    def _validate_field_dependencies(self, settings: Dict[str, Any]) -> List[str]:
        """验证字段依赖关系"""
        errors = []
        
        # 验证additional_terms不能包含signal_base_term
        if ('klines' in settings and isinstance(settings['klines'], dict) and
            'signal_base_term' in settings['klines'] and 'additional_terms' in settings['klines']):
            klines = settings['klines']
            signal_base_term = klines['signal_base_term']
            additional_terms = klines['additional_terms']
            
            if isinstance(additional_terms, list) and signal_base_term in additional_terms:
                errors.append(f"additional_terms cannot contain signal_base_term '{signal_base_term}'")
        
        return errors
    
    def get_default_settings(self) -> Dict[str, Any]:
        """
        获取默认设置模板
        
        Returns:
            Dict: 默认设置模板
        """
        return {
            'klines': {
                'signal_base_term': 'daily',
                'simulate_base_term': 'daily',
                'additional_terms': []
            },
            'goal': {},
            'mode': {}
        }
    
    def merge_with_defaults(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        """
        将用户设置与默认设置合并
        
        Args:
            settings: 用户设置
            
        Returns:
            Dict: 合并后的设置
        """
        default_settings = self.get_default_settings()
        
        # 深度合并
        merged_settings = self._deep_merge(default_settings, settings)
        
        return merged_settings
    
    def _deep_merge(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """深度合并字典"""
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        
        return result
