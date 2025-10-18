"""
股票标签表模型定义
"""
from typing import List, Optional, Dict, Any
from datetime import datetime, date
from utils.db.db_model import BaseTableModel


class StockLabelModel(BaseTableModel):
    """股票标签表模型类"""
    
    def __init__(self, table_name: str, connected_db):
        super().__init__(table_name, connected_db)
    
    # ============ 私有工具方法 ============
    
    def _parse_labels_string(self, labels_str: str) -> List[str]:
        """解析标签字符串为标签列表"""
        if not labels_str:
            return []
        return [label.strip() for label in labels_str.split(',') if label.strip()]
    
    def _join_labels_list(self, label_list: List[str]) -> str:
        """将标签列表转换为逗号分隔的字符串"""
        return ','.join(label_list)
    
    def _has_label_in_string(self, labels_str: str, label_id: str) -> bool:
        """检查标签字符串中是否包含指定标签"""
        if not labels_str:
            return False
        labels_list = self._parse_labels_string(labels_str)
        return label_id in labels_list
    
    def get_all_stocks_last_update_dates(self, stock_ids: List[str]) -> Dict[str, str]:
        """
        批量获取所有股票的最后更新时间
        
        Args:
            stock_ids: 股票代码列表
            
        Returns:
            Dict[str, str]: 股票代码 -> 最后更新日期的映射
        """
        try:
            if not stock_ids:
                return {}
            
            # 使用BaseTableModel的execute_sync_query方法
            placeholders = ','.join(['%s'] * len(stock_ids))
            
            sql = f"""
            SELECT stock_id, MAX(label_date) as last_update_date
            FROM {self.table_name}
            WHERE stock_id IN ({placeholders})
            GROUP BY stock_id
            """
            
            result = self.db.execute_sync_query(sql, stock_ids)
            
            # 构建映射字典
            stock_last_dates = {}
            for row in result:
                stock_id = row['stock_id']
                last_date = row['last_update_date']
                
                if last_date:
                    if isinstance(last_date, date):
                        stock_last_dates[stock_id] = last_date.strftime('%Y%m%d')
                    else:
                        stock_last_dates[stock_id] = str(last_date).replace('-', '')
            
            return stock_last_dates
            
        except Exception as e:
            from loguru import logger
            logger.error(f"批量获取股票最后更新时间失败: {e}")
            return {}
    
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
        try:
            # 使用私有工具方法将标签列表转换为字符串
            labels_str = self._join_labels_list(labels)
            
            # 使用BaseTableModel的insert_or_update方法
            data = {
                'stock_id': stock_id,
                'label_date': target_date,
                'labels': labels_str
            }
            
            # 使用BaseTableModel的replace方法实现upsert
            return self.replace_one(data, ['stock_id', 'label_date'])
            
        except Exception as e:
            from loguru import logger
            logger.error(f"插入股票标签记录失败 {stock_id} {target_date}: {e}")
            return False
    
    def get_stock_labels_by_date(self, stock_id: str, target_date: str) -> List[str]:
        """
        获取指定股票在指定日期的标签
        
        Args:
            stock_id: 股票代码
            target_date: 目标日期
            
        Returns:
            List[str]: 标签列表
        """
        try:
            # 使用BaseTableModel的load_one方法
            condition = "stock_id = %s AND label_date = %s"
            params = (stock_id, target_date)
            
            result = self.load_one(condition, params)
            
            if result and result.get('labels'):
                labels_str = result['labels']
                return self._parse_labels_string(labels_str)
            else:
                return []
                
        except Exception as e:
            from loguru import logger
            logger.error(f"获取股票标签失败 {stock_id} {target_date}: {e}")
            return []
    
    def get_labels_by_date_range(self, start_date: str, end_date: str, 
                                stock_ids: Optional[List[str]] = None) -> Dict[str, List[Dict]]:
        """
        按日期范围获取标签数据
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            stock_ids: 股票代码过滤，为None时获取所有股票
            
        Returns:
            Dict: 按日期分组的标签数据
        """
        try:
            # 构建查询条件
            if stock_ids:
                placeholders = ','.join(['%s'] * len(stock_ids))
                condition = f"label_date >= %s AND label_date <= %s AND stock_id IN ({placeholders})"
                params = [start_date, end_date] + stock_ids
            else:
                condition = "label_date >= %s AND label_date <= %s"
                params = [start_date, end_date]
            
            # 使用BaseTableModel的load方法
            result = self.load(condition, params, order_by="label_date, stock_id")
            
            # 按日期分组
            labels_by_date = {}
            for row in result:
                date = row['label_date']
                if date not in labels_by_date:
                    labels_by_date[date] = []
                
                labels_list = self._parse_labels_string(row['labels'])
                labels_by_date[date].append({
                    'stock_id': row['stock_id'],
                    'labels': labels_list
                })
            
            return labels_by_date
            
        except Exception as e:
            from loguru import logger
            logger.error(f"按日期范围获取标签失败: {e}")
            return {}
    
    def get_stocks_with_label(self, label_id: str, target_date: str) -> List[str]:
        """
        获取具有指定标签的股票列表
        
        Args:
            label_id: 标签ID
            target_date: 目标日期
            
        Returns:
            List[str]: 股票代码列表
        """
        try:
            condition = "label_date <= %s AND FIND_IN_SET(%s, labels) > 0"
            params = (target_date, label_id)
            order_by = "label_date DESC"
            
            result = self.load(condition, params, order_by)
            
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
            from loguru import logger
            logger.error(f"获取具有标签的股票失败: {label_id}, {target_date}, {e}")
            return []
    
    def get_label_statistics(self, target_date: str) -> Dict[str, Any]:
        """
        获取标签统计信息
        
        Args:
            target_date: 目标日期
            
        Returns:
            Dict: 标签统计信息
        """
        try:
            # 使用BaseTableModel的execute_sync_query方法进行复杂查询
            sql = """
            SELECT 
                COUNT(DISTINCT stock_id) as total_stocks,
                COUNT(*) as total_records,
                MAX(label_date) as latest_date,
                MIN(label_date) as earliest_date
            FROM stock_labels 
            WHERE label_date <= %s
            """
            
            result = self.db.execute_sync_query(sql, (target_date,))
            
            if result:
                stats = result[0]
                
                # 获取各标签的使用频率
                sql2 = """
                SELECT labels FROM stock_labels 
                WHERE label_date <= %s
                ORDER BY label_date DESC
                """
                
                label_records = self.db.execute_sync_query(sql2, (target_date,))
                
                label_counts = {}
                if label_records:
                    for record in label_records:
                        labels = self._parse_labels_string(record['labels']) if record['labels'] else []
                        for label in labels:
                            label_counts[label] = label_counts.get(label, 0) + 1
                
                stats['label_counts'] = label_counts
                return stats
            
            return {}
            
        except Exception as e:
            from loguru import logger
            logger.error(f"获取标签统计失败: {target_date}, {e}")
            return {}
    
    def get_stock_labels_by_date_range(self, stock_id: str, target_date: str) -> List[str]:
        """
        获取股票在指定日期或之前最近的标签
        
        Args:
            stock_id: 股票代码
            target_date: 目标日期
            
        Returns:
            List[str]: 标签列表
        """
        try:
            condition = "stock_id = %s AND label_date <= %s"
            params = (stock_id, target_date)
            order_by = "label_date DESC"
            limit = 1
            
            result = self.load(condition, params, order_by, limit)
            
            if result and result[0].get('labels'):
                labels_str = result[0]['labels']
                return self._parse_labels_string(labels_str)
            else:
                return []
                
        except Exception as e:
            from loguru import logger
            logger.error(f"获取股票标签失败 {stock_id} {target_date}: {e}")
            return []
