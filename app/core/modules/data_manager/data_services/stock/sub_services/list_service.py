"""
股票列表服务（ListService）

职责：
- 提供股票列表相关的查询和操作
- 支持全量股票列表、过滤股票列表等功能
- 支持按类型、行业等条件筛选股票

涉及的表：
- stock_list: 股票列表
"""
from typing import List, Dict, Any, Optional
from loguru import logger

from ... import BaseDataService


class ListService(BaseDataService):
    """股票列表服务"""
    
    def __init__(self, data_manager: Any):
        """
        初始化股票列表服务
        
        Args:
            data_manager: DataManager 实例
        """
        super().__init__(data_manager)
        
        # 获取相关 Model（股票基础数据）- 私有属性，不对外暴露
        self._stock_list = data_manager.get_table('stock_list')
    
    # ==================== 股票列表查询 ====================
    
    def load(
        self,
        filtered: bool = True,
        order_by: str = 'id'
    ) -> List[Dict[str, Any]]:
        """
        加载股票列表
        
        Args:
            filtered: 是否使用过滤规则（默认True，排除ST、科创板等）
            order_by: 排序字段（默认 'id'）
            
        Returns:
            List[Dict]: 股票列表
        """
        if filtered:
            return self.load_filtered(exclude_patterns=None, order_by=order_by)
        else:
            return self.load_all()
    
    def load_all(self) -> List[Dict[str, Any]]:
        """
        加载所有股票列表
        
        Returns:
            股票列表
        """
        return self._stock_list.load_active_stocks()
    
    def load_filtered(
        self, 
        exclude_patterns: Optional[Dict[str, List[str]]] = None,
        order_by: str = 'id'
    ) -> List[Dict[str, Any]]:
        """
        加载过滤后的股票列表（排除ST、科创板等）
        
        默认过滤规则：
        - 排除 id 以 "688" 开头的（科创板）
        - 排除 name 以 "*ST"、"ST"、"退" 开头的（ST股票和退市股票）
        - 注意：北交所（BJ）不排除（根据用户要求）
        
        Args:
            exclude_patterns: 自定义排除规则（可选）
            order_by: 排序字段（默认 'id'）
            
        Returns:
            List[Dict]: 过滤后的股票列表
        """
        # 默认过滤规则
        default_exclude = {
            "start_with": {
                "id": ["688"],  # 科创板
                "name": ["*ST", "ST", "退"]  # ST股票和退市股票
            },
            "contains": {}
        }
        
        # 合并用户自定义规则
        exclude = self._merge_exclude_patterns(default_exclude, exclude_patterns)
        
        # 加载所有活跃股票
        all_stocks = self._stock_list.load_active_stocks()
        
        # 应用过滤规则
        filtered_stocks = [
            stock for stock in all_stocks
            if not self._should_exclude_stock(stock, exclude)
        ]
        
        # 排序
        return self._sort_stocks(filtered_stocks, order_by)
    
    def load_by_type(
        self,
        stock_type: str,
        filtered: bool = True,
        order_by: str = 'id'
    ) -> List[Dict[str, Any]]:
        """
        按类型加载股票列表
        
        Args:
            stock_type: 股票类型（如 'main', 'gem', 'star' 等，具体类型取决于数据库字段）
            filtered: 是否使用过滤规则（默认True）
            order_by: 排序字段（默认 'id'）
            
        Returns:
            List[Dict]: 指定类型的股票列表
        """
        # 先获取基础列表
        if filtered:
            stocks = self.load_filtered(exclude_patterns=None, order_by=order_by)
        else:
            stocks = self.load_all()
        
        # 按类型过滤（如果 stock_list 表有 type 字段）
        # 注意：这里假设有 type 字段，如果没有，需要根据实际数据库结构调整
        filtered_by_type = [
            stock for stock in stocks
            if stock.get('type') == stock_type
        ]
        
        return self._sort_stocks(filtered_by_type, order_by)
    
    def load_by_industry(
        self,
        industry: str,
        filtered: bool = True,
        order_by: str = 'id'
    ) -> List[Dict[str, Any]]:
        """
        按行业加载股票列表
        
        Args:
            industry: 行业名称
            filtered: 是否使用过滤规则（默认True）
            order_by: 排序字段（默认 'id'）
            
        Returns:
            List[Dict]: 指定行业的股票列表
        """
        # 先获取基础列表
        if filtered:
            stocks = self.load_filtered(exclude_patterns=None, order_by=order_by)
        else:
            stocks = self.load_all()
        
        # 按行业过滤
        filtered_by_industry = [
            stock for stock in stocks
            if stock.get('industry') == industry
        ]
        
        return self._sort_stocks(filtered_by_industry, order_by)
    
    def save(self, stocks: List[Dict[str, Any]]) -> int:
        """
        批量保存股票列表（自动去重）
        
        Args:
            stocks: 股票数据列表
            
        Returns:
            影响的行数
        """
        return self._stock_list.save_stocks(stocks)
    
    # ==================== 私有方法 ====================
    
    def _merge_exclude_patterns(
        self,
        default_exclude: Dict[str, Dict[str, List[str]]],
        exclude_patterns: Optional[Dict[str, List[str]]]
    ) -> Dict[str, Dict[str, List[str]]]:
        """
        合并默认过滤规则和用户自定义规则
        
        Args:
            default_exclude: 默认过滤规则
            exclude_patterns: 用户自定义规则
            
        Returns:
            合并后的过滤规则
        """
        if not exclude_patterns:
            return default_exclude
        
        exclude = exclude_patterns.copy()
        
        # 合并 start_with 规则
        if "start_with" in exclude_patterns:
            exclude["start_with"] = {
                **default_exclude["start_with"],
                **exclude_patterns["start_with"]
            }
        else:
            exclude["start_with"] = default_exclude["start_with"]
        
        # 合并 contains 规则
        if "contains" in exclude_patterns:
            exclude["contains"] = {
                **default_exclude["contains"],
                **exclude_patterns["contains"]
            }
        else:
            exclude["contains"] = default_exclude["contains"]
        
        return exclude
    
    def _should_exclude_stock(
        self,
        stock: Dict[str, Any],
        exclude: Dict[str, Dict[str, List[str]]]
    ) -> bool:
        """
        判断股票是否应该被排除
        
        Args:
            stock: 股票数据字典
            exclude: 过滤规则
            
        Returns:
            是否应该排除
        """
        stock_id = str(stock.get('id', ''))
        stock_name = str(stock.get('name', ''))
        
        # 检查 start_with 规则
        for field, patterns in exclude.get("start_with", {}).items():
            value = stock_id if field == "id" else stock_name
            if any(value.startswith(pattern) for pattern in patterns):
                return True
        
        # 检查 contains 规则
        for field, patterns in exclude.get("contains", {}).items():
            value = stock_id if field == "id" else stock_name
            if any(pattern in value for pattern in patterns):
                return True
        
        return False
    
    def _sort_stocks(self, stocks: List[Dict[str, Any]], order_by: str) -> List[Dict[str, Any]]:
        """
        对股票列表进行排序
        
        Args:
            stocks: 股票列表
            order_by: 排序字段
            
        Returns:
            排序后的股票列表
        """
        if not order_by:
            return stocks
        
        try:
            stocks.sort(key=lambda x: x.get(order_by, ''))
        except Exception as e:
            logger.warning(f"排序失败，使用默认排序: {e}")
            stocks.sort(key=lambda x: x.get('id', ''))
        
        return stocks
