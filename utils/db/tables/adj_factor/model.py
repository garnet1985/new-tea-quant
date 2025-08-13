"""
Adjust Factor 模型
提供复权因子相关的特定方法
"""
import pandas as pd
from utils.db.db_model import BaseTableModel
from loguru import logger
from datetime import datetime, date
from typing import Optional, Dict, List, Tuple
import os

class AdjustFactor(BaseTableModel):
    """复权因子表自定义模型"""
    
    def __init__(self, table_name: str, connected_db):
        super().__init__(table_name, connected_db)
        # 标记为基础表（不需要前缀）
        self.is_base_table = True
        self.csv_file_name = "factors.csv"

    def get_adj_factor(self, ts_code: str, type: str = 'qfq', date: str = None) -> Optional[Dict]:
        """
        获取指定日期的复权因子
        
        Args:
            ts_code: 股票代码
            type: 复权类型 ('qfq' 或 'hfq')
            date: 查询日期，如果为None则返回最新的因子
        """
        factor_type = type
        
        if date:
            # 查询指定日期之前最近的复权因子
            query = f"""
                SELECT {factor_type}, date, last_update
                FROM adj_factor 
                WHERE id = %s AND date <= %s
                ORDER BY date DESC
                LIMIT 1
            """
            result = self.execute_raw_query(query, (ts_code, date))
        else:
            # 查询最新的复权因子
            query = f"""
                SELECT {factor_type}, date, last_update
                FROM adj_factor 
                WHERE id = %s
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
            WHERE id = %s
            ORDER BY date DESC
        """
        return self.execute_raw_query(query, (ts_code,))
    
    def get_all_stocks_latest_update_dates(self) -> List[Dict]:
        """
        获取所有股票的复权因子更新状态
        只负责数据查询，不包含业务逻辑
        
        Returns:
            所有股票的更新状态列表，包含：
            - ts_code: 股票代码
            - last_factor_date: 最近的因子变化日期
            - last_update: 系统最后更新时间
        """
        try:
            # 查询每只股票的因子状态
            query = """
                SELECT MAX(date) AS last_factor_date, id, last_update
                FROM adj_factor 
                GROUP BY id
            """
            
            result = self.execute_raw_query(query)
            return result if result else []
            
        except Exception as e:
            logger.error(f"获取股票更新状态失败: {e}")
            return []

    def _is_table_empty(self) -> bool:
        return self.count() == 0
    
    def import_from_csv(self) -> None:
        """从CSV文件导入复权因子数据"""
        try:
            # 检查当前表是否为空
            if not self._is_table_empty():
                logger.error(f"CSV导入失败：表不为空，请先清空表")
                return

            # 检查CSV文件是否存在
            file_path = os.path.join(os.path.dirname(__file__), self.csv_file_name)
            if not os.path.exists(file_path):
                logger.error(f"CSV导入失败：找不到文件 {file_path}")
                return

            # 读取CSV文件
            df = pd.read_csv(file_path, dtype={
                'id': str, 
                'date': str, 
                'qfq': float, 
                'hfq': float, 
                'last_update': str
            })
            
            # 验证数据完整性
            if df.empty:
                logger.error(f"CSV文件为空")
                return
                
            # 转换数据格式
            records = df.to_dict(orient='records')
            for record in records:
                # 确保last_update是有效的日期时间格式
                if pd.isna(record['last_update']):
                    record['last_update'] = datetime.now()
                elif isinstance(record['last_update'], str):
                    try:
                        # 尝试解析日期时间字符串
                        record['last_update'] = pd.to_datetime(record['last_update'])
                    except:
                        record['last_update'] = datetime.now()

            # 插入数据
            inserted_count = self.insert(records)
            logger.info(f"CSV导入成功：导入了 {inserted_count} 条记录")
            
        except Exception as e:
            logger.error(f"CSV导入失败：{e}")
            raise


    def export_to_csv(self) -> None:
        """导出复权因子数据到CSV文件"""
        if self._is_table_empty():
            logger.warning(f"表为空，没有数据可导出")
            return

        # 检查CSV文件是否存在，如果存在则删除
        file_path = os.path.join(os.path.dirname(__file__), self.csv_file_name)
        if os.path.exists(file_path):
            os.remove(file_path)
            
        # 转换为DataFrame并处理日期时间格式
        all_factors = self.load_all()
        df = pd.DataFrame(all_factors)
        
        # 处理last_update字段，确保CSV兼容
        if 'last_update' in df.columns:
            df['last_update'] = df['last_update'].astype(str)
        
        # 导出到CSV
        df.to_csv(file_path, index=False, encoding='utf-8')            

