#!/usr/bin/env python3
"""
标签数据加载器
"""
from typing import List, Dict, Any, Optional
from utils.date.date_utils import DateUtils
from loguru import logger
from utils.db.db_manager import DatabaseManager
# from utils.db.tables.stock_labels.model import StockLabelModel  # TODO: 迁移到 DataManager


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
        # 不再使用 model，直接使用 db 的 CRUD 方法
        # self.stock_label_model = self.db.get_table_instance('stock_labels')
    
    def get_stock_labels(self, stock_id: str, target_date: Optional[str] = None, max_days_back: int = 90) -> Dict[str, Any]:
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
        
        return self.stock_label_model.get_stock_labels_by_date_range(stock_id, target_date, max_days_back)
    
    def get_stock_labels_by_category(self, stock_id: str, category: str, target_date: Optional[str] = None, max_days_back: int = 90) -> Dict[str, Any]:
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
            # 使用一次性查询获取日期范围内的所有标签记录
            condition = "stock_id = %s AND label_date >= %s AND label_date <= %s"
            params = (stock_id, start_date, end_date)
            order_by = "label_date ASC"
            
            # 一次性查询所有记录
            results = self.stock_label_model.load(condition, params, order_by)
            
            # 解析标签数据
            records = []
            for result in results:
                label_date = result.get('label_date')
                labels_str = result.get('labels', '')
                
                if label_date and labels_str:
                    # 解析标签字符串
                    label_ids = self.stock_label_model._parse_labels_string(labels_str)
                    
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
    
    def batch_save_stock_labels(self, labels_to_save: List[Dict[str, Any]]) -> bool:
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
            return self.stock_label_model.batch_upsert_stock_labels(labels_to_save)
            
        except Exception as e:
            logger.error(f"批量保存股票标签失败: {e}")
            return False
