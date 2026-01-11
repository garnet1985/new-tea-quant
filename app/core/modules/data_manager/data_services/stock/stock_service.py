"""
股票数据服务（StockService）

职责：
- 封装股票相关的跨表查询和数据组装
- 提供领域级的业务方法
- 作为统一入口，协调子服务（kline, tags, corporate_finance）

涉及的表：
- stock_list: 股票列表
- stock_labels: 股票标签
"""
from typing import List, Dict, Any, Optional, Union
from loguru import logger

from .. import BaseDataService


class StockService(BaseDataService):
    """股票数据服务（统一入口）"""
    
    def __init__(self, data_manager: Any):
        """
        初始化股票数据服务
        
        Args:
            data_manager: DataManager 实例
        """
        super().__init__(data_manager)
        
        # 初始化子服务
        from .kline_service import KlineService
        from .tag_service import TagDataService
        from .finance_service import CorporateFinanceService
        
        self.kline = KlineService(data_manager)
        self.tags = TagDataService(data_manager)
        self.corporate_finance = CorporateFinanceService(data_manager)
        
        # 获取相关 Model（股票基础数据）- 私有属性，不对外暴露
        self._stock_list = data_manager.get_model('stock_list')
        self._stock_labels = data_manager.get_model('stock_labels')
        
        # 获取 DatabaseManager 用于复杂 SQL 查询
        from app.core.infra.db import DatabaseManager
        self.db = DatabaseManager.get_default()
    
    # ==================== 股票基础信息 ====================
    
    def load_stock_info(self, stock_id: str) -> Optional[Dict[str, Any]]:
        """
        加载股票基本信息
        
        Args:
            stock_id: 股票代码
            
        Returns:
            股票信息字典，如果不存在返回 None
        """
        return self._stock_list.load_one("id = %s", (stock_id,))
    
    def load_stock_list(
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
            return self.load_filtered_stock_list(exclude_patterns=None, order_by=order_by)
        else:
            return self.load_all_stocks()
    
    def load_all_stocks(self) -> List[Dict[str, Any]]:
        """
        加载所有股票列表
        
        Returns:
            股票列表
        """
        return self._stock_list.load_active_stocks()
    
    def load_filtered_stock_list(
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
            "contains": {
                # 注意：北交所（BJ）不排除（根据用户要求）
            }
        }
        
        # 合并用户自定义规则
        if exclude_patterns:
            exclude = exclude_patterns.copy()
            if "start_with" in exclude_patterns:
                exclude["start_with"] = {
                    **default_exclude["start_with"],
                    **exclude_patterns["start_with"]
                }
            else:
                exclude["start_with"] = default_exclude["start_with"]
            if "contains" in exclude_patterns:
                exclude["contains"] = {
                    **default_exclude["contains"],
                    **exclude_patterns["contains"]
                }
            else:
                exclude["contains"] = default_exclude["contains"]
        else:
            exclude = default_exclude
        
        # 加载所有活跃股票
        all_stocks = self._stock_list.load_active_stocks()
        
        # 应用过滤规则
        filtered_stocks = []
        for stock in all_stocks:
            stock_id = str(stock.get('id', ''))
            stock_name = str(stock.get('name', ''))
            
            should_exclude = False
            
            # 检查 start_with 规则
            for field, patterns in exclude.get("start_with", {}).items():
                value = stock_id if field == "id" else stock_name
                for pattern in patterns:
                    if value.startswith(pattern):
                        should_exclude = True
                        break
                if should_exclude:
                    break
            
            # 检查 contains 规则
            if not should_exclude:
                for field, patterns in exclude.get("contains", {}).items():
                    value = stock_id if field == "id" else stock_name
                    for pattern in patterns:
                        if pattern in value:
                            should_exclude = True
                            break
                    if should_exclude:
                        break
            
            if not should_exclude:
                filtered_stocks.append(stock)
        
        # 排序
        if order_by:
            try:
                filtered_stocks.sort(key=lambda x: x.get(order_by, ''))
            except Exception as e:
                logger.warning(f"排序失败，使用默认排序: {e}")
                filtered_stocks.sort(key=lambda x: x.get('id', ''))
        
        return filtered_stocks
    
    def save_stocks(self, stocks: List[Dict[str, Any]]) -> int:
        """
        批量保存股票列表（自动去重）
        
        Args:
            stocks: 股票数据列表
            
        Returns:
            影响的行数
        """
        return self._stock_list.save_stocks(stocks)
    
    # ==================== K线常用方法（统一入口）====================
    
    def load_klines(
        self,
        stock_id: str,
        term: str = 'daily',
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        adjust: str = 'qfq',
        filter_negative: bool = True,
        as_dataframe: bool = False
    ) -> Union[List[Dict], Any]:
        """
        加载K线数据（常用方法，统一入口）
        
        委托给 KlineService
        
        Args:
            stock_id: 股票代码
            term: 周期（daily/weekly/monthly）
            start_date: 开始日期（YYYYMMDD）
            end_date: 结束日期（YYYYMMDD）
            adjust: 复权方式（qfq前复权/hfq后复权/none不复权）
            filter_negative: 是否过滤负值（默认True，暂不支持）
            as_dataframe: 是否返回DataFrame（默认False返回List[Dict]）
            
        Returns:
            DataFrame or List[Dict]: K线数据
        """
        return self.kline.load(
            stock_id, term, start_date, end_date, adjust, filter_negative, as_dataframe
        )
    
    def load_qfq_klines(
        self,
        stock_id: str,
        term: str = 'daily',
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        加载前复权（QFQ）K线数据（常用方法，统一入口）
        
        委托给 KlineService
        
        Args:
            stock_id: 股票代码
            term: 周期（daily/weekly/monthly，默认 daily）
            start_date: 开始日期（YYYYMMDD 或 YYYY-MM-DD，可选）
            end_date: 结束日期（YYYYMMDD 或 YYYY-MM-DD，可选）
        
        Returns:
            List[Dict]: 前复权K线数据列表
        """
        return self.kline.load_qfq_klines(stock_id, term, start_date, end_date)
    
    def load_multiple_terms(self, stock_id: str, settings: Dict[str, Any]) -> Dict[str, List[Dict]]:
        """
        加载多个周期的K线数据（常用方法，统一入口）
        
        委托给 KlineService
        
        Args:
            stock_id: 股票代码
            settings: 配置字典，包含terms、adjust、allow_negative_records等
            
        Returns:
            Dict[term, List[Dict]]: 各周期的K线数据
        """
        return self.kline.load_multiple_terms(stock_id, settings)
    
    # ==================== 标签常用方法（统一入口）====================
    
    def load_tags(
        self,
        stock_id: str,
        date: Optional[str] = None,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        加载股票标签（常用方法，统一入口）
        
        使用 stock_labels Model 直接加载
        
        Args:
            stock_id: 股票代码
            date: 日期（可选）
            **kwargs: 其他参数
            
        Returns:
            List[Dict]: 标签列表
        """
        if date:
            # 如果指定日期，使用 load_by_date_range 返回该日期范围内的所有标签记录
            return self._stock_labels.load_by_date_range(stock_id, date, date)
        else:
            # 如果没有指定日期，返回该股票的所有标签记录
            return self._stock_labels.load_by_stock(stock_id)
    
    def load_stock_labels_by_date_range(
        self,
        stock_id: str,
        start_date: str,
        end_date: str
    ) -> List[Dict[str, Any]]:
        """
        加载时间范围内的标签（常用方法，统一入口）
        
        使用 stock_labels Model 直接加载
        
        Args:
            stock_id: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            List[Dict]: 标签列表（每条记录包含 date, labels 等字段）
        """
        return self._stock_labels.load_by_date_range(stock_id, start_date, end_date)
    
    # ==================== 财务常用方法（统一入口）====================
    
    def load_corporate_finance(
        self,
        stock_id: str,
        categories: Optional[List[str]] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        加载企业财务数据（常用方法，统一入口）
        
        委托给 CorporateFinanceService.load()
        
        Args:
            stock_id: 股票代码
            categories: 指标类别列表（可选，如 ['profitability', 'growth']）
            start_date: 开始日期（可选）
            end_date: 结束日期（可选）
            
        Returns:
            Dict: 财务数据字典
        """
        return self.corporate_finance.load(stock_id, categories, start_date, end_date)
    
    # ==================== 跨表查询 ====================
    
    def load_stock_with_labels(
        self, 
        stock_id: str, 
        date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        加载股票信息 + 标签（SQL JOIN）
        
        Args:
            stock_id: 股票代码
            date: 日期（可选，如果提供则只查询该日期的标签）
            
        Returns:
            包含股票信息和标签列表的字典
        """
        # 先获取股票信息
        stock_info = self.load_stock_info(stock_id)
        if not stock_info:
            return {}
        
        # 查询标签
        if date:
            labels = self._stock_labels.load(
                "id = %s AND date = %s",
                (stock_id, date)
            )
        else:
            labels = self._stock_labels.load("id = %s", (stock_id,))
        
        stock_info['labels'] = labels
        return stock_info
