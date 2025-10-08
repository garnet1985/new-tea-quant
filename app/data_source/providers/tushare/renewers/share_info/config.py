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
    'apis': [
        {
            'name': 'stk_premarket_data',
            'method': 'stk_premarket',
            'params': {
                'ts_code': '{ts_code}',
                'start_date': '{start_date}',
                'end_date': '{end_date}',
                'fields': 'trade_date,ts_code,total_share,float_share'
            },
            'mapping': {
                'ts_code': 'id',                 # 股票代码
                'trade_date': 'quarter',         # 将在预处理阶段转换为季度
                'total_share': 'total_share',    # 总股本（单位：股，预处理会乘以1万）
                'float_share': 'float_share'     # 流通股本（单位：股，预处理会乘以1万）
            }
        }
    ]
}
