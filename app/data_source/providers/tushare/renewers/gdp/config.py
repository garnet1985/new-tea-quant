"""
GDP更新配置
"""

CONFIG = {
    'table_name': 'gdp',
    'job_mode': 'simple',
    'date_field': 'date',
    'renew_mode': 'upsert',
    'apis': [
        {
            'name': 'gdp_data',
            'method': 'cn_gdp',
            'params': {
                'start_date': '{start_date}',
                'end_date': '{end_date}'
            }
        }
    ]
}
