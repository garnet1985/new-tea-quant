
"""
Tushare数据存储类
"""
from loguru import logger


class TushareStorage:
    def __init__(self, connected_db):
        self.db = connected_db
        self.stock_index_table = self.db.get_table_instance('stock_index', 'base')
        self.stock_kline_table = self.db.get_table_instance('stock_kline', 'base')

    def save_stock_index(self, data):
        self.stock_index_table.clear()

        # 将 pandas DataFrame 转换为字典列表
        if hasattr(data, 'to_dict'):
            # 如果是 pandas DataFrame
            data_list = data.to_dict('records')
        elif isinstance(data, list):
            # 如果已经是列表
            data_list = data
        else:
            # 其他情况，尝试转换
            data_list = [data]
        
        # 转换数据格式以匹配数据库表结构
        converted_data = []
        from datetime import datetime
        
        for item in data_list:
            # 分离 ts_code，例如 "000001.SZ" -> code="000001", market="SZ"
            ts_code = item.get('ts_code', '')
            if '.' in ts_code:
                code, market = ts_code.split('.', 1)
            else:
                code = ts_code
                market = item.get('market', '')
            
            converted_item = {
                'code': code,  # 股票代码（不含市场后缀）
                'name': item.get('name', ''),
                'market': market,  # 市场（.后的部分）
                'industry': item.get('industry', ''),
                'type': item.get('market', ''),  # market -> type
                'exchangeCenter': item.get('exchange', ''),  # exchange -> exchangeCenter
                'isAlive': 1,  # 默认活跃
                'lastUpdate': datetime.now().strftime('%Y-%m-%d')  # 当前日期
            }
            converted_data.append(converted_item)
        
        self.stock_index_table.insert(converted_data)

    def get_stock_index(self):
        return self.stock_index_table.get_all()

    def get_all_latest_kline_data(self) -> dict:
        """
        一次性获取所有股票所有周期的最新数据日期
        返回格式: {code: {term: latest_date}}
        """
        try:
            # 使用SQL聚合查询获取所有股票所有周期的最新日期
            query = """
                SELECT code, market, term, MAX(date) as latest_date 
                FROM stock_kline 
                GROUP BY code, market, term
            """
            result = self.stock_kline_table.execute_raw_query(query)
            
            # 转换为字典格式
            latest_data = {}
            for row in result:
                code = row['code']
                market = row['market']
                ts_code = code + '.' + market
                term = row['term']
                latest_date = row['latest_date']
                
                if ts_code not in latest_data:
                    latest_data[ts_code] = {}
                latest_data[ts_code][term] = latest_date
            
            logger.info(f"获取到 {len(latest_data)} 只股票的最新数据状态")
            return latest_data
            
        except Exception as e:
            logger.error(f"获取最新数据状态失败: {e}")
            return {}