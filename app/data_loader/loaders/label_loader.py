#!/usr/bin/env python3
"""
标签数据加载器
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, date
from loguru import logger
from utils.db.db_manager import DatabaseManager
from utils.db.tables.stock_labels.model import StockLabel


class LabelLoader:
    """
    标签数据加载器
    
    职责：
    - 股票标签的读写操作
    - 标签定义的查询
    - 批量标签计算和保存
    """
    
    def __init__(self, db: DatabaseManager):
        """
        初始化标签加载器
        
        Args:
            db: 数据库管理器实例
        """
        self.db = db
        self._stock_labels_table = None
        self._label_definitions_table = None
    
    @property
    def stock_labels_table(self):
        """懒加载股票标签表"""
        if self._stock_labels_table is None:
            self._stock_labels_table = self.db.get_table_instance('stock_labels')
        return self._stock_labels_table
    
    @property
    def label_definitions_table(self):
        """懒加载标签定义表"""
        if self._label_definitions_table is None:
            self._label_definitions_table = self.db.get_table_instance('label_definitions')
        return self._label_definitions_table
    
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
            target_date = datetime.now().strftime('%Y-%m-%d')
        
        try:
            # 查找最接近的历史标签
            sql = """
            SELECT labels FROM stock_labels 
            WHERE stock_id = %s AND label_date <= %s 
            ORDER BY label_date DESC 
            LIMIT 1
            """
            
            result = self.db.execute_query(sql, (stock_id, target_date))
            
            if result:
                label_record = result[0]
                labels_str = label_record['labels']
                if labels_str:
                    return [label.strip() for label in labels_str.split(',') if label.strip()]
            
            return []
            
        except Exception as e:
            logger.error(f"获取股票标签失败: {stock_id}, {target_date}, {e}")
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
            labels_str = ','.join(labels) if labels else ''
            
            sql = """
            INSERT INTO stock_labels (stock_id, label_date, labels)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE 
                labels = %s, 
                updated_at = CURRENT_TIMESTAMP
            """
            
            self.db.execute(sql, (stock_id, label_date, labels_str, labels_str))
            logger.debug(f"保存股票标签成功: {stock_id}, {label_date}, {labels}")
            
        except Exception as e:
            logger.error(f"保存股票标签失败: {stock_id}, {label_date}, {e}")
    
    def get_label_definition(self, label_id: str) -> Optional[Dict[str, Any]]:
        """
        获取标签定义
        
        Args:
            label_id: 标签ID
            
        Returns:
            Dict: 标签定义信息
        """
        try:
            sql = """
            SELECT label_id, label_name, label_category, label_description, is_active, created_at
            FROM label_definitions 
            WHERE label_id = %s AND is_active = TRUE
            """
            
            result = self.db.execute_query(sql, (label_id,))
            
            if result:
                return result[0]
            
            return None
            
        except Exception as e:
            logger.error(f"获取标签定义失败: {label_id}, {e}")
            return None
    
    def get_all_label_definitions(self) -> List[Dict[str, Any]]:
        """
        获取所有标签定义
        
        Returns:
            List[Dict]: 所有标签定义列表
        """
        try:
            sql = """
            SELECT label_id, label_name, label_category, label_description, is_active, created_at
            FROM label_definitions 
            WHERE is_active = TRUE
            ORDER BY label_category, label_id
            """
            
            result = self.db.execute_query(sql)
            return result if result else []
            
        except Exception as e:
            logger.error(f"获取所有标签定义失败: {e}")
            return []
    
    def get_label_definitions_by_category(self, category: str) -> List[Dict[str, Any]]:
        """
        根据分类获取标签定义
        
        Args:
            category: 标签分类
            
        Returns:
            List[Dict]: 标签定义列表
        """
        try:
            sql = """
            SELECT label_id, label_name, label_category, label_description, is_active, created_at
            FROM label_definitions 
            WHERE label_category = %s AND is_active = TRUE
            ORDER BY label_id
            """
            
            result = self.db.execute_query(sql, (category,))
            return result if result else []
            
        except Exception as e:
            logger.error(f"根据分类获取标签定义失败: {category}, {e}")
            return []
    
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
            target_date = datetime.now().strftime('%Y-%m-%d')
        
        try:
            sql = """
            SELECT stock_id FROM stock_labels 
            WHERE label_date <= %s AND FIND_IN_SET(%s, labels) > 0
            ORDER BY label_date DESC
            """
            
            result = self.db.execute_query(sql, (target_date, label_id))
            
            if result:
                # 去重，保留最新的标签记录
                seen = set()
                stock_ids = []
                for row in result:
                    stock_id = row['stock_id']
                    if stock_id not in seen:
                        seen.add(stock_id)
                        stock_ids.append(stock_id)
                
                return stock_ids
            
            return []
            
        except Exception as e:
            logger.error(f"获取具有标签的股票失败: {label_id}, {target_date}, {e}")
            return []
    
    def get_label_statistics(self, target_date: Optional[str] = None) -> Dict[str, Any]:
        """
        获取标签统计信息
        
        Args:
            target_date: 目标日期 (YYYY-MM-DD)，None表示当前日期
            
        Returns:
            Dict: 标签统计信息
        """
        if target_date is None:
            target_date = datetime.now().strftime('%Y-%m-%d')
        
        try:
            # 获取标签分布统计
            sql = """
            SELECT 
                COUNT(DISTINCT stock_id) as total_stocks,
                COUNT(*) as total_records,
                MAX(label_date) as latest_date,
                MIN(label_date) as earliest_date
            FROM stock_labels 
            WHERE label_date <= %s
            """
            
            result = self.db.execute_query(sql, (target_date,))
            
            if result:
                stats = result[0]
                
                # 获取各标签的使用频率
                sql2 = """
                SELECT labels FROM stock_labels 
                WHERE label_date <= %s
                ORDER BY label_date DESC
                """
                
                label_records = self.db.execute_query(sql2, (target_date,))
                
                label_counts = {}
                if label_records:
                    for record in label_records:
                        labels = record['labels'].split(',') if record['labels'] else []
                        for label in labels:
                            label = label.strip()
                            if label:
                                label_counts[label] = label_counts.get(label, 0) + 1
                
                stats['label_counts'] = label_counts
                return stats
            
            return {}
            
        except Exception as e:
            logger.error(f"获取标签统计失败: {target_date}, {e}")
            return {}
