#!/usr/bin/env python3
"""
Strategy Settings - 策略配置模型

职责：
- 表示策略配置（直接使用字典，灵活支持用户自定义结构）
"""

from typing import Dict, Any, Optional


class StrategySettings:
    """
    策略配置（基于字典的灵活配置）
    
    用户 settings 结构（新格式）：
    {
        "name": "strategy_name",
        "description": "...",
        "is_enabled": True/False,
        "core": {...},
        "data": {
            "base_price_source": "stock_kline_daily",
            "adjust_type": "qfq",
            "min_required_records": 1000,
            "indicators": {...},
            "extra_data_sources": [...]
        },
        "sampling": {
            "strategy": "random",
            "sampling_amount": 50,
            ...
        },
        "goal": {
            "expiration": {
                "fixed_window_in_days": 30,
                "is_trading_days": True
            },
            "stop_loss": {...},
            "take_profit": {...}
        },
        "simulator": {
            "start_date": "",
            "end_date": "",
            "sot_version": "latest",
            "use_sampling": True,
            "max_workers": "auto"
        },
        "enumerator": {
            "use_sampling": True,
            "max_workers": "auto"
        }
    }
    """
    
    def __init__(self, settings_dict: Dict[str, Any]):
        """
        初始化配置
        
        Args:
            settings_dict: 配置字典
        """
        self._settings = settings_dict
        
        # 基本信息
        self.name = settings_dict.get('name', 'unknown')
        self.description = settings_dict.get('description', '')
        self.is_enabled = settings_dict.get('is_enabled', False)
        
        # 核心配置
        self.core = settings_dict.get('core', {})
        
        # 数据配置（新格式：使用 "data" 字段）
        self.data = settings_dict.get('data', {})
        
        # 采样配置（新格式：顶层 "sampling"）
        self.sampling = settings_dict.get('sampling', {})
        
        # Simulator 配置（新格式：使用 "simulator" 字段）
        self.simulator = settings_dict.get('simulator', {})
        
        # 投资目标配置（提升为顶层配置，跨模块使用）
        # 优先从顶层 goal 读取，如果没有则从 simulator.goal 读取（向后兼容）
        self.goal = settings_dict.get('goal') or self.simulator.get('goal', {})
        
        # 性能配置
        self.performance = settings_dict.get('performance', {})
    
    # =========================================================================
    # 便捷访问属性
    # =========================================================================
    
    @property
    def base_kline_type(self) -> str:
        """基础 K线 类型"""
        return self.data.get('base_price_source', 'stock_kline_daily')
    
    @property
    def min_required_records(self) -> int:
        """最小要求记录数"""
        return self.data.get('min_required_records', 1000)
    
    @property
    def adjust_type(self) -> str:
        """复权类型"""
        return self.data.get('adjust_type', 'qfq')
    
    @property
    def indicators(self) -> Dict[str, Any]:
        """技术指标配置"""
        return self.data.get('indicators', {})
    
    @property
    def required_entities(self) -> list:
        """依赖实体列表"""
        return self.data.get('extra_data_sources', [])
    
    @property
    def start_date(self) -> str:
        """模拟开始日期"""
        return self.simulator.get('start_date', '')
    
    @property
    def end_date(self) -> str:
        """模拟结束日期"""
        return self.simulator.get('end_date', '')
    
    @property
    def sampling_amount(self) -> int:
        """采样数量"""
        return self.sampling.get('sampling_amount', 10)
    
    @property
    def sampling_config(self) -> Dict[str, Any]:
        """采样配置"""
        return self.sampling
    
    @property
    def max_workers(self) -> Any:
        """
        最大进程数（'auto' 或具体数字）
        
        优先级：simulator.max_workers > enumerator.max_workers > performance.max_workers > "auto"
        """
        simulator_cfg = self.simulator or {}
        enumerator_cfg = self.get('enumerator') or {}
        performance_cfg = self.performance or {}
        
        return (
            simulator_cfg.get('max_workers')
            or enumerator_cfg.get('max_workers')
            or performance_cfg.get('max_workers')
            or 'auto'
        )
    
    # =========================================================================
    # 序列化方法
    # =========================================================================
    
    def to_dict(self) -> Dict[str, Any]:
        """转为字典"""
        return self._settings
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StrategySettings':
        """从字典创建"""
        return cls(data)
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置项"""
        return self._settings.get(key, default)
