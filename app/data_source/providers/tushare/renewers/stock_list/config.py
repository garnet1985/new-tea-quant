"""
股票列表更新配置（替代 stock_index，排除北交所）
"""
from datetime import datetime


CONFIG = {
    'table_name': 'stock_list',
    'job_mode': 'simple',
    'date': {
        'format': 'YYYYMMDD',
        'interval': 'day',
        'field': 'last_update'
    },
    'renew_mode': 'upsert',
    'apis': [
        {
            'name': 'stock_basic',
            'method': 'stock_basic',
            'params': {
                'fields': 'ts_code,symbol,name,area,industry,market,exchange,list_date'
            },
            'mapping': {
                'id': 'ts_code',
                'name': 'name',
                'industry': lambda x: x.get('industry') or '未知行业',
                'type': lambda x: x.get('market') or '未知类型',
                'exchange_center': lambda x: x.get('exchange') or '未知交易所',
                'is_active': lambda x: 1,
                'last_update': lambda x: datetime.now().strftime('%Y-%m-%d')
            }
        }
    ]
}


