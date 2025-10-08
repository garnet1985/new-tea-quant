"""
Shibor更新配置
"""

CONFIG = {
    'table_name': 'shibor',
    'job_mode': 'simple',
    'date_field': 'date',
    'renew_mode': 'incremental',
    'apis': [
        {
            'name': 'shibor_data',
            'method': 'shibor',
            'params': {
                'start_date': '{start_date}',
                'end_date': '{end_date}'
            },
            'mapping': {
                'date': 'date',
                'on': 'one_night',      # 隔夜
                '1w': 'one_week',       # 1周
                '1m': 'one_month',      # 1个月
                '3m': 'three_month',    # 3个月
                '1y': 'one_year'        # 1年
                # 注意：API 还有 2w, 6m, 9m 字段，但数据库表中没有对应字段，会被忽略
            }
        }
    ]
}
