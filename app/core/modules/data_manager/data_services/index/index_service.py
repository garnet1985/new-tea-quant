"""
指数数据服务（IndexService）

职责：
- 封装指数指标相关的查询和数据操作
- 提供指数指标和指数成分股权重的访问接口

涉及的表：
- stock_index_indicator: 指数指标数据
- stock_index_indicator_weight: 指数成分股权重数据
"""
from typing import List, Dict, Any, Optional
from loguru import logger

from .. import BaseDataService


class IndexService(BaseDataService):
    """指数数据服务"""
    
    def __init__(self, data_manager: Any):
        """
        初始化指数数据服务
        
        Args:
            data_manager: DataManager 实例
        """
        super().__init__(data_manager)
        
        # 获取相关 Model - 私有属性，不对外暴露
        self._stock_index_indicator = data_manager.get_table('stock_index_indicator')
        self._stock_index_indicator_weight = data_manager.get_table('stock_index_indicator_weight')
        
        # 获取 DatabaseManager 用于复杂 SQL 查询
        from app.core.infra.db import DatabaseManager
        self.db = DatabaseManager.get_default()
    
    # ==================== 指数指标数据 ====================
    
    def load_indicator(
        self,
        index_id: str,
        term: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        加载指数指标数据
        
        Args:
            index_id: 指数ID
            term: 周期（daily, weekly, monthly），如果为 None 则返回所有周期
            start_date: 开始日期（YYYYMMDD）
            end_date: 结束日期（YYYYMMDD）
            
        Returns:
            指数指标数据列表
        """
        conditions = ["id = %s"]
        params = [index_id]
        
        if term:
            conditions.append("term = %s")
            params.append(term)
        
        if start_date:
            conditions.append("date >= %s")
            params.append(start_date)
        
        if end_date:
            conditions.append("date <= %s")
            params.append(end_date)
        
        where_clause = " AND ".join(conditions)
        return self._stock_index_indicator.load(
            where_clause,
            tuple(params),
            order_by="date ASC, term ASC"
        )
    
    def load_latest_indicator(self, index_id: str, term: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        加载最新的指数指标数据
        
        Args:
            index_id: 指数ID
            term: 周期（daily, weekly, monthly），如果为 None 则返回所有周期的最新数据
            
        Returns:
            最新的指数指标数据，如果不存在返回 None
        """
        if term:
            return self._stock_index_indicator.load_one(
                "id = %s AND term = %s",
                (index_id, term),
                order_by="date DESC"
            )
        else:
            # 返回所有周期的最新数据
            return self._stock_index_indicator.load_one(
                "id = %s",
                (index_id,),
                order_by="date DESC, term ASC"
            )
    
    def save_indicator(self, indicator_data: List[Dict[str, Any]]) -> int:
        """
        批量保存指数指标数据（自动去重）
        
        Args:
            indicator_data: 指数指标数据列表
            
        Returns:
            影响的行数
        """
        return self._stock_index_indicator.replace(
            indicator_data,
            unique_keys=["id", "term", "date"]
        )
    
    # ==================== 指数成分股权重数据 ====================
    
    def load_weight(
        self,
        index_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        加载指数成分股权重数据
        
        Args:
            index_id: 指数ID
            start_date: 开始日期（YYYYMMDD）
            end_date: 结束日期（YYYYMMDD）
            
        Returns:
            指数成分股权重数据列表
        """
        conditions = ["id = %s"]
        params = [index_id]
        
        if start_date:
            conditions.append("date >= %s")
            params.append(start_date)
        
        if end_date:
            conditions.append("date <= %s")
            params.append(end_date)
        
        where_clause = " AND ".join(conditions)
        return self._stock_index_indicator_weight.load(
            where_clause,
            tuple(params),
            order_by="date ASC, stock_id ASC"
        )
    
    def load_latest_weight(self, index_id: str) -> Optional[Dict[str, Any]]:
        """
        加载最新的指数成分股权重数据
        
        Args:
            index_id: 指数ID
            
        Returns:
            最新的指数成分股权重数据，如果不存在返回 None
        """
        return self._stock_index_indicator_weight.load_one(
            "id = %s",
            (index_id,),
            order_by="date DESC"
        )
    
    def save_weight(self, weight_data: List[Dict[str, Any]]) -> int:
        """
        批量保存指数成分股权重数据（自动去重）
        
        Args:
            weight_data: 指数成分股权重数据列表
            
        Returns:
            影响的行数
        """
        return self._stock_index_indicator_weight.replace(
            weight_data,
            unique_keys=["id", "date", "stock_id"]
        )
    
    # ==================== 批量查询方法 ====================
    
    def load_latest_indicators_by_term(
        self,
        index_ids: Optional[List[str]] = None
    ) -> Dict[str, Dict[str, str]]:
        """
        批量查询所有指数在多个周期的最新日期
        
        Args:
            index_ids: 指数ID列表，如果为 None 则查询所有指数
            
        Returns:
            {index_id: {term: latest_date}} 格式的字典
        """
        if not self._stock_index_indicator:
            return {}
        
        # 使用批量查询：一次性获取所有指数的所有周期的最新记录
        all_latest_records = self._stock_index_indicator.load_latest_records(
            date_field='date',
            primary_keys=['id', 'term']  # 按 id 和 term 分组
        )
        
        # 构建结果字典
        result = {}
        for record in all_latest_records:
            index_id = record.get('id')
            term = record.get('term')
            latest_date = record.get('date')
            
            if not index_id or not term or not latest_date:
                continue
            
            # 如果指定了 index_ids，只返回匹配的指数
            if index_ids and index_id not in index_ids:
                continue
            
            if index_id not in result:
                result[index_id] = {}
            result[index_id][term] = latest_date
        
        return result
    
    def load_latest_weights(
        self,
        index_ids: Optional[List[str]] = None
    ) -> Dict[str, str]:
        """
        批量查询所有指数的最新权重日期
        
        Args:
            index_ids: 指数ID列表，如果为 None 则查询所有指数
            
        Returns:
            {index_id: latest_date} 格式的字典
        """
        if not self._stock_index_indicator_weight:
            return {}
        
        # 使用批量查询：一次性获取所有指数的最新记录
        all_latest_records = self._stock_index_indicator_weight.load_latest_records(
            date_field='date',
            primary_keys=['id']  # 按指数ID分组
        )
        
        # 构建结果字典
        result = {}
        for record in all_latest_records:
            index_id = record.get('id')
            latest_date = record.get('date')
            
            if not index_id or not latest_date:
                continue
            
            # 如果指定了 index_ids，只返回匹配的指数
            if index_ids and index_id not in index_ids:
                continue
            
            result[index_id] = latest_date
        
        return result
