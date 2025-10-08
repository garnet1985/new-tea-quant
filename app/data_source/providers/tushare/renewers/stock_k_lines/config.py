"""
股票K线数据更新配置
"""

CONFIG = {
    'table_name': 'stock_klines',
    'job_mode': 'multithread',
    'date_field': 'date',
    'renew_mode': 'incremental',
    'multithread': {
        'workers': 10,
        'enable_monitoring': True
    },
    'rate_limit': {
        'max_per_minute': 800
    },
    'apis': [
        {
            'name': 'daily',
            'method': 'daily',
            'params': {
                'fields': 'ts_code,trade_date,open,high,low,close,pre_close,change,pct_chg,vol,amount'
            },
            'mapping': {
                'id': 'ts_code',
                'date': 'trade_date',
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'preClose': 'pre_close',
                'change': 'change',
                'pctChg': 'pct_chg',
                'volume': 'vol',
                'amount': 'amount'
            }
        }
    ]
}
