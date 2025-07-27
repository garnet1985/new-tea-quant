
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

    def get_all_latest_kline_dates(self) -> dict:
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
        
            return latest_data
            
        except Exception as e:
            logger.error(f"获取最新数据状态失败: {e}")
            return {}

    def save_stock_kline(self, data, job):
        """
        保存股票K线数据到数据库
        
        Args:
            data: pandas DataFrame，包含K线数据
            job: 包含任务信息的字典，包括 code, market, term, start_date, end_date 等
        """
        if data is None or data.empty:
            logger.warning("没有K线数据需要保存")
            return
        
        try:
            # 从job中获取基本信息
            code = job.get('code', '')
            market = job.get('market', '')
            term = job.get('term', 'daily')
            
            # 将 pandas DataFrame 转换为字典列表
            if hasattr(data, 'to_dict'):
                data_list = data.to_dict('records')
            elif isinstance(data, list):
                data_list = data
            else:
                data_list = [data]
            
            # 转换数据格式以匹配数据库表结构
            converted_data = []
            
            for item in data_list:
                # 根据schema.json的字段定义转换数据
                converted_item = {
                    'code': code,  # 从job中获取
                    'market': market,  # 从job中获取
                    'term': term,  # 从job中获取
                    'date': item.get('trade_date', ''),  # 交易日期
                    'open': item.get('open', 0),  # 开盘价
                    'close': item.get('close', 0),  # 收盘价
                    'highest': item.get('high', 0),  # 最高价
                    'lowest': item.get('low', 0),  # 最低价
                    'priceChangeDelta': item.get('change', 0),  # 价格变动
                    'priceChangeRateDelta': item.get('pct_chg', 0),  # 价格变动率
                    'preClose': item.get('pre_close', 0),  # 前日收盘价
                    'volume': item.get('vol', 0),  # 成交量
                    'amount': item.get('amount', 0)  # 成交额
                }
                
                # 验证必填字段
                required_fields = ['code', 'market', 'term', 'date', 'open', 'close', 'highest', 'lowest']
                missing_fields = [field for field in required_fields if not converted_item.get(field)]
                
                if missing_fields:
                    logger.warning(f"跳过缺少必填字段的数据: {missing_fields}, 数据: {item}")
                    continue
                
                converted_data.append(converted_item)
            
            # 批量插入数据
            if converted_data:
                logger.info(f"保存 {len(converted_data)} 条 {term} K线数据 (股票: {code}.{market})")
                self.stock_kline_table.insert(converted_data)
                logger.info(f"✅ {term} K线数据保存成功")
            else:
                logger.warning("没有有效的K线数据需要保存")
                
        except Exception as e:
            logger.error(f"保存K线数据失败: {e}")
            raise