"""
Shibor更新配置
"""

CONFIG = {
    'table_name': 'shibor',
    'job_mode': 'simple',
    'date_field': 'date',
    'renew_mode': 'upsert',
    'apis': [
        {
            'name': 'shibor_data',
            'method': 'shibor',
            'params': {
                'start_date': '{start_date}',
                'end_date': '{end_date}'
            }
        }
    ]
}
