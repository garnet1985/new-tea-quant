import os

import requests
import tushare as ts

from conf.settings import START_DATE, END_DATE


# 股票基本信息
def stock_basic(engine, table_name):
    df = pro.stock_basic(exchange='', list_status='L',
                         fields='ts_code,symbol,name,area,industry,market,exchange,list_date')
    df.to_sql(con=engine, name=table_name, if_exists='replace')
    return df


# 交易日历
def trade_calendar(engine, table_name, exchange='SSE', start_date=START_DATE, end_date=END_DATE):
    df = pro.trade_cal(exchange=exchange, start_date=start_date, end_date=end_date)
    df.to_sql(con=engine, name=table_name, if_exists='replace')
    return df


# 复权因子
def adj_factor(engine, table_name, ts_code='', trade_date='', start_date=START_DATE, end_date=END_DATE):
    df = pro.adj_factor(ts_code=ts_code, trade_date=trade_date, start_date=start_date, end_date=end_date)
    df.to_sql(con=engine, name=table_name, if_exists='append')
    return df


# 日线数据 - 不复权 - 批量
def stock_daily(engine, table_name, ts_code='', trade_date='', start_date=START_DATE, end_date=END_DATE):
    df = pro.daily(ts_code=ts_code, trade_date=trade_date, start_date=start_date, end_date=end_date)
    df.to_sql(con=engine, name=table_name, if_exists='append')
    return df


# 日线数据 - 不复权
def stock_daily_bfq(engine, table_name, ts_code, start_date=START_DATE, end_date=END_DATE):
    df = ts.pro_bar(ts_code=ts_code, start_date=start_date, end_date=end_date)  # 默认adj为不复权
    df.to_sql(con=engine, name=table_name, if_exists='append')
    return df


# 日线数据 - 前复权
def stock_daily_qfq(engine, table_name, ts_code, start_date=START_DATE, end_date=END_DATE):
    df = ts.pro_bar(ts_code=ts_code, start_date=start_date, end_date=end_date, adj='qfq')  # 默认adj为不复权
    df.to_sql(con=engine, name=table_name, if_exists='append')
    return df


# 日线数据 - 后复权
def stock_daily_hfq(engine, table_name, ts_code, start_date=START_DATE, end_date=END_DATE):
    df = ts.pro_bar(ts_code=ts_code, start_date=start_date, end_date=end_date, adj='hfq')
    df.to_sql(con=engine, name=table_name, if_exists='append')
    return df


# LPR利率
def interest_rate_lpr(engine, table_name, start_date=START_DATE, end_date=END_DATE):
    df = pro.shibor_lpr(start_date=start_date, end_date=end_date)
    df.to_sql(con=engine, name=table_name, if_exists='append')
    return df


# Shibor利率
def interest_rate_shibor(engine, table_name, start_date=START_DATE, end_date=END_DATE):
    df = pro.shibor(start_date=start_date, end_date=end_date)
    df.to_sql(con=engine, name=table_name, if_exists='append')
    return df


# 每日指标
def daily_basic_indicator(engine, table_name, trade_date):
    df = pro.daily_basic(trade_date=trade_date)
    df.to_sql(con=engine, name=table_name, if_exists='append')
    return df


# 分红送股
def dividend(engine, table_name, ts_code):
    df = pro.dividend(ts_code=ts_code)
    df.to_sql(con=engine, name=table_name, if_exists='append')
    return df


# 利润表
def income_vip(engine, table_name, period):
    df = pro.income_vip(period=period)
    df.to_sql(con=engine, name=table_name, if_exists='append')
    return df


# 资产负债表
def balancesheet_vip(engine, table_name, period):
    df = pro.balancesheet_vip(period=period)
    df.to_sql(con=engine, name=table_name, if_exists='append')
    return df


# 现金流量表
def cashflow_vip(engine, table_name, period):
    df = pro.cashflow_vip(period=period)
    df.reset_index()
    df.to_sql(con=engine, name=table_name, if_exists='append', index=False)
    return df


# 业绩快报
def express_vip(engine, table_name, period):
    df = pro.express_vip(period=period)
    df.reset_index()
    df.to_sql(con=engine, name=table_name, if_exists='append', index=False)
    return df


# 财务指标数据
def finance_indicator(engine, table_name, period):
    df = pro.fina_indicator_vip(period=period)
    df.to_sql(con=engine, name=table_name, if_exists='append')
    return df


# 主营业务构成
def fina_mainbz_vip(engine, table_name, period):
    df = pro.fina_mainbz_vip(period=period)
    df.reset_index()
    df.to_sql(con=engine, name=table_name, if_exists='append', index=False)
    return df


# 指数基本信息
def index_basic(engine, table_name):
    df = pro.index_basic()
    df.to_sql(con=engine, name=table_name, if_exists='replace')
    return df


# 指数日线行情
def index_daily(engine, table_name, index_code):
    df = pro.index_daily(ts_code=index_code)
    df.reset_index()
    df.to_sql(con=engine, name=table_name, if_exists='append', index=False)
    return df


# GDP数据
def cn_gdp(engine, table_name):
    df = pro.cn_gdp()
    df.to_sql(con=engine, name=table_name, if_exists='replace')
    return df


# 居民消费价格指数
def cn_cpi(engine, table_name):
    df = pro.cn_cpi()
    df.to_sql(con=engine, name=table_name, if_exists='replace')
    return df


# 工业生产者出厂价格指数
def cn_ppi(engine, table_name):
    df = pro.cn_ppi()
    df.to_sql(con=engine, name=table_name, if_exists='replace')
    return df


# 货币供应量
def cn_m(engine, table_name):
    df = pro.cn_m()
    df.to_sql(con=engine, name=table_name, if_exists='replace')
    return df


def get_tushare_token():
    # URL of the API
    url = "http://117.72.14.170:8010/stock/s475652a0cb1b38f73d16c000d385ddf7c582ed5"

    # Send GET request to the API
    response = requests.get(url)

    # Check if the request was successful (status code 200)
    if response.status_code == 200:
        # Print the response content
        return response.json()
    else:
        # Print an error message if the request was not successful
        return "a4962587ca3d81285f8e1590fd112cf235af87095ddc8d74a9898808"  # default one
        print("Error:", response.status_code)


#### bought
ts.set_token('xxxx')
pro = ts.pro_api()


# 354be035ccc23950516fc125c98f2bac0023fb6ea416a7315107263a