"""
股指指标更新配置（指数K线数据）
"""

CONFIG = {
    'table_name': 'stock_index_indicator',
    'renew_mode': 'incremental',  # 增量更新
    
    'date': {
        'field': 'date',           # 数据库字段名
        'storage_format': 'date',   # 数据库存储格式（YYYYMMDD）
        'interval': 'day',         # 更新间隔
        'api_format': 'date'       # API需要日期格式（YYYYMMDD）
    },
    
    'job_mode': 'multithread',
    'multithread': {
        'workers': 3,  # 指数数量少，降低并发
        'log': {
            'success': '✅ 指数 {index_name} {id} [{term}] 更新完毕 - 进度 {progress}%',
            'failure': '❌ 指数 {index_name} {id} [{term}] 更新失败'
        }
    },
    
    'rate_limit': {
        'max_per_minute': 500,  # Tushare 指数接口限制
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
    # 注意：不在这里配置，而是在 renewer 中动态选择（类似 stock_kline）
}

