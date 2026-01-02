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
from utils.date.date_utils import DateUtils

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
    
    def get_stock_labels(
        self, 
        stock_id: str, 
        target_date: Optional[str] = None, 
        max_days_back: int = 90
    ) -> Dict[str, Any]:
        """
        获取股票在指定日期的标签，带时间阈值限制
        
        Args:
            stock_id: 股票代码
            target_date: 目标日期 (YYYY-MM-DD)，None表示当前日期
            max_days_back: 最大回退天数，默认90天
            
        Returns:
            Dict包含:
            - labels: 标签列表
            - label_date: 标签实际日期
            - days_back: 回退天数
            - is_valid: 是否在阈值内
        """
        if target_date is None:
            target_date = DateUtils.get_current_date_str(DateUtils.DATE_FORMAT_YYYY_MM_DD)
        
        return self.stock_labels.get_stock_labels_by_date_range(stock_id, target_date, max_days_back)
    
    def get_stock_labels_by_category(
        self, 
        stock_id: str, 
        category: str, 
        target_date: Optional[str] = None, 
        max_days_back: int = 90
    ) -> Dict[str, Any]:
        """
        获取股票在指定日期的特定分类标签，带时间阈值限制
        
        Args:
            stock_id: 股票代码
            category: 标签分类（如 market_cap, industry, volatility 等）
            target_date: 目标日期 (YYYY-MM-DD)，None表示当前日期
            max_days_back: 最大回退天数，默认90天
            
        Returns:
            Dict包含:
            - labels: 该分类的标签列表
            - label_date: 标签实际日期
            - days_back: 回退天数
            - is_valid: 是否在阈值内
        """
        try:
            # 获取所有标签
            label_info = self.get_stock_labels(stock_id, target_date, max_days_back)
            
            # 从标签定义中获取该分类的所有可能标签
            from app.labeler.conf.label_mapping import LabelMapping
            label_mapping = LabelMapping()
            category_labels = label_mapping.get_labels_by_category(category)
            
            # 过滤出属于该分类的标签
            filtered_labels = []
            for label in label_info['labels']:
                if label in category_labels:
                    filtered_labels.append(label)
            
            # 返回相同结构的信息，但只包含特定分类的标签
            return {
                'labels': filtered_labels,
                'label_date': label_info['label_date'],
                'days_back': label_info['days_back'],
                'is_valid': label_info['is_valid']
            }
            
        except Exception as e:
            logger.error(f"获取股票分类标签失败 {stock_id} {category}: {e}")
            return {
                'labels': [],
                'label_date': None,
                'days_back': None,
                'is_valid': False
            }
    
    def get_stock_labels_by_date_range(
        self, 
        stock_id: str, 
        start_date: str, 
        end_date: str
    ) -> List[Dict[str, Any]]:
        """
        获取股票在指定日期范围内的所有标签记录
        
        Args:
            stock_id: 股票代码
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            
        Returns:
            List[Dict]: 标签记录列表，格式为 [{'date': 'YYYY-MM-DD', 'label_id': 'label_id'}, ...]
        """
        try:
            # 使用一次性查询获取日期范围内的所有标签记录
            condition = "stock_id = %s AND label_date >= %s AND label_date <= %s"
            params = (stock_id, start_date, end_date)
            order_by = "label_date ASC"
            
            # 一次性查询所有记录
            results = self.stock_labels.load(condition, params, order_by)
            
            # 解析标签数据
            records = []
            for result in results:
                label_date = result.get('label_date')
                labels_str = result.get('labels', '')
                
                if label_date and labels_str:
                    # 解析标签字符串
                    label_ids = self.stock_labels._parse_labels_string(labels_str)
                    
                    # 格式化日期
                    if isinstance(label_date, str):
                        formatted_date = label_date
                    else:
                        # 如果是datetime.date对象，转换为字符串
                        formatted_date = label_date.strftime('%Y-%m-%d')
                    
                    # 为每个标签ID创建记录
                    for label_id in label_ids:
                        records.append({
                            'date': formatted_date,
                            'label_id': label_id
                        })
            
            return records
            
        except Exception as e:
            logger.error(f"获取股票标签记录失败 {stock_id} {start_date}-{end_date}: {e}")
            return []
    
    def save_stock_labels(self, stock_id: str, label_date: str, labels: List[str]):
        """
        保存股票标签
        
        Args:
            stock_id: 股票代码
            label_date: 标签日期 (YYYY-MM-DD)
            labels: 标签ID列表
        """
        try:
            success = self.stock_labels.upsert_stock_label(stock_id, label_date, labels)
            if success:
                logger.debug(f"保存股票标签成功: {stock_id}, {label_date}, {labels}")
            else:
                logger.error(f"保存股票标签失败: {stock_id}, {label_date}")
                
        except Exception as e:
            logger.error(f"保存股票标签失败: {stock_id}, {label_date}, {e}")
    
    def get_stocks_with_label(
        self, 
        label_id: str, 
        target_date: Optional[str] = None
    ) -> List[str]:
        """
        获取具有指定标签的股票列表
        
        Args:
            label_id: 标签ID
            target_date: 目标日期 (YYYY-MM-DD)，None表示当前日期
            
        Returns:
            List[str]: 股票代码列表
        """
        if target_date is None:
            target_date = DateUtils.get_current_date_str(DateUtils.DATE_FORMAT_YYYY_MM_DD)
        
        return self.stock_labels.get_stocks_with_label(label_id, target_date)
    
    def get_label_statistics(
        self, 
        target_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取标签统计信息
        
        Args:
            target_date: 目标日期 (YYYY-MM-DD)，None表示当前日期
            
        Returns:
            Dict: 标签统计信息
        """
        if target_date is None:
            target_date = DateUtils.get_current_date_str(DateUtils.DATE_FORMAT_YYYY_MM_DD)
        
        return self.stock_labels.get_label_statistics(target_date)
    
    def get_all_stocks_last_update_dates(
        self, 
        stock_ids: List[str]
    ) -> Dict[str, str]:
        """
        批量获取所有股票的最后更新时间
        
        Args:
            stock_ids: 股票代码列表
            
        Returns:
            Dict[str, str]: 股票代码 -> 最后更新日期的映射
        """
        return self.stock_labels.get_all_stocks_last_update_dates(stock_ids)
    
    def upsert_stock_label(
        self, 
        stock_id: str, 
        target_date: str, 
        labels: List[str]
    ) -> bool:
        """
        插入或更新股票标签记录
        
        Args:
            stock_id: 股票代码
            target_date: 目标日期
            labels: 标签列表
            
        Returns:
            bool: 是否成功
        """
        return self.stock_labels.upsert_stock_label(stock_id, target_date, labels)
    
    def get_stock_labels_by_date(
        self, 
        stock_id: str, 
        target_date: str
    ) -> List[str]:
        """
        获取指定股票在指定日期的标签
        
        Args:
            stock_id: 股票代码
            target_date: 目标日期
            
        Returns:
            List[str]: 标签列表
        """
        return self.stock_labels.get_stock_labels_by_date(stock_id, target_date)
    
    def batch_save_stock_labels(
        self, 
        labels_to_save: List[Dict[str, Any]]
    ) -> bool:
        """
        批量保存股票标签记录
        
        Args:
            labels_to_save: 要保存的标签数据列表，每个元素包含：
                - stock_id: 股票代码
                - label_date: 标签日期
                - labels: 标签列表
                
        Returns:
            bool: 是否成功
        """
        try:
            if not labels_to_save:
                return True
            
            # 批量保存到数据库
            return self.stock_labels.batch_upsert_stock_labels(labels_to_save)
            
        except Exception as e:
            logger.error(f"批量保存股票标签失败: {e}")
            return False


__all__ = ['LabelDataService']

