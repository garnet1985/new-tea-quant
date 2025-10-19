#!/usr/bin/env python3
"""
数据加载服务 - 重构版本（Proxy模式）

职责：
- 作为统一的数据加载API入口
- 将具体功能委托给子loaders处理
- 提供统一的配置和常量管理

架构：
- DataLoader: 主入口，统一API（Proxy模式）
- KlineLoader: K线数据专用加载器
- LabelLoader: 标签数据专用加载器
- Config: 统一配置管理
- Enums: 枚举类型定义
- DateUtils: 日期工具类
"""
from typing import Dict, List, Any, Optional, Union
import pandas as pd
from loguru import logger

from .loaders import KlineLoader
from .loaders import LabelLoader
from app.conf.conf import data_default_start_date
from app.data_source.enums import KlineTerm, AdjustType
from utils.date.date_utils import DateUtils


class DataLoader:
    """
    数据加载服务（Proxy模式）
    
    职责：
    - 作为统一的数据加载API入口
    - 将具体功能委托给子loaders处理
    - 提供统一的配置和常量管理
    
    使用方式：
        from app.data_loader import DataLoader
        from utils.db.db_manager import DatabaseManager
        
        # 方式1：外部传入DatabaseManager实例（推荐，支持连接池共享）
        db = DatabaseManager(use_connection_pool=True)
        db.initialize()
        loader = DataLoader(db)
        
        # 方式2：DataLoader自行创建DatabaseManager（向后兼容）
        loader = DataLoader()
        
        data = loader.prepare_data(stock, planner_settings)
    """
    
    def __init__(self, db=None):
        """
        初始化数据加载器（Proxy模式）
        
        Args:
            db: DatabaseManager实例，如果为None则自行创建
               外部应用可以传入自己的DatabaseManager实例以共享连接池
        
        注意：子loaders共享同一个DatabaseManager实例和连接池
        """
        if db is not None:
            # 使用外部传入的DatabaseManager实例（推荐，支持更高层级的连接池共享）
            self.db = db
        else:
            # 自行创建DatabaseManager实例（向后兼容）
            from utils.db.db_manager import DatabaseManager
            self.db = DatabaseManager(use_connection_pool=True)
            self.db.initialize()
        
        # 子loaders使用共享的DatabaseManager实例
        self.kline_loader = KlineLoader(self.db)
        self.label_loader = LabelLoader(self.db)
    
    def prepare_data(self, stock: Dict[str, Any], settings: Dict[str, Any]) -> Dict[str, Any]:
        """
        准备所有需要的数据（聚合方法）
        
        用于策略分析，一次性加载所有需要的数据
        
        Args:
            stock: 股票信息
            settings: 数据设置（包含klines、macro、corporate_finance等配置）
            
        Returns:
            Dict: {
                'klines': {...},
                'macro': {...},
                'corporate_finance': {...},
                'labels': {...},
                ...
            }
        """
        data = {}
        stock_id = stock.get('id')
        
        # 1. 加载K线数据
        klines_settings = settings.get("klines")
        if klines_settings:
            data["klines"] = self.kline_loader.load_multiple_terms(stock_id, klines_settings)
            
            # 确保返回dict类型
            if not isinstance(data.get("klines"), dict):
                data["klines"] = {}
            
            # 加载股票标签数据（如果配置）
            if klines_settings.get('stock_labels', False):
                data["stock_labels"] = self._load_stock_labels_data_for_simulation(stock_id, klines_settings)
            
            # 应用技术指标（如果配置）
            if data["klines"] and klines_settings.get('indicators'):
                from app.analyzer.components.indicators import Indicators
                data["klines"] = Indicators.add_indicators(data["klines"], klines_settings['indicators'])
        
        # 2. 加载宏观数据
        macro_settings = settings.get("macro")
        if macro_settings:
            data["macro"] = self._load_macro_data(macro_settings)
        
        # 3. 加载企业财务数据
        corporate_finance_settings = settings.get("corporate_finance")
        if corporate_finance_settings:
            data["corporate_finance"] = self._load_corporate_finance_data(stock_id, corporate_finance_settings)
        
        # 4. 加载指数指标数据
        index_indicators_settings = settings.get("index_indicators")
        if index_indicators_settings:
            data["index_indicators"] = self._load_index_indicators_data(index_indicators_settings)
        
        # 5. 加载行业资金流数据
        industry_capital_flow_settings = settings.get("industry_capital_flow")
        if industry_capital_flow_settings:
            data["industry_capital_flow"] = self._load_industry_capital_flow_data(industry_capital_flow_settings)
        
        return data
    
    def _load_stock_labels_data_for_simulation(self, stock_id: str, klines_settings: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
        """
        为模拟器加载股票标签数据（一次性加载所有历史标签，按日期升序）
        
        Args:
            stock_id: 股票代码
            klines_settings: K线设置（包含模拟时间范围等信息）
            
        Returns:
            Dict: 按日期分组的标签数据，格式为 {date: [label_objects]}
        """
        try:
            # 获取模拟时间范围
            simulation_settings = klines_settings.get('simulation', {})
            start_date = simulation_settings.get('start_date')
            end_date = simulation_settings.get('end_date')
            
            # 验证必要的时间范围配置
            if not start_date:
                raise ValueError("模拟时间范围配置缺失：start_date")
            if not end_date:
                end_date = DateUtils.get_current_date_str()  # 只有end_date可以使用当前日期作为默认值
            
            # 一次性获取时间范围内的所有标签数据
            all_labels = self.label_loader.get_stock_labels_by_date_range(stock_id, start_date, end_date)
            
            # 按日期分组标签数据，只保存标签ID
            labels_by_date = {}
            for label_record in all_labels:
                date = label_record.get('date')
                label_id = label_record.get('label_id')
                if date and label_id:
                    if date not in labels_by_date:
                        labels_by_date[date] = []
                    labels_by_date[date].append(label_id)
            
            # 按日期排序
            sorted_labels = dict(sorted(labels_by_date.items()))
            
            return sorted_labels
            
        except Exception as e:
            logger.error(f"加载股票标签数据失败 {stock_id}: {e}")
            return {}
    
    @staticmethod
    def filter_labels_by_category(all_labels: List[str], target_categories: List[str]) -> Dict[str, List[str]]:
        """
        静态方法：按标签种类过滤标签
        
        Args:
            all_labels: 所有标签ID列表
            target_categories: 目标标签种类列表（如 ['market_cap', 'volatility']）
            
        Returns:
            Dict: 按种类分组的标签，格式为 {category: [label_ids]}
        """
        try:
            from app.labeler.conf.label_mapping import LabelMapping
            label_mapping = LabelMapping()
            
            filtered_labels = {}
            for category in target_categories:
                # 获取该分类的所有可能标签
                category_labels = label_mapping.get_labels_by_category(category)
                if category_labels:
                    # 过滤出属于该分类的标签
                    category_filtered = []
                    for label in all_labels:
                        if label in category_labels:
                            category_filtered.append(label)
                    filtered_labels[category] = category_filtered
            
            return filtered_labels
            
        except Exception as e:
            logger.error(f"按种类过滤标签失败: {e}")
            return {}
    
    # ============ 标签相关方法 ============
    
    def get_stock_labels(self, stock_id: str, target_date: Optional[str] = None) -> List[str]:
        """
        获取股票在指定日期的标签
        
        Args:
            stock_id: 股票代码
            target_date: 目标日期 (YYYY-MM-DD)，None表示当前日期
            
        Returns:
            List[str]: 标签ID列表
        """
        return self.label_loader.get_stock_labels(stock_id, target_date)
    
    def save_stock_labels(self, stock_id: str, label_date: str, labels: List[str]):
        """
        保存股票标签
        
        Args:
            stock_id: 股票代码
            label_date: 标签日期 (YYYY-MM-DD)
            labels: 标签ID列表
        """
        return self.label_loader.save_stock_labels(stock_id, label_date, labels)
    
    def get_stocks_with_label(self, label_id: str, target_date: Optional[str] = None) -> List[str]:
        """
        获取具有指定标签的股票列表
        
        Args:
            label_id: 标签ID
            target_date: 目标日期 (YYYY-MM-DD)，None表示当前日期
            
        Returns:
            List[str]: 股票代码列表
        """
        return self.label_loader.get_stocks_with_label(label_id, target_date)
    
    def get_label_statistics(self, target_date: Optional[str] = None) -> Dict[str, Any]:
        """
        获取标签统计信息
        
        Args:
            target_date: 目标日期 (YYYY-MM-DD)，None表示当前日期
            
        Returns:
            Dict: 统计信息
        """
        return self.label_loader.get_label_statistics(target_date)
    
    # ============ 私有方法（委托给子loaders）============
    
    def _load_macro_data(self, macro_settings: Dict[str, Any]) -> Dict[str, Any]:
        """加载宏观数据（委托给KlineLoader）"""
        return self.kline_loader.load_macro_data(macro_settings)
    
    def _load_corporate_finance_data(self, stock_id: str, corporate_finance_settings: Dict[str, Any]) -> Dict[str, Any]:
        """加载企业财务数据（委托给KlineLoader）"""
        return self.kline_loader.load_corporate_finance_data(stock_id, corporate_finance_settings)
    
    def _load_index_indicators_data(self, index_indicators_settings: Dict[str, Any]) -> Dict[str, Any]:
        """加载指数指标数据（委托给KlineLoader）"""
        return self.kline_loader.load_index_indicators_data(index_indicators_settings)
    
    def _load_industry_capital_flow_data(self, industry_capital_flow_settings: Dict[str, Any]) -> Dict[str, Any]:
        """加载行业资金流数据（委托给KlineLoader）"""
        return self.kline_loader.load_industry_capital_flow_data(industry_capital_flow_settings)
    
    def load_stock_list(self, 
                       filtered: bool = False,
                       industry: str = None,
                       stock_type: str = None,
                       exchange_center: str = None,
                       order_by: str = 'id') -> List[Dict[str, Any]]:
        """
        加载股票列表
        
        Args:
            filtered: 是否使用过滤规则加载（默认False，排除ST、科创板等）
            industry: 按行业过滤（可选）
            stock_type: 按股票类型过滤（可选）
            exchange_center: 按交易所过滤（可选）
            order_by: 排序字段
            
        Returns:
            List[Dict]: 股票列表
            
        示例：
            # 加载过滤后的股票列表（默认，推荐）
            stocks = loader.load_stock_list(filtered=True)
            
            # 加载所有股票（不过滤）
            stocks = loader.load_stock_list(filtered=False)
            
            # 加载特定行业
            stocks = loader.load_stock_list(industry='银行')
            
            # 加载特定交易所
            stocks = loader.load_stock_list(exchange_center='SSE')
        """
        # 使用缓存的数据库实例获取股票列表
        table = self.db.get_table_instance('stock_list')
        
        # 优先使用简单条件过滤（性能更好）
        if industry:
            return table.load_by_industry(industry, order_by)
        elif stock_type:
            return table.load_by_type(stock_type, order_by)
        elif exchange_center:
            return table.load_by_exchange_center(exchange_center, order_by)
        elif filtered:
            # 使用过滤规则（默认行为）
            return table.load_filtered_stock_list(exclude_patterns=None, order_by=order_by)
        else:
            # 加载所有活跃股票（不过滤）
            return table.load_all_active(order_by)
    
    def load_klines(self, stock_id: str, term: str = 'daily',
                    start_date: Optional[str] = None, end_date: Optional[str] = None,
                    adjust: str = 'qfq', filter_negative: bool = True,
                    as_dataframe: bool = False) -> Union[pd.DataFrame, List[Dict]]:
        """
        加载K线数据（委托给KlineLoader）
        
        Args:
            stock_id: 股票代码
            term: 周期（daily/weekly/monthly）
            start_date: 开始日期（YYYYMMDD）
            end_date: 结束日期（YYYYMMDD）
            adjust: 复权方式（qfq前复权/hfq后复权/none不复权）
            filter_negative: 是否过滤负值（默认True）
            as_dataframe: 是否返回DataFrame（默认False返回List[Dict]）
            
        Returns:
            DataFrame or List[Dict]: K线数据
        """
        return self.kline_loader.load(
            stock_id, term, start_date, end_date, adjust, filter_negative, as_dataframe
        )
