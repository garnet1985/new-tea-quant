"""
股本信息更新配置
"""

CONFIG = {
    'table_name': 'share_info',
    'job_mode': 'multithread',
    'date_field': 'quarter',
    'renew_mode': 'incremental',
    'multithread': {
        'workers': 4,
        'rate_limit': {
            'max_per_minute': 200,
            'buffer': 10
        }
    },
    'rate_limit': {
        'max_per_minute': 200,
        'buffer': 10
    },
}
