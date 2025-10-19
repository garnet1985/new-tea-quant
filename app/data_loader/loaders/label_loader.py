#!/usr/bin/env python3
"""
标签数据加载器
"""
from typing import List, Dict, Any, Optional
from utils.date.date_utils import DateUtils
from loguru import logger
from utils.db.db_manager import DatabaseManager
from utils.db.tables.stock_labels.model import StockLabelModel


class LabelLoader:
    """
    标签数据加载器
    
    职责：
    - 股票标签的读写操作
    - 标签定义的查询
    - 批量标签计算和保存
    """
    
    def __init__(self, db=None):
        """
        初始化标签加载器
        
        Args:
            db: DatabaseManager实例，如果为None则自行创建
        """
        if db is not None:
            # 使用外部传入的DatabaseManager实例（推荐，共享连接池）
            self.db = db
        else:
            # 自行管理DatabaseManager（向后兼容）
            from utils.db.db_manager import DatabaseManager
            self.db = DatabaseManager()
        self.db.initialize()
        self.stock_label_model = self.db.get_table_instance('stock_labels')
    
    def get_stock_labels(self, stock_id: str, target_date: Optional[str] = None) -> List[str]:
        """
        获取股票在指定日期的标签
        
        Args:
            stock_id: 股票代码
            target_date: 目标日期 (YYYY-MM-DD)，None表示当前日期
            
        Returns:
            List[str]: 标签ID列表
        """
        if target_date is None:
            target_date = DateUtils.get_current_date_str(DateUtils.DATE_FORMAT_YYYY_MM_DD)
        
        return self.stock_label_model.get_stock_labels_by_date_range(stock_id, target_date)
    
    def get_stock_labels_by_category(self, stock_id: str, category: str, target_date: Optional[str] = None) -> List[str]:
        """
        获取股票在指定日期的特定分类标签
        
        Args:
            stock_id: 股票代码
            category: 标签分类（如 market_cap, industry, volatility 等）
            target_date: 目标日期 (YYYY-MM-DD)，None表示当前日期
            
        Returns:
            List[str]: 该分类的标签ID列表
        """
        try:
            # 获取所有标签
            all_labels = self.get_stock_labels(stock_id, target_date)
            
            # 从标签定义中获取该分类的所有可能标签
            from app.labeler.conf.label_mapping import LabelMapping
            label_mapping = LabelMapping()
            category_labels = label_mapping.get_labels_by_category(category)
            
            # 过滤出属于该分类的标签
            filtered_labels = []
            for label in all_labels:
                if label in category_labels:
                    filtered_labels.append(label)
            
            return filtered_labels
            
        except Exception as e:
            logger.error(f"获取股票分类标签失败 {stock_id} {category}: {e}")
            return []
    
    def get_stock_labels_by_date_range(self, stock_id: str, start_date: str, end_date: str) -> List[Dict[str, Any]]:
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
            # 由于数据库模型只支持单个日期查询，我们需要获取多个日期的标签
            records = []
            
            # 生成日期范围
            from utils.date.date_utils import DateUtils
            date_list = DateUtils.generate_date_range(start_date, end_date)
            
            for date_str in date_list:
                # 获取该日期的标签
                labels = self.stock_label_model.get_stock_labels_by_date_range(stock_id, date_str)
                if labels:
                    for label_id in labels:
                        records.append({
                            'date': date_str,
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
            success = self.stock_label_model.upsert_stock_label(stock_id, label_date, labels)
            if success:
                logger.debug(f"保存股票标签成功: {stock_id}, {label_date}, {labels}")
            else:
                logger.error(f"保存股票标签失败: {stock_id}, {label_date}")
            
        except Exception as e:
            logger.error(f"保存股票标签失败: {stock_id}, {label_date}, {e}")
    
    def batch_calculate_labels(self, stock_ids: List[str], label_date: str, 
                              calculator_func: callable):
        """
        批量计算并保存股票标签
        
        Args:
            stock_ids: 股票代码列表
            label_date: 标签日期 (YYYY-MM-DD)
            calculator_func: 标签计算函数，接收(stock_id, target_date)返回标签列表
        """
        logger.info(f"开始批量计算标签: {len(stock_ids)}只股票, 日期: {label_date}")
        
        success_count = 0
        error_count = 0
        
        for stock_id in stock_ids:
            try:
                # 计算标签
                labels = calculator_func(stock_id, label_date)
                
                # 保存标签
                self.save_stock_labels(stock_id, label_date, labels)
                success_count += 1
                
                if success_count % 100 == 0:
                    logger.info(f"已处理: {success_count}/{len(stock_ids)}")
                    
            except Exception as e:
                logger.error(f"计算股票标签失败: {stock_id}, {e}")
                error_count += 1
        
        logger.info(f"批量计算标签完成: 成功{success_count}个, 失败{error_count}个")
    
    def get_stocks_with_label(self, label_id: str, target_date: Optional[str] = None) -> List[str]:
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
        
        return self.stock_label_model.get_stocks_with_label(label_id, target_date)
    
    def get_label_statistics(self, target_date: Optional[str] = None) -> Dict[str, Any]:
        """
        获取标签统计信息
        
        Args:
            target_date: 目标日期 (YYYY-MM-DD)，None表示当前日期
            
        Returns:
            Dict: 标签统计信息
        """
        if target_date is None:
            target_date = DateUtils.get_current_date_str(DateUtils.DATE_FORMAT_YYYY_MM_DD)
        
        return self.stock_label_model.get_label_statistics(target_date)
    
    def get_all_stocks_last_update_dates(self, stock_ids: List[str]) -> Dict[str, str]:
        """
        批量获取所有股票的最后更新时间
        
        Args:
            stock_ids: 股票代码列表
            
        Returns:
            Dict[str, str]: 股票代码 -> 最后更新日期的映射
        """
        return self.stock_label_model.get_all_stocks_last_update_dates(stock_ids)
    
    def upsert_stock_label(self, stock_id: str, target_date: str, labels: List[str]) -> bool:
        """
        插入或更新股票标签记录
        
        Args:
            stock_id: 股票代码
            target_date: 目标日期
            labels: 标签列表
            
        Returns:
            bool: 是否成功
        """
        return self.stock_label_model.upsert_stock_label(stock_id, target_date, labels)
    
    def get_stock_labels_by_date(self, stock_id: str, target_date: str) -> List[str]:
        """
        获取指定股票在指定日期的标签
        
        Args:
            stock_id: 股票代码
            target_date: 目标日期
            
        Returns:
            List[str]: 标签列表
        """
        return self.stock_label_model.get_stock_labels_by_date(stock_id, target_date)
