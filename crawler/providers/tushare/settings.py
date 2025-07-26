# Tushare API settings

# Token configuration
auth_token = 'crawler/providers/tushare/auth/token.txt'

# Date settings
default_start_date = '20080101'

# API settings
base_url = 'http://117.72.14.170:8010'
token_endpoint = '/stock/s475652a0cb1b38f73d16c000d385ddf7c582ed5'


STOCK_INDEX_FIELDS = 'ts_code,name,area,industry,market,exchange,list_date'

# API field mappings
STOCK_BASIC_FIELDS = 'ts_code,symbol,name,area,industry,market,exchange,list_date'
STOCK_DAILY_FIELDS = 'ts_code,trade_date,open,high,low,close,pre_close,change,pct_chg,vol,amount'
INDEX_DAILY_FIELDS = 'ts_code,trade_date,close,open,high,low,pre_close,change,pct_chg,vol,amount'






