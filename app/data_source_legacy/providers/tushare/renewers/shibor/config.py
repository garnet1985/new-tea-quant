"""
Shibor更新配置
"""

CONFIG = {
    'is_enabled': True,  # 是否启用此 renewer
    'table_name': 'shibor',
    'renew_mode': 'incremental',  # 增量更新
    
    'date': {
        'field': 'date',           # 数据库字段名
        'storage_format': 'date',   # 数据库存储格式（YYYYMMDD）
        'interval': 'day',         # 更新间隔（每个工作日都有数据）
        'api_format': 'date'       # API需要日期格式（YYYYMMDD）
    },
    
    'job_mode': 'simple',  # 宏观数据只有一个任务
    
    'rate_limit': {
        'max_per_minute': 200,  # Tushare 宏观数据接口限制
    },
    
    # API配置
    'apis': [
        {
            'name': 'shibor_data',
            'method': 'shibor',
            'params': {
                'start_date': '{start_date}',
                'end_date': '{end_date}'
            },
            'mapping': {
                # DB字段: API字段
                'date': 'date',
                'one_night': 'on',      # 隔夜
                'one_week': '1w',       # 1周
                'one_month': '1m',      # 1个月
                'three_month': '3m',    # 3个月
                'one_year': '1y'        # 1年
                # 注意：API 还有 2w, 6m, 9m 字段，但数据库表中没有对应字段，会被忽略
            }
        }
    ]
}
