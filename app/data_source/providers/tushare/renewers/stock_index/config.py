"""
股票指数更新配置
"""
from datetime import datetime

CONFIG = {
    'table_name': 'stock_index',
    'job_mode': 'simple',
    'date_field': 'date',
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
                'exchangeCenter': lambda x: x.get('exchange') or '未知交易所',
                'isAlive': lambda x: 1,  # API返回的股票都是活跃的
                'lastUpdate': lambda x: datetime.now().strftime('%Y-%m-%d')  # 当前更新日期
            }
        }
    ]
}
