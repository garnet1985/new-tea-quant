"""
标签数据服务（LabelDataService）

职责：
- 封装股票标签相关的查询和数据操作
- 提供领域级的业务方法

涉及的表：
- stock_labels: 股票标签
"""
from typing import List, Dict, Any, Optional
from loguru import logger
from app.core.utils.date.date_utils import DateUtils

from ... import BaseDataService


class LabelDataService(BaseDataService):
    """标签数据服务"""
    
    def __init__(self, data_manager: Any):
        """
        初始化标签数据服务
        
        Args:
            data_manager: DataManager 实例
        """
        super().__init__(data_manager)
        
        # 获取相关 Model（通过 DataManager，自动绑定默认 db）
        self.stock_labels = data_manager.get_model('stock_labels')

__all__ = ['LabelDataService']

