
class TushareStorage:
    def __init__(self, connected_db):
        self.db = connected_db
        self.stock_index_table = self.db.get_table_instance('stock_index', 'base')

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
        return self.stock_index_table.find_all()