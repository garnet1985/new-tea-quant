from datetime import datetime, timedelta
import tushare as ts
from crawler.providers.tushare.settings import (
    auth_token, 
    default_start_date
)
from crawler.db.db_manager import DatabaseManager
import pandas as pd
from loguru import logger

class TushareQuery:
    def __init__(self):
        self.token = self.get_token()
        ts.set_token(self.token)

        self.pro = ts.pro_api()

        self.last_market_open_day = self.get_last_market_open_day()

    # auth related
    def get_token(self):
        """获取Tushare token"""
        try:
            # 从配置文件获取token
            with open(auth_token, 'r') as f:
                return f.read().strip()
        except FileNotFoundError:
            raise FileNotFoundError(f"Token file not found: {auth_token}. Please create the token file with your Tushare token.")


    def get_last_market_open_day(self):
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=10)).strftime('%Y%m%d')
        dates = self.pro.trade_cal(exchange='', start_date=start_date, end_date=end_date)
        # get last cal_date which is_open == 1 and date < today
        last_market_open_day = dates[dates['is_open'] == 1]['cal_date'].max()
        return last_market_open_day

    def get_stock_index(self, is_inactivated_include=False):
        # exchange: 交易所，list_status: 上市状态，fields: 字段
        fields = 'ts_code,symbol,name,area,industry,market,exchange,list_date'
        # 上市状态 L上市 D退市 P暂停上市，默认是L
        stock_status = 'L' if is_inactivated_include else 'L'
        # 设置token
        data = self.pro.stock_basic(exchange='', list_status=stock_status, fields=fields)
        return data

    # renew functions
    def renew_stock_index(self):
        """更新股票基础信息"""
        try:
            logger.info("🔄 开始更新股票基础信息...")
            
            # step 1: 检查数据库连接和表是否存在
            db = DatabaseManager()
            db.connect_sync()
            
            # 检查表是否存在，如果不存在则创建
            with db.get_sync_cursor() as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS stock_index (
                        code INT(10) PRIMARY KEY,
                        name TEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci,
                        market TEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci,
                        industry TEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci,
                        isAlive TINYINT(1),
                        type TEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci,
                        lastUpdate DATE NULL
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
                """)
                logger.info("✅ 表stock_index检查/创建完成")
            
            # step 2: 检查数据是否最新（股票基础信息通常不需要按日期检查，直接更新即可）
            logger.info("📊 检查现有数据...")
            with db.get_sync_cursor() as cursor:
                cursor.execute("SELECT COUNT(*) as count FROM stock_index")
                existing_count = cursor.fetchone()['count']
                logger.info(f"📈 现有数据: {existing_count} 条记录")
            
            # step 3: 获取最新股票数据并更新数据库
            logger.info("🔄 获取最新股票数据...")
            new_data = self.get_stock_index()
            logger.success(f"✅ 获取到 {len(new_data)} 条股票数据")
            
            # 保存到数据库
            if self.save_stock_index_to_db(new_data):
                logger.success("🎉 股票基础信息更新完成！")
                db.disconnect_sync()
                return True
            else:
                logger.error("❌ 股票基础信息更新失败！")
                db.disconnect_sync()
                return False
                
        except Exception as e:
            logger.error(f"❌ 更新股票基础信息时发生错误: {e}")
            import traceback
            traceback.print_exc()
            return False


    def save_stock_index_to_db(self, data):
        """保存股票基础信息到数据库"""
        try:
            # 数据转换
            transformed_data = []
            for _, row in data.iterrows():
                # 提取market（ts_code中.之后的字母部分）
                market = row['ts_code'].split('.')[-1] if '.' in row['ts_code'] else ''
                
                transformed_row = {
                    'code': int(row['symbol']),  # symbol转为int
                    'name': row['name'],
                    'market': market,  # ts_code中.之后的字母部分
                    'industry': row['industry'] if pd.notna(row['industry']) else '',
                    'isAlive': 1,  # 默认活跃
                    'type': row['exchange'],
                    'lastUpdate': None  # 留空不更新
                }
                transformed_data.append(transformed_row)
            
            # 创建DataFrame
            df = pd.DataFrame(transformed_data)
            
            # 连接数据库
            db = DatabaseManager()
            db.connect_sync()
            
            # 创建表（如果不存在）
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS stock_index (
                code INT(10) PRIMARY KEY,
                name TEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci,
                market TEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci,
                industry TEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci,
                isAlive TINYINT(1),
                type TEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci,
                lastUpdate DATE NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
            """
            
            with db.get_sync_cursor() as cursor:
                cursor.execute(create_table_sql)
                logger.info("✅ 表stock_index创建成功或已存在")
            
            # 清空表数据（可选，根据需要决定是否保留）
            with db.get_sync_cursor() as cursor:
                cursor.execute("DELETE FROM stock_index")
                logger.info("✅ 表stock_index数据已清空")
            
            # 插入数据
            insert_sql = """
            INSERT INTO stock_index (code, name, market, industry, isAlive, type, lastUpdate)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            
            # 准备数据
            insert_data = []
            for _, row in df.iterrows():
                insert_data.append((
                    row['code'],
                    row['name'],
                    row['market'],
                    row['industry'],
                    row['isAlive'],
                    row['type'],
                    row['lastUpdate']
                ))
            
            # 批量插入
            with db.get_sync_cursor() as cursor:
                cursor.executemany(insert_sql, insert_data)
                logger.success(f"✅ 成功插入 {len(insert_data)} 条股票数据到stock_index表")
            
            # 验证插入结果
            with db.get_sync_cursor() as cursor:
                cursor.execute("SELECT COUNT(*) as count FROM stock_index")
                count = cursor.fetchone()['count']
                logger.info(f"📊 表stock_index当前共有 {count} 条记录")
            
            db.disconnect_sync()
            return True
            
        except Exception as e:
            logger.error(f"❌ 保存股票数据到数据库失败: {e}")
            return False

    # def get_stock_daily(self, ts_code='', trade_date='', start_date=start_date, end_date=end_date):
    #     """获取股票日线数据"""
    #     pro = ts.pro_api()
        
    #     df = pro.daily(ts_code=ts_code, trade_date=trade_date, 
    #                   start_date=start_date, end_date=end_date,
    #                   fields=STOCK_DAILY_FIELDS)
    #     return df

    # def get_index_daily(self, ts_code, start_date=start_date, end_date=end_date):
    #     """获取指数日线数据"""
    #     pro = ts.pro_api()
        
    #     df = pro.index_daily(ts_code=ts_code, start_date=start_date, 
    #                        end_date=end_date, fields=INDEX_DAILY_FIELDS)
    #     return df

    # def get_stock_weekly(self):

    # def get_data(self, code, start_date, end_date):
    #     pass


    # # Stock APIs

    # def get_data(self, code, start_date, end_date):
    #     pass

    # def request_stock_index(self):
    #     pass

    # def request_stock(self):
    #     pass

    # def request_stock_daily(self):
    #     pass

    # def request_stock_weekly(self):
    #     pass

    # def request_stock_monthly(self):
    #     pass

    # def request_stocks(self):
    #     pass

    # def request_stocks_daily(self):
    #     pass

    # def request_stocks_weekly(self):
    #     pass

    # def request_stocks_monthly(self):
    #     pass

    # Financial APIs