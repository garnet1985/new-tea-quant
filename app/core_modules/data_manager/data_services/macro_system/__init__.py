"""
宏观/系统数据服务

包含：
- 宏观经济指标（GDP、CPI、PPI、PMI、货币供应量）
- 利率数据（Shibor、LPR）
- 交易日历、元信息（待实现）
"""

from typing import Optional, Dict, Any
from .. import BaseDataService
from .macro.macro_data_service import MacroDataService


class MacroSystemDataService(BaseDataService):
    """
    宏观/系统数据的统一接口
    
    当前作为转发器，未来可以添加大类内的组合查询方法。
    """
    
    def __init__(self, data_manager):
        super().__init__(data_manager)
        self.macro_service: Optional[MacroDataService] = None
        self.meta_service = None  # 待实现
    
    def initialize(self):
        """初始化所有子 Service"""
        self.macro_service = MacroDataService(self.data_manager)
        # self.meta_service = MetaDataService(self.data_manager)
    
    # ========== 转发方法 ==========
    
    def load_gdp(self, *args, **kwargs):
        """转发到 MacroDataService"""
        return self.macro_service.load_gdp(*args, **kwargs)
    
    def load_cpi(self, *args, **kwargs):
        """转发到 MacroDataService"""
        return self.macro_service.load_cpi(*args, **kwargs)
    
    def load_ppi(self, *args, **kwargs):
        """转发到 MacroDataService"""
        return self.macro_service.load_ppi(*args, **kwargs)
    
    def load_pmi(self, *args, **kwargs):
        """转发到 MacroDataService"""
        return self.macro_service.load_pmi(*args, **kwargs)
    
    def load_money_supply(self, *args, **kwargs):
        """转发到 MacroDataService"""
        return self.macro_service.load_money_supply(*args, **kwargs)
    
    def load_shibor(self, *args, **kwargs):
        """转发到 MacroDataService"""
        return self.macro_service.load_shibor(*args, **kwargs)
    
    def load_lpr(self, *args, **kwargs):
        """转发到 MacroDataService"""
        return self.macro_service.load_lpr(*args, **kwargs)
    
    def load_risk_free_rate(self, *args, **kwargs):
        """转发到 MacroDataService"""
        return self.macro_service.load_risk_free_rate(*args, **kwargs)
    
    def load_macro_snapshot(self, *args, **kwargs):
        """转发到 MacroDataService"""
        return self.macro_service.load_macro_snapshot(*args, **kwargs)


__all__ = ['MacroSystemDataService']

