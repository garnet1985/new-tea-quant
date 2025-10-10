"""
GDP更新配置
"""

CONFIG = {
    'table_name': 'gdp',
    'renew_mode': 'incremental',  # 增量更新
    
    'date': {
        'field': 'quarter',         # 数据库字段名
        'storage_format': 'quarter', # 数据库存储格式（YYYYQ[1-4]）
        'interval': 'quarter',      # 更新间隔
        'api_format': 'quarter',    # API需要季度格式（YYYYQ[1-4]）
        'disclosure_delay_months': 1  # 披露延迟：季度数据在下季度第一个月发布
    },
    
    'job_mode': 'simple',  # 宏观数据只有一个任务
    
    'rate_limit': {
        'max_per_minute': 200,  # Tushare 宏观数据接口限制
    },
    
    # API配置
    'apis': [
        {
            'name': 'gdp_data',
            'method': 'cn_gdp',
            'params': {
                'start_q': '{start_date}',  # 注意：API参数名是 start_q, end_q
                'end_q': '{end_date}'
            },
            'mapping': {
                # DB字段: API字段
                'quarter': 'quarter',
                'gdp': 'gdp',
                'gdp_yoy': 'gdp_yoy',
                'primary_industry': 'pi',           # 第一产业
                'primary_industry_yoy': 'pi_yoy',   # 第一产业同比
                'secondary_industry': 'si',         # 第二产业
                'secondary_industry_yoy': 'si_yoy', # 第二产业同比
                'tertiary_industry': 'ti',          # 第三产业
                'tertiary_industry_yoy': 'ti_yoy'   # 第三产业同比
            }
        }
    ]
}
