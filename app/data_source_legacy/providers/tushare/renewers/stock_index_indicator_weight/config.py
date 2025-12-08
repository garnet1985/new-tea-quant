"""
股指成分股权重更新配置
"""

CONFIG = {
    'is_enabled': True,  # 是否启用此 renewer
    'table_name': 'stock_index_indicator_weight',
    'renew_mode': 'incremental',  # 增量更新
    
    'date': {
        'field': 'date',           # 数据库字段名
        'storage_format': 'date',   # 数据库存储格式（YYYYMMDD）
        'interval': 'month',       # 更新间隔（指数成分股不常变化，月度更新即可）
        'api_format': 'date'       # API需要日期格式（YYYYMMDD）
    },
    
    'job_mode': 'multithread',
    'multithread': {
        'workers': 3,  # 指数数量少
        'log': {
            'success': '✅ 指数 {index_name} {id} 成分股权重更新完毕 - 进度 {progress}%',
            'failure': '❌ 指数 {index_name} {id} 成分股权重更新失败'
        }
    },
    
    'rate_limit': {
        'max_per_minute': 200,  # Tushare 指数权重接口限制
    },
    
    # 指数列表（主要指数）
    'index_list': [
        {'id': '000001.SH', 'name': '上证指数'},
        {'id': '000300.SH', 'name': '沪深300'},
        {'id': '000688.SH', 'name': '科创50'},
        {'id': '399001.SZ', 'name': '深证成指'},
        {'id': '399006.SZ', 'name': '创业板指'},
    ],
    
    # API配置
    'apis': [
        {
            'name': 'index_weight',
            'method': 'index_weight',
            'params': {
                'index_code': '{id}',
                'start_date': '{start_date}',
                'end_date': '{end_date}'
            },
            'mapping': {
                # DB字段: API字段
                'date': 'trade_date',
                'stock_id': 'con_code',  # 成分股代码
                'weight': 'weight'       # 权重
            }
        }
    ]
}

