"""
LPR利率更新配置
"""

CONFIG = {
    'is_enabled': True,  # 是否启用此 renewer
    'table_name': 'lpr',
    'renew_mode': 'incremental',  # 增量更新
    
    'date': {
        'field': 'date',           # 数据库字段名
        'storage_format': 'date',   # 数据库存储格式（YYYYMMDD）
        'interval': 'day',         # 更新间隔（LPR按日发布，但不是每天都有）
        'api_format': 'date'       # API需要日期格式（YYYYMMDD）
    },
    
    'job_mode': 'simple',  # 宏观数据只有一个任务
    
    'rate_limit': {
        'max_per_minute': 200,  # Tushare 宏观数据接口限制
    },
    
    # API配置
    'apis': [
        {
            'name': 'lpr_data',
            'method': 'shibor_lpr',
            'params': {
                'start_date': '{start_date}',
                'end_date': '{end_date}',
                'fields': 'date,1y,5y'
            },
            'mapping': {
                # DB字段: API字段
                'date': 'date',
                'lpr_1_y': '1y',
                'lpr_5_y': '5y'
            }
        }
    ]
}
