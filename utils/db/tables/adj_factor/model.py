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

    def get_qfq_factor(self, ts_code: str, date: str = None) -> Optional[Dict]:
        return self.get_adj_factor(ts_code, 'qfq', date)
    
    def get_hfq_factor(self, ts_code: str, date: str = None) -> Optional[Dict]:
        return self.get_adj_factor(ts_code, 'hfq', date)

    def get_latest_factor(self, ts_code: str) -> Optional[Dict]:
        query = """
            SELECT *
            FROM adj_factor
            WHERE ts_code = %s
            ORDER BY date DESC
            LIMIT 1
        """
        result = self.execute_raw_query(query, (ts_code,))
        if result:
            return result[0]
        return None

    def get_adj_factor(self, ts_code: str, type: str = 'qfq', date: str = None) -> Optional[Dict]:
        """
        获取指定日期的复权因子
        
        Args:
            ts_code: 股票代码
            type: 复权类型 ('qfq' 或 'hfq')
            date: 查询日期，如果为None则返回最新的因子
        """
        factor_type = type + '_factor'
        
        if date:
            # 查询指定日期之前最近的复权因子
            query = f"""
                SELECT {factor_type}, date, last_update
                FROM adj_factor 
                WHERE ts_code = %s AND date <= %s
                ORDER BY date DESC
                LIMIT 1
            """
            result = self.execute_raw_query(query, (ts_code, date))
        else:
            # 查询最新的复权因子
            query = f"""
                SELECT {factor_type}, date, last_update
                FROM adj_factor 
                WHERE ts_code = %s
                ORDER BY date DESC
                LIMIT 1
            """
            result = self.execute_raw_query(query, (ts_code,))
            
        if result:
            return {
                'type': type,
                'value': float(result[0][factor_type]),
                'date': result[0]['date'],
                'last_update': result[0]['last_update']
            }
        return None

    def get_all_adj_factors(self, ts_code: str) -> List[Dict]:
        query = """
            SELECT * 
            FROM adj_factor
            WHERE ts_code = %s
            ORDER BY date DESC
        """
        return self.execute_raw_query(query, (ts_code,))
    
    def get_adj_factors(self, ts_code: str, date: str = None) -> Optional[Dict]:
        """
        获取指定日期的所有复权因子
        
        Args:
            ts_code: 股票代码
            date: 查询日期，如果为None则返回最新的因子
        """
        if date:
            query = """
                SELECT qfq_factor, hfq_factor, date, last_update
                FROM adj_factor 
                WHERE ts_code = %s AND date <= %s
                ORDER BY date DESC
                LIMIT 1
            """
            result = self.execute_raw_query(query, (ts_code, date))
        else:
            query = """
                SELECT qfq_factor, hfq_factor, date, last_update
                FROM adj_factor 
                WHERE ts_code = %s
                ORDER BY date DESC
                LIMIT 1
            """
            result = self.execute_raw_query(query, (ts_code,))
        
        if result:
            return {
                'qfq_factor': float(result[0]['qfq_factor']),
                'hfq_factor': float(result[0]['hfq_factor']),
                'date': result[0]['date'],
                'last_update': result[0]['last_update']
            }
        return None
    
    def upsert_adj_factor(self, ts_code: str, date: str, qfq_factor: float, hfq_factor: float) -> bool:
        """
        插入或更新复权因子
        
        Args:
            ts_code: 股票代码
            date: 复权事件日期
            qfq_factor: 前复权因子
            hfq_factor: 后复权因子
        """
        try:
            query = """
                INSERT INTO adj_factor (ts_code, date, qfq_factor, hfq_factor, last_update)
                VALUES (%s, %s, %s, %s, NOW())
                ON DUPLICATE KEY UPDATE 
                    qfq_factor = VALUES(qfq_factor),
                    hfq_factor = VALUES(hfq_factor),
                    last_update = NOW()
            """
            
            self.execute_raw_update(query, (ts_code, date, qfq_factor, hfq_factor))
            return True
            
        except Exception as e:
            logger.error(f"插入复权因子失败: {e}")
            return False
  
    def delete_adj_factor(self, ts_code: str, date: str = None) -> bool:
        """
        删除复权因子
        
        Args:
            ts_code: 股票代码
            date: 复权事件日期，如果为None则删除该股票的所有复权因子
        """
        if date:
            query = "DELETE FROM adj_factor WHERE ts_code = %s AND date = %s"
            self.execute_raw_update(query, (ts_code, date))
        else:
            query = "DELETE FROM adj_factor WHERE ts_code = %s"
            self.execute_raw_update(query, (ts_code,))
        return True
    
    def batch_upsert_adj_factors(self, factors_data: List[Tuple]) -> bool:
        """
        批量插入或更新复权因子
        
        Args:
            factors_data: 复权因子数据列表，每个元素为 (ts_code, date, qfq_factor, hfq_factor)
        """
        try:
            if not factors_data:
                return True
            
            for ts_code, date, qfq_factor, hfq_factor in factors_data:
                self.upsert_adj_factor(ts_code, date, qfq_factor, hfq_factor)
            
            return True
            
        except Exception as e:
            logger.error(f"批量插入复权因子失败: {e}")
            return False
    

