"""
通用更新器管理器
管理所有数据类型的更新器实例
"""
from typing import Dict, Any
from .universal_renewer import UniversalRenewer
from .configs import CONFIG_MAP


class UniversalRenewerManager:
    """通用更新器管理器"""
    
    def __init__(self, db, api, storage, is_verbose: bool = False):
        self.db = db
        self.api = api
        self.storage = storage
        self.is_verbose = is_verbose
        self._renewers = {}
    
    def get_renewer(self, data_type: str) -> UniversalRenewer:
        """
        获取指定数据类型的更新器
        
        Args:
            data_type: 数据类型名称
            
        Returns:
            UniversalRenewer: 更新器实例
        """
        if data_type not in self._renewers:
            if data_type not in CONFIG_MAP:
                raise ValueError(f"不支持的数据类型: {data_type}")
            
            config = CONFIG_MAP[data_type]
            self._renewers[data_type] = UniversalRenewer(
                db=self.db,
                api=self.api,
                storage=self.storage,
                config=config,
                is_verbose=self.is_verbose
            )
        
        return self._renewers[data_type]
    
    def renew(self, data_type: str, latest_market_open_day: str = None) -> bool:
        """
        更新指定数据类型
        
        Args:
            data_type: 数据类型名称
            latest_market_open_day: 最新交易日
            
        Returns:
            bool: 是否更新成功
        """
        renewer = self.get_renewer(data_type)
        return renewer.renew(latest_market_open_day)
    
    def renew_all(self, data_types: list, latest_market_open_day: str = None) -> Dict[str, bool]:
        """
        批量更新多种数据类型
        
        Args:
            data_types: 数据类型列表
            latest_market_open_day: 最新交易日
            
        Returns:
            Dict[str, bool]: 各数据类型的更新结果
        """
        results = {}
        for data_type in data_types:
            try:
                results[data_type] = self.renew(data_type, latest_market_open_day)
            except Exception as e:
                print(f"更新 {data_type} 失败: {e}")
                results[data_type] = False
        
        return results
    
    def get_supported_types(self) -> list:
        """
        获取支持的数据类型列表
        
        Returns:
            list: 支持的数据类型列表
        """
        return list(CONFIG_MAP.keys())
