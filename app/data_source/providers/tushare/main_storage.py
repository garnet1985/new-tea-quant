
"""
Tushare数据存储类
"""
from loguru import logger

class TushareStorage:
    def __init__(self, connected_db):
        self.db = connected_db
        # 使用线程安全的数据库模型
        self.meta_info = connected_db.get_table_instance('meta_info')
        self.stock_index_table = connected_db.get_table_instance('stock_index')
        self.stock_kline_table = connected_db.get_table_instance('stock_kline')
        self.stock_index_indicator_table = connected_db.get_table_instance('stock_index_indicator')
        self.stock_index_indicator_weight_table = connected_db.get_table_instance('stock_index_indicator_weight')

    def save_stock_index(self, data):
        """
        保存股票指数数据到数据库 - 使用upsert方式
        
        Args:
            data: 股票指数数据列表
        """
        # 转换数据格式以匹配数据库表结构
        api_stocks = []
        from datetime import datetime
        current_date = datetime.now().strftime('%Y-%m-%d')
        
        for item in data:
            # 使用 ts_code 作为 id
            ts_code = item.get('ts_code', '')
            
            # 验证必填字段
            if not ts_code or not item.get('name'):
                continue
            
            api_stocks.append({
                'id': ts_code,  # 股票代码（包含市场后缀）
                'name': item.get('name', ''),
                'industry': item.get('industry', ''),
                'type': item.get('market', ''),  # market -> type
                'exchangeCenter': item.get('exchange', ''),  # exchange -> exchangeCenter
                'isAlive': 1,  # API返回的股票都是活跃的
                'lastUpdate': current_date
            })

        # 一次性更新：插入/更新活跃股票，标记未出现的股票为非活跃
        self.stock_index_table.renew_index(api_stocks)
        
        return True

    def load_stock_index(self):
        return self.stock_index_table.load_all()

    def get_most_recent_stock_kline_record_dates(self) -> dict:
        try:
            # 使用SQL聚合查询获取所有股票所有周期的最新日期
            query = """
                SELECT id, term, MAX(date) as latest_date 
                FROM stock_kline 
                GROUP BY id, term
            """
            result = self.stock_kline_table.execute_raw_query(query)
            
            # 转换为字典格式
            latest_data = {}
            for row in result:
                stock_id = row['id']
                term = row['term']
                latest_date = row['latest_date']
                
                if stock_id not in latest_data:
                    latest_data[stock_id] = {}
                latest_data[stock_id][term] = latest_date
        
            return latest_data
            
        except Exception as e:
            logger.error(f"获取最新数据状态失败: {e}")
            return {}

    def get_most_recent_stock_index_indicator_record_dates(self) -> dict:
        """
        获取股票指数指标数据的最新记录日期
        返回格式: {index_id: {term: latest_date}}
        """
        try:
            # 使用SQL聚合查询获取所有指数所有周期的最新日期
            query = """
                SELECT id, term, MAX(date) as latest_date 
                FROM stock_index_indicator 
                GROUP BY id, term
            """
            result = self.stock_index_indicator_table.execute_raw_query(query)
            
            # 转换为字典格式
            latest_data = {}
            for row in result:
                index_id = row['id']
                term = row['term']
                latest_date = row['latest_date']
                
                if index_id not in latest_data:
                    latest_data[index_id] = {}
                latest_data[index_id][term] = latest_date
        
            return latest_data
            
        except Exception as e:
            logger.error(f"获取股票指数指标最新数据状态失败: {e}")
            return {}

    def get_most_recent_stock_index_indicator_weight_record_dates(self) -> dict:
        """
        获取股票指数指标权重数据的最新记录日期
        返回格式: {index_id: latest_date}
        """
        try:
            # 使用SQL聚合查询获取所有指数的最新日期
            query = """
                SELECT id, MAX(date) as latest_date 
                FROM stock_index_indicator_weight 
                GROUP BY id
            """
            result = self.stock_index_indicator_weight_table.execute_raw_query(query)
            
            # 转换为字典格式
            latest_data = {}
            for row in result:
                index_id = row['id']
                latest_date = row['latest_date']
                latest_data[index_id] = latest_date
        
            return latest_data
            
        except Exception as e:
            logger.error(f"获取股票指数指标权重最新数据状态失败: {e}")
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
            stock_id = job.get('ts_code', '')  # 使用 ts_code 作为 id
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
                    'id': stock_id,  # 从job中获取 ts_code
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
                logger.info(f"保存 {len(converted_data)} 条 {term} K线数据 (股票: {stock_id})")
                self.stock_kline_table.insert(converted_data)
                logger.info(f"✅ {term} K线数据保存成功")
            else:
                logger.warning("没有有效的K线数据需要保存")
                
        except Exception as e:
            logger.error(f"保存K线数据失败: {e}")
            raise
    
    def convert_kline_data_for_storage(self, data, job):
        """
        将K线数据转换为存储格式
        
        Args:
            data: pandas.DataFrame K线数据
            job: 任务信息，包含 ts_code, term 等
            
        Returns:
            list: 转换后的数据列表
        """
        import math
        
        if data is None or data.empty:
            return []
        
        # 从job中获取基本信息
        stock_id = job['ts_code']  # 使用 ts_code 作为 id
        term = job['term']
        
        # 转换DataFrame为字典列表
        data_list = data.to_dict('records')
        
        # 转换数据格式以匹配数据库表结构
        converted_data = []
        
        for item in data_list:
            # 处理NaN值和范围限制的辅助函数
            def clean_value(value, default=0, max_value=None, min_value=None):
                """清理数值，将NaN转换为默认值，并限制范围"""
                if value is None or (isinstance(value, float) and math.isnan(value)):
                    return default
                
                # 限制范围
                if max_value is not None and value > max_value:
                    value = max_value
                if min_value is not None and value < min_value:
                    value = min_value
                
                return value
            
            # 根据schema.json的字段定义转换数据
            converted_item = {
                'id': stock_id,  # 从job中获取 ts_code
                'term': term,  # 从job中获取
                'date': item.get('trade_date', ''),  # 交易日期
                'open': clean_value(item.get('open', 0)),  # 开盘价
                'close': clean_value(item.get('close', 0)),  # 收盘价
                'highest': clean_value(item.get('high', 0)),  # 最高价
                'lowest': clean_value(item.get('low', 0)),  # 最低价
                'priceChangeDelta': clean_value(item.get('change', 0)),  # 价格变动
                'priceChangeRateDelta': clean_value(item.get('pct_chg', 0), 0, 9999.9999, -9999.9999),  # 价格变动率，限制在decimal(8,4)范围内
                'preClose': clean_value(item.get('pre_close', 0)),  # 前日收盘价
                'volume': clean_value(item.get('vol', 0)),  # 成交量
                'amount': clean_value(item.get('amount', 0))  # 成交额
            }
            
            # 验证必填字段（排除NaN值的情况）
            required_fields = ['id', 'term', 'date', 'open', 'close', 'highest', 'lowest']
            missing_fields = []
            for field in required_fields:
                value = converted_item.get(field)
                if value is None or value == '' or (isinstance(value, float) and math.isnan(value)):
                    missing_fields.append(field)
            
            if missing_fields:
                logger.warning(f"跳过缺少必填字段的数据: {missing_fields}, 数据: {item}")
                continue
            
            converted_data.append(converted_item)
        
        return converted_data

    def batch_save_stock_kline(self, data_list):
        """
        批量保存股票K线数据到数据库
        
        Args:
            data_list: 数据列表，每个元素都是字典格式
        """
        import math
        
        if not data_list:
            logger.warning("没有数据需要保存")
            return
        
        try:
            # 验证数据格式并清理NaN值
            valid_data = []
            for item in data_list:
                # 清理NaN值
                cleaned_item = {}
                for key, value in item.items():
                    if isinstance(value, float) and math.isnan(value):
                        cleaned_item[key] = 0
                    else:
                        cleaned_item[key] = value
                
                # 验证必填字段
                required_fields = ['id', 'term', 'date', 'open', 'close', 'highest', 'lowest']
                missing_fields = [field for field in required_fields if not cleaned_item.get(field)]
                
                if missing_fields:
                    logger.warning(f"跳过缺少必填字段的数据: {missing_fields}")
                    continue
                
                valid_data.append(cleaned_item)
            
            if valid_data:
                # 统计不同term的数据量
                term_counts = {}
                stock_counts = {}
                for item in valid_data:
                    term = item['term']
                    stock_key = item['id']
                    term_counts[term] = term_counts.get(term, 0) + 1
                    stock_counts[stock_key] = stock_counts.get(stock_key, 0) + 1
                
                # 批量插入或更新数据（使用ON DUPLICATE KEY UPDATE）
                # 主键字段: ['id', 'term', 'date']
                primary_keys = ['id', 'term', 'date']
                self.stock_kline_table.replace(valid_data, primary_keys)
            else:
                logger.warning("没有有效数据需要保存")
                
        except Exception as e:
            logger.error(f"批量保存K线数据失败: {e}")
            raise

    def get_meta_info(self, key):
        return self.meta_info.get_meta_info(key)

    def set_meta_info(self, key, value):
        self.meta_info.set_meta_info(key, value)

    def is_index_empty(self):
        return self.stock_index_table.count() == 0

    def convert_corporate_finance_data_for_storage(self, data):
        """
        转换企业财务数据为存储格式
        
        Args:
            data: Tushare API返回的企业财务数据DataFrame
            
        Returns:
            list: 转换后的数据列表
        """
        converted_data = []
        
        for _, row in data.iterrows():
            # 提取季度信息
            end_date = row.get('end_date', '')
            quarter = self._extract_quarter_from_date(end_date)
            
            if not quarter:
                continue
            
            # 构建存储记录
            record = {
                'id': row.get('ts_code', ''),
                'quarter': quarter,
                'eps': self._safe_float(row.get('eps')),
                'dt_eps': self._safe_float(row.get('dt_eps')),
                'roe_dt': self._safe_float(row.get('roe_dt')),
                'roe': self._safe_float(row.get('roe')),
                'roa': self._safe_float(row.get('roa')),
                'netprofit_margin': self._safe_float(row.get('netprofit_margin')),
                'gross_profit_margin': self._safe_float(row.get('grossprofit_margin')),
                'op_income': self._safe_float(row.get('op_income')),
                'roic': self._safe_float(row.get('roic')),
                'ebit': self._safe_float(row.get('ebit')),
                'ebitda': self._safe_float(row.get('ebitda')),
                'dtprofit_to_profit': self._safe_float(row.get('profit_dedt')),
                'profit_dedt': self._safe_float(row.get('profit_dedt')),
                'or_yoy': self._safe_float(row.get('or_yoy')),
                'netprofit_yoy': self._safe_float(row.get('netprofit_yoy')),
                'basic_eps_yoy': self._safe_float(row.get('basic_eps_yoy')),
                'dt_eps_yoy': self._safe_float(row.get('dt_eps_yoy')),
                'tr_yoy': self._safe_float(row.get('tr_yoy')),
                'netdebt': self._safe_float(row.get('netdebt')),
                'debt_to_eqt': self._safe_float(row.get('debt_to_eqt')),
                'debt_to_assets': self._safe_float(row.get('debt_to_assets')),
                'interestdebt': self._safe_float(row.get('interestdebt')),
                'assets_to_eqt': self._safe_float(row.get('assets_to_eqt')),
                'quick_ratio': self._safe_float(row.get('quick_ratio')),
                'current_ratio': self._safe_float(row.get('current_ratio')),
                'ar_turn': self._safe_float(row.get('ar_turn')),
                'bps': self._safe_float(row.get('bps')),
                'ocfps': self._safe_float(row.get('ocfps')),
                'fcff': self._safe_float(row.get('fcff')),
                'fcfe': self._safe_float(row.get('fcfe'))
            }
            
            converted_data.append(record)
        
        return converted_data

    def batch_save_corporate_finance(self, data_list):
        """
        批量保存企业财务数据到数据库
        
        Args:
            data_list: 数据列表，每个元素都是字典格式
        """
        import math
        
        if not data_list:
            logger.warning("没有企业财务数据需要保存")
            return
        
        try:
            # 验证数据格式并清理NaN值
            valid_data = []
            for item in data_list:
                # 清理NaN值
                cleaned_item = {}
                for key, value in item.items():
                    if isinstance(value, float) and math.isnan(value):
                        cleaned_item[key] = 0
                    else:
                        cleaned_item[key] = value
                
                # 验证必填字段
                required_fields = ['id', 'quarter']
                missing_fields = [field for field in required_fields if not cleaned_item.get(field)]
                
                if missing_fields:
                    logger.warning(f"跳过缺少必填字段的企业财务数据: {missing_fields}")
                    continue
                
                valid_data.append(cleaned_item)
            
            if valid_data:
                # 批量插入或更新数据（使用ON DUPLICATE KEY UPDATE）
                # 主键字段: ['id', 'quarter']
                primary_keys = ['id', 'quarter']
                table = self.db.get_table_instance('corporate_finance')
                table.replace(valid_data, primary_keys)
            else:
                logger.warning("没有有效的企业财务数据需要保存")
                
        except Exception as e:
            logger.error(f"批量保存企业财务数据失败: {e}")
            raise

    def _extract_quarter_from_date(self, date_str: str) -> str:
        """
        从日期字符串提取季度信息
        
        Args:
            date_str: 日期字符串，格式 YYYYMMDD
            
        Returns:
            str: 季度字符串，格式 YYYYQ{N}
        """
        if not date_str or len(date_str) != 8:
            return ''
        
        try:
            year = date_str[:4]
            month = int(date_str[4:6])
            quarter = (month - 1) // 3 + 1
            return f"{year}Q{quarter}"
        except (ValueError, IndexError):
            return ''

    def _safe_float(self, value):
        """
        安全转换为浮点数
        
        Args:
            value: 输入值
            
        Returns:
            float: 转换后的浮点数，无效值返回0
        """
        try:
            if value is None or value == '':
                return 0.0
            return float(value)
        except (ValueError, TypeError):
            return 0.0

    def convert_stock_index_indicator_data_for_storage(self, data, term='daily'):
        """
        转换股票指数指标数据格式以匹配数据库schema
        
        Args:
            data: Tushare API返回的DataFrame或列表
            term: 数据周期，如 'daily', 'weekly', 'monthly'
            
        Returns:
            list: 转换后的数据列表
        """
        converted_data = []
        
        # 确保data是列表格式
        if hasattr(data, 'to_dict'):
            data = data.to_dict('records')
        elif not isinstance(data, list):
            data = [data]
        
        for item in data:
            try:
                # 根据schema.json的字段定义转换数据
                converted_item = {
                    'id': item.get('ts_code', ''),  # 股指代码
                    'term': term,  # 数据周期
                    'date': item.get('trade_date', ''),  # 交易日期
                    'open': self._safe_float(item.get('open', 0)),  # 开盘价
                    'close': self._safe_float(item.get('close', 0)),  # 收盘价
                    'highest': self._safe_float(item.get('high', 0)),  # 最高价
                    'lowest': self._safe_float(item.get('low', 0)),  # 最低价
                    'priceChangeDelta': self._safe_float(item.get('change', 0)),  # 价格变动
                    'priceChangeRateDelta': self._safe_float(item.get('pct_chg', 0)),  # 价格变动率
                    'preClose': self._safe_float(item.get('pre_close', 0)),  # 前日收盘价
                    'volume': self._safe_float(item.get('vol', 0)),  # 成交量
                    'amount': self._safe_float(item.get('amount', 0))  # 成交额
                }
                
                # 验证必填字段
                required_fields = ['id', 'term', 'date', 'open', 'close', 'highest', 'lowest']
                if all(converted_item.get(field) is not None and converted_item.get(field) != '' 
                       for field in required_fields):
                    converted_data.append(converted_item)
                else:
                    logger.warning(f"跳过缺少必填字段的股票指数指标数据: {item}")
                    
            except Exception as e:
                logger.warning(f"转换股票指数指标数据时出错: {e}, 数据: {item}")
                continue
        
        return converted_data

    def batch_save_stock_index_indicator(self, data_list, term='daily'):
        """
        批量保存股票指数指标数据
        
        Args:
            data_list: 数据列表
            term: 数据周期
        """
        try:
            converted_data = self.convert_stock_index_indicator_data_for_storage(data_list, term)
            
            if converted_data:
                # 使用replace方法进行upsert操作
                primary_keys = ['id', 'term', 'date']
                self.stock_index_indicator_table.replace(converted_data, primary_keys)
                logger.info(f"✅ 成功保存 {len(converted_data)} 条股票指数指标数据 (周期: {term})")
            else:
                logger.warning(f"没有有效的股票指数指标数据需要保存 (周期: {term})")
                
        except Exception as e:
            logger.error(f"批量保存股票指数指标数据失败: {e}")
            raise

    def convert_stock_index_indicator_weight_data_for_storage(self, data):
        """
        转换股票指数指标权重数据格式以匹配数据库schema
        
        Args:
            data: Tushare API返回的DataFrame或列表
            
        Returns:
            list: 转换后的数据列表
        """
        converted_data = []
        
        # 确保data是列表格式
        if hasattr(data, 'to_dict'):
            data = data.to_dict('records')
        elif not isinstance(data, list):
            data = [data]
        
        logger.info(f"🔍 开始转换权重数据，原始数据条数: {len(data)}")
        
        # 记录前几条数据的字段名，用于调试
        if data and len(data) > 0:
            sample_item = data[0]
            logger.info(f"🔍 权重数据字段名示例: {list(sample_item.keys())}")
            logger.info(f"🔍 第一条权重数据示例: {sample_item}")
        
        skipped_count = 0
        for item in data:
            try:
                # 根据schema.json的字段定义转换数据
                # 注意：Tushare API的字段名可能与预期不同，需要调试确定
                converted_item = {
                    'id': item.get('index_code', ''),  # 股指代码
                    'date': item.get('trade_date', ''),  # 交易日期
                    'stock_id': item.get('con_code', ''),  # 成分股代码
                    'weight': self._safe_float(item.get('weight', 0))  # 权重
                }
                
                # 验证必填字段
                required_fields = ['id', 'date', 'stock_id']
                missing_fields = []
                for field in required_fields:
                    value = converted_item.get(field)
                    if value is None or value == '':
                        missing_fields.append(field)
                
                if missing_fields:
                    skipped_count += 1
                    if skipped_count <= 5:  # 只记录前5条被跳过的数据
                        logger.warning(f"跳过缺少必填字段的权重数据，缺少字段: {missing_fields}, 数据: {item}")
                else:
                    # 检查权重值是否有效（不为0）
                    weight_value = converted_item.get('weight', 0)
                    if weight_value > 0:
                        converted_data.append(converted_item)
                    else:
                        skipped_count += 1
                        if skipped_count <= 5:
                            logger.warning(f"跳过权重为0的数据: {item}")
                    
            except Exception as e:
                skipped_count += 1
                if skipped_count <= 5:
                    logger.warning(f"转换权重数据时出错: {e}, 数据: {item}")
                continue
        
        logger.info(f"🔍 权重数据转换完成: 原始 {len(data)} 条，转换后 {len(converted_data)} 条，跳过 {skipped_count} 条")
        
        return converted_data

    def batch_save_stock_index_indicator_weight(self, data_list):
        """
        批量保存股票指数指标权重数据
        
        Args:
            data_list: 数据列表
        """
        try:
            converted_data = self.convert_stock_index_indicator_weight_data_for_storage(data_list)
            
            if converted_data:
                # 使用replace方法进行upsert操作
                primary_keys = ['id', 'date', 'stock_id']
                self.stock_index_indicator_weight_table.replace(converted_data, primary_keys)
                logger.info(f"✅ 成功保存 {len(converted_data)} 条股票指数指标权重数据")
            else:
                logger.warning("没有有效的股票指数指标权重数据需要保存")
                
        except Exception as e:
            logger.error(f"批量保存股票指数指标权重数据失败: {e}")
            raise