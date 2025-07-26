from datetime import datetime, timedelta
import tushare as ts
from app.data_source.providers.tushare.settings import (
    auth_token
)
from app.data_source.providers.conf.conf import data_start_date
from app.data_source.providers.tushare.storage import TushareStorage

class Tushare:
    def __init__(self, connected_db):
        self.db = connected_db
        self.storage = TushareStorage(connected_db)

        self.meta_info = self.db.get_table_instance('meta_info', 'base')

        self.token = self.get_token()
        ts.set_token(self.token)

        self.pro = ts.pro_api()

        self.last_market_open_day = self.get_last_market_open_day()

    def renew_data(self):
        self.renew_stock_index()

    # auth related
    def get_token(self):
        try:
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

    # renew functions
    def renew_stock_index(self, is_force=True):

        if is_force:
            print('renew stock index')
            data = self.request_stock_index()
            self.storage.save_stock_index(data)
            self.meta_info.set_meta_info('stock_index_last_update', self.last_market_open_day)
            return



        meta_info = self.meta_info.get_meta_info('stock_index_last_update')
        if meta_info == None:
            print('renew stock index')
            data = self.request_stock_index()
            self.storage.save_stock_index(data)
            self.meta_info.set_meta_info('stock_index_last_update', self.last_market_open_day)
        else:
            if meta_info < self.last_market_open_day:
                print('renew stock index')
                data = self.request_stock_index()
                self.storage.save_stock_index(data)
                self.meta_info.set_meta_info('stock_index_last_update', self.last_market_open_day)
            else:
                print('stock index is up to date')

    def request_stock_index(self):
        fields = 'ts_code,symbol,name,area,industry,market,exchange,list_date'
        stock_status = 'L'
        data = self.pro.stock_basic(exchange='', list_status=stock_status, fields=fields)
        return data





        # meta_info.get_meta_info('stock_index_last_update')

        # if self.storage.should_renew_stock_index():
        #     # exchange: 交易所，list_status: 上市状态，fields: 字段
        #     fields = 'ts_code,symbol,name,area,industry,market,exchange,list_date'
        #     # 上市状态 L上市 D退市 P暂停上市，默认是L
        #     stock_status = 'L'

        #     # 获取数据
        #     data = self.pro.stock_basic(exchange='', list_status=stock_status, fields=fields)

        #     # 保存到数据库
        #     self.storage.save_stock_index(data)

        # return data

   
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