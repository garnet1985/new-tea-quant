"""
行业资金流向更新配置（同花顺）
"""

CONFIG = {
    'is_enabled': True,  # 是否启用此 renewer
    'table_name': 'industry_capital_flow',
    'renew_mode': 'incremental',  # 增量更新
    
    'date': {
        'field': 'date',           # 数据库字段名
        'storage_format': 'date',   # 数据库存储格式（YYYYMMDD）
        'interval': 'day',         # 更新间隔
        'api_format': 'date'       # API需要日期格式（YYYYMMDD）
    },
    
    'job_mode': 'simple',  # 宏观数据，单任务即可
    
    'rate_limit': {
        'max_per_minute': 200,  # Tushare 限流
    },
    
    # API配置
    'apis': [
        {
            'name': 'moneyflow_ind_ths',
            'method': 'moneyflow_ind_ths',
            'params': {
                'start_date': '{start_date}',
                'end_date': '{end_date}'
            },
            'mapping': {
                # DB字段: API字段
                'date': 'trade_date',
                'industry': 'industry',
                'industry_id': 'ts_code',
                'company_number': 'company_num',
                'net_buy_amount': 'net_buy_amount',
                'net_sell_amount': 'net_sell_amount',
                'net_amount': 'net_amount',
                'index_change_percent': 'pct_change'
            }
        }
    ]
}

