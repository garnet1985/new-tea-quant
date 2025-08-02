"""
Adjust Factor 模型
提供复权因子相关的特定方法
"""
from utils.db.db_model import BaseTableModel
from loguru import logger
from datetime import datetime, date
from typing import Optional, Dict, List, Tuple


class AdjustFactor(BaseTableModel):
    """复权因子表自定义模型"""
    
    def __init__(self, table_name: str, connected_db):
        super().__init__(table_name, connected_db)
        # 标记为基础表（不需要前缀）
        self.is_base_table = True
    
    def get_adj_factor(self, code: str, market: str, trade_date: str) -> Optional[Dict]:
        query = """
            SELECT qfq_factor, hfq_factor, last_update
            FROM adj_factor 
            WHERE code = %s AND market = %s AND date <= %s
            ORDER BY date DESC
            LIMIT 1
        """
        result = self.execute_raw_query(query, (code, market, trade_date))
        
        if result:
            return {
                'qfq_factor': float(result[0]['qfq_factor']),
                'hfq_factor': float(result[0]['hfq_factor']),
                'last_update': result[0]['last_update']
            }
        return None
    
    def get_adj_factors_by_date_range(self, code: str, market: str, start_date: str, end_date: str) -> List[Dict]:
        """
        获取指定股票在日期范围内的复权因子
        
        Args:
            code: 股票代码（不含市场后缀）
            market: 市场代码（SZ/SH）
            start_date: 开始日期（YYYYMMDD）
            end_date: 结束日期（YYYYMMDD）
            
        Returns:
            复权因子数据列表
        """
        try:
            query = """
                SELECT date, qfq_factor, hfq_factor, last_update
                FROM adj_factor 
                WHERE code = %s AND market = %s AND date BETWEEN %s AND %s
                ORDER BY date
            """
            result = self.execute_raw_query(query, (code, market, start_date, end_date))
            
            return [
                {
                    'date': row['date'],
                    'qfq_factor': float(row['qfq_factor']),
                    'hfq_factor': float(row['hfq_factor']),
                    'last_update': row['last_update']
                }
                for row in result
            ]
            
        except Exception as e:
            logger.error(f"获取复权因子范围失败: {e}")
            return []
    
    def calculate_qfq_price(self, raw_price: float, qfq_factor: float) -> float:
        """
        计算前复权价格
        
        Args:
            raw_price: 不复权价格
            qfq_factor: 前复权因子
            
        Returns:
            前复权价格
        """
        return raw_price * qfq_factor
    
    def calculate_hfq_price(self, raw_price: float, hfq_factor: float) -> float:
        """
        计算后复权价格
        
        Args:
            raw_price: 不复权价格
            hfq_factor: 后复权因子
            
        Returns:
            后复权价格
        """
        return raw_price * hfq_factor
    
    def upsert_adj_factor(self, code: str, market: str, trade_date: str, qfq_factor: float, hfq_factor: float) -> bool:
        """
        插入或更新复权因子
        
        Args:
            code: 股票代码（不含市场后缀）
            market: 市场代码（SZ/SH）
            trade_date: 交易日期（YYYYMMDD）
            qfq_factor: 前复权因子
            hfq_factor: 后复权因子
            
        Returns:
            操作是否成功
        """
        try:
            query = """
                INSERT INTO adj_factor (code, market, date, qfq_factor, hfq_factor, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
                ON DUPLICATE KEY UPDATE 
                    qfq_factor = VALUES(qfq_factor),
                    hfq_factor = VALUES(hfq_factor),
                    updated_at = NOW()
            """
            
            self.execute_raw_update(query, (code, market, trade_date, qfq_factor, hfq_factor))
            return True
            
        except Exception as e:
            logger.error(f"插入复权因子失败: {e}")
            return False
    
    def batch_upsert_adj_factors(self, factors_data: List[Tuple]) -> bool:
        """
        批量插入或更新复权因子
        
        Args:
            factors_data: 复权因子数据列表，每个元素为 (code, market, date, qfq_factor, hfq_factor)
            
        Returns:
            操作是否成功
        """
        try:
            if not factors_data:
                return True
            
            # 构建批量插入语句
            placeholders = ', '.join(['(%s, %s, %s, %s, %s, NOW())'] * len(factors_data))
            query = f"""
                INSERT INTO adj_factor (code, market, date, qfq_factor, hfq_factor, last_update)
                VALUES {placeholders}
                ON DUPLICATE KEY UPDATE 
                    qfq_factor = VALUES(qfq_factor),
                    hfq_factor = VALUES(hfq_factor),
                    last_update = NOW()
            """
            
            # 展平数据
            flat_data = []
            for factor_data in factors_data:
                flat_data.extend(factor_data)
            
            self.execute_raw_update(query, flat_data)
            return True
            
        except Exception as e:
            logger.error(f"批量插入复权因子失败: {e}")
            return False
    
    def get_latest_adj_factor(self, code: str, market: str) -> Optional[Dict]:
        """
        获取指定股票的最新复权因子
        
        Args:
            code: 股票代码（不含市场后缀）
            market: 市场代码（SZ/SH）
            
        Returns:
            最新复权因子数据
        """
        try:
            query = """
                SELECT date, qfq_factor, hfq_factor, last_update
                FROM adj_factor 
                WHERE code = %s AND market = %s
                ORDER BY date DESC
                LIMIT 1
            """
            result = self.execute_raw_query(query, (code, market))
            
            if result:
                return {
                    'date': result[0]['date'],
                    'qfq_factor': float(result[0]['qfq_factor']),
                    'hfq_factor': float(result[0]['hfq_factor']),
                    'last_update': result[0]['last_update']
                }
            return None
            
        except Exception as e:
            logger.error(f"获取最新复权因子失败: {e}")
            return None
    
    def delete_adj_factor(self, code: str, market: str, trade_date: str) -> bool:
        query = "DELETE FROM adj_factor WHERE code = %s AND market = %s AND date = %s"
        self.execute_raw_update(query, (code, market, trade_date))
        return True
    
    def get_factor_changes_since(self, code: str, market: str, since_date: str) -> List[Dict]:
        query = """
            SELECT date, qfq_factor, hfq_factor
            FROM adj_factor 
            WHERE code = %s AND market = %s AND date >= %s
            ORDER BY date
        """
        result = self.execute_raw_query(query, (code, market, since_date))
        
        return [
            {
                'date': row['date'],
                'qfq_factor': float(row['qfq_factor']),
                'hfq_factor': float(row['hfq_factor'])
            }
            for row in result
        ]
    
    def has_factor_changes(self, code: str, market: str, since_date: str) -> bool:
        query = """
            SELECT COUNT(*) as count
            FROM adj_factor 
            WHERE code = %s AND market = %s AND date >= %s
        """
        result = self.execute_raw_query(query, (code, market, since_date))
        return result[0]['count'] > 0
    
   
