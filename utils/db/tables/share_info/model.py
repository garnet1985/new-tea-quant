"""
Share Info Model - 股本信息模型
增量存储策略：只存储股本发生变化的季度数据，大幅减少存储空间
"""
from utils.db.db_model import BaseTableModel
from datetime import datetime
from loguru import logger


class ShareInfoModel(BaseTableModel):
    """股本信息模型 - 增量存储优化"""
    
    def __init__(self, table_name: str, connected_db):
        super().__init__(table_name, connected_db)
        # 标记为基础表（不需要前缀）
        self.is_base_table = True
    
    def get_share_info_by_date(self, stock_id, target_date):
        """
        根据指定日期获取股票的股本信息
        自动找到该日期对应的最新股本数据
        
        Args:
            stock_id (str): 股票代码
            target_date (str): 目标日期，格式 YYYYMMDD
            
        Returns:
            dict: 股本数据，包含 total_share, float_share
        """
        # 将日期转换为季度
        target_quarter = self._date_to_quarter(target_date)
        
        query = """
        SELECT id, quarter, total_share, float_share, change_type
        FROM share_info 
        WHERE id = %s AND quarter <= %s
        ORDER BY quarter DESC 
        LIMIT 1
        """
        result = self.db.execute_sync_query(query, (stock_id, target_quarter))
        return result[0] if result else None
    
    def get_share_changes(self, stock_id, start_quarter=None, end_quarter=None):
        """
        获取股票股本变化记录
        
        Args:
            stock_id (str): 股票代码
            start_quarter (str): 开始季度，如 '2018Q1'
            end_quarter (str): 结束季度，如 '2024Q3'
            
        Returns:
            list: 股本变化记录列表
        """
        if start_quarter and end_quarter:
            query = """
            SELECT id, quarter, total_share, float_share, change_type
            FROM share_info 
            WHERE id = %s AND quarter >= %s AND quarter <= %s
            ORDER BY quarter
            """
            return self.db.execute_sync_query(query, (stock_id, start_quarter, end_quarter))
        else:
            query = """
            SELECT id, quarter, total_share, float_share, change_type
            FROM share_info 
            WHERE id = %s
            ORDER BY quarter
            """
            return self.db.execute_sync_query(query, (stock_id,))
    
    def calculate_market_cap_by_date(self, stock_id, price, target_date):
        """
        根据指定日期和价格计算市值
        
        Args:
            stock_id (str): 股票代码
            price (float): 股票价格
            target_date (str): 目标日期，格式 YYYYMMDD
            
        Returns:
            dict: 市值计算结果
        """
        share_info = self.get_share_info_by_date(stock_id, target_date)
        
        if not share_info:
            return None
        
        total_share = share_info['total_share']
        float_share = share_info.get('float_share', total_share)
        
        # 计算市值（单位：亿元）
        total_market_cap_yi = (total_share * price) / 1e8
        float_market_cap_yi = (float_share * price) / 1e8
        
        return {
            'stock_id': stock_id,
            'date': target_date,
            'price': price,
            'total_share': total_share,
            'float_share': float_share,
            'total_market_cap_yi': total_market_cap_yi,
            'float_market_cap_yi': float_market_cap_yi,
            'quarter': share_info['quarter'],
            'change_type': share_info.get('change_type')
        }
    
    def insert_share_change(self, stock_id, quarter, total_share, float_share=None, change_type=None):
        """
        插入股本变化记录（增量存储）
        
        Args:
            stock_id (str): 股票代码
            quarter (str): 季度
            total_share (int): 总股本
            float_share (int): 流通股本
            change_type (str): 变化类型
        """
        query = """
        INSERT INTO share_info (id, quarter, total_share, float_share, change_type)
        VALUES (%s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
        total_share = VALUES(total_share),
        float_share = VALUES(float_share),
        change_type = VALUES(change_type)
        """
        
        self.db.execute_sync_query(query, (stock_id, quarter, total_share, float_share, change_type))
    
    def batch_insert_share_changes(self, changes_list):
        """
        批量插入股本变化记录
        
        Args:
            changes_list (list): 变化记录列表
        """
        query = """
        INSERT INTO share_info (id, quarter, total_share, float_share, change_type)
        VALUES (%s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
        total_share = VALUES(total_share),
        float_share = VALUES(float_share),
        change_type = VALUES(change_type)
        """
        
        data_to_insert = []
        for change in changes_list:
            data_to_insert.append((
                change['id'],
                change['quarter'],
                change['total_share'],
                change.get('float_share'),
                change.get('change_type')
            ))
        
        return self.db.execute_sync_query(query, data_to_insert, batch=True)
    
    def detect_and_store_changes(self, stock_id, raw_quarterly_data):
        """
        检测股本变化并只存储变化的数据
        
        Args:
            stock_id (str): 股票代码
            raw_quarterly_data (list): 原始季度数据，格式：[{'quarter': '2024Q1', 'total_share': 1000000, ...}, ...]
        """
        # 获取已有的股本变化记录
        existing_changes = self.get_share_changes(stock_id)
        existing_quarters = {change['quarter'] for change in existing_changes}
        
        changes_to_store = []
        last_total_share = None
        last_float_share = None
        
        for data in sorted(raw_quarterly_data, key=lambda x: x['quarter']):
            quarter = data['quarter']
            total_share = data['total_share']
            float_share = data.get('float_share', total_share)
            
            # 检测是否发生变化
            if (last_total_share is None or 
                total_share != last_total_share or 
                float_share != last_float_share):
                
                changes_to_store.append({
                    'id': stock_id,
                    'quarter': quarter,
                    'total_share': total_share,
                    'float_share': float_share,
                    'change_type': self._detect_change_type(last_total_share, total_share)
                })
                
                last_total_share = total_share
                last_float_share = float_share
        
        # 批量插入变化记录
        if changes_to_store:
            self.batch_insert_share_changes(changes_to_store)
            print(f"{stock_id}: 检测到 {len(changes_to_store)} 次股本变化，已存储")
        else:
            print(f"{stock_id}: 无股本变化")
        
        return len(changes_to_store)
    
    def replace(self, data_list, primary_keys=None):
        """
        重写replace方法，实现增量存储逻辑
        只存储股本发生变化的季度数据
        
        Args:
            data_list: 数据列表
            primary_keys: 主键列表（未使用）
        """
        if not data_list:
            return True
        
        # 按股票分组处理
        stock_groups = {}
        for item in data_list:
            stock_id = item.get('id')
            if stock_id:
                if stock_id not in stock_groups:
                    stock_groups[stock_id] = []
                stock_groups[stock_id].append(item)
        
        # 对每只股票进行增量存储
        total_changes = 0
        for stock_id, stock_data in stock_groups.items():
            try:
                changes_count = self.detect_and_store_changes(stock_id, stock_data)
                total_changes += changes_count
                logger.debug(f"📊 {stock_id}: 检测到 {changes_count} 次股本变化")
            except Exception as e:
                logger.error(f"❌ 处理 {stock_id} 股本数据失败: {e}")
                continue
        
        logger.info(f"✅ share_info 增量存储完成，总共 {total_changes} 次变化")
        return True
    
    def get_latest_date(self):
        """
        获取最新数据日期（用于UniversalRenewer的日期检查）
        由于share_info使用quarter而不是date，这里返回一个默认值
        """
        try:
            # 获取最新的季度（按年份和季度排序）
            query = """
            SELECT quarter 
            FROM share_info 
            ORDER BY 
                CAST(SUBSTRING(quarter, 1, 4) AS UNSIGNED) DESC,
                CAST(SUBSTRING(quarter, 6, 1) AS UNSIGNED) DESC
            LIMIT 1
            """
            result = self.db.execute_sync_query(query)
            if result and result[0]['quarter']:
                # 将季度转换为日期格式（季度末日期）
                quarter = result[0]['quarter']
                year = quarter[:4]
                q = int(quarter[5])
                
                if q == 1:
                    return f"{year}0331"
                elif q == 2:
                    return f"{year}0630"
                elif q == 3:
                    return f"{year}0930"
                else:  # q == 4
                    return f"{year}1231"
            
            return "20080101"  # 默认开始日期
        except Exception as e:
            logger.warning(f"❌ 获取share_info最新日期失败: {e}")
            return "20080101"
    
    def get_latest_date_from_table(self, table_name: str, date_field: str = 'date') -> str:
        """
        重写get_latest_date_from_table方法，特殊处理quarter字段
        """
        if date_field == 'quarter':
            return self.get_latest_date()
        else:
            # 调用父类方法
            return super().get_latest_date_from_table(table_name, date_field)
    
    def get_latest_quarters_by_stock(self):
        """
        获取每只股票的最新股本信息季度
        
        Returns:
            dict: {stock_id: latest_quarter}
        """
        try:
            query = """
            SELECT id, MAX(quarter) as latest_quarter
            FROM share_info
            GROUP BY id
            """
            result = self.db.execute_sync_query(query)
            
            latest_quarters = {}
            for row in result:
                latest_quarters[row['id']] = row['latest_quarter']
            
            return latest_quarters
        except Exception as e:
            logger.warning(f"❌ 获取最新股本信息季度失败: {e}")
            return {}
    
    def _date_to_quarter(self, date_str):
        """
        将日期转换为季度
        
        Args:
            date_str (str): 日期，格式 YYYYMMDD
            
        Returns:
            str: 季度，格式 YYYYQ[1-4]
        """
        year = int(date_str[:4])
        month = int(date_str[4:6])
        
        if month <= 3:
            return f"{year}Q1"
        elif month <= 6:
            return f"{year}Q2"
        elif month <= 9:
            return f"{year}Q3"
        else:
            return f"{year}Q4"
    
    def _detect_change_type(self, old_shares, new_shares):
        """
        检测股本变化类型
        
        Args:
            old_shares (int): 旧股本
            new_shares (int): 新股本
            
        Returns:
            str: 变化类型
        """
        if old_shares is None:
            return "初始"
        
        if new_shares > old_shares:
            return "股本增加"
        elif new_shares < old_shares:
            return "股本减少"
        else:
            return "无变化"
    
    def get_compression_stats(self, stock_id):
        """
        获取数据压缩统计信息
        
        Args:
            stock_id (str): 股票代码
            
        Returns:
            dict: 压缩统计信息
        """
        changes = self.get_share_changes(stock_id)
        
        if not changes:
            return {"total_changes": 0, "compression_ratio": 0}
        
        # 计算理论上的总季度数（从第一个变化到最后一个变化）
        first_quarter = changes[0]['quarter']
        last_quarter = changes[-1]['quarter']
        
        # 简化的季度数计算
        first_year = int(first_quarter[:4])
        first_q = int(first_quarter[5])
        last_year = int(last_quarter[:4])
        last_q = int(last_quarter[5])
        
        total_quarters = (last_year - first_year) * 4 + (last_q - first_q) + 1
        stored_changes = len(changes)
        
        compression_ratio = (1 - stored_changes / total_quarters) * 100 if total_quarters > 0 else 0
        
        return {
            "stock_id": stock_id,
            "period": f"{first_quarter} ~ {last_quarter}",
            "total_quarters": total_quarters,
            "stored_changes": stored_changes,
            "compression_ratio": round(compression_ratio, 2)
        }