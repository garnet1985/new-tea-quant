"""
宏观经济价格指数更新配置
包含 CPI、PPI、PMI、货币供应量等宏观经济数据
"""

CONFIG = {
    'is_enabled': True,  # 是否启用此 renewer
    'table_name': 'price_indexes',
    'renew_mode': 'incremental',  # 增量更新
    
    'date': {
        'field': 'date',           # 数据库字段名
        'storage_format': 'month',  # 数据库存储格式（YYYYMM）
        'interval': 'month',       # 更新间隔
        'api_format': 'month',     # API需要月份格式（YYYYMM）
        'disclosure_delay_months': 1  # 披露延迟：月度数据在下个月中旬左右发布
    },
    
    'job_mode': 'simple',  # 宏观数据只有一个任务
    
    'rate_limit': {
        'max_per_minute': 200,  # Tushare 宏观数据接口限制
    },
    
    # API配置 - 4个API需要合并
    'apis': [
        {
            'name': 'cpi_data',
            'method': 'cn_cpi',
            'params': {
                'start_m': '{start_date}',  # BaseRenewer会自动提供
                'end_m': '{end_date}'
            },
            'mapping': {
                'date': 'month',           # DB字段: API字段
                'cpi': 'nt_val',           # CPI当月值
                'cpi_yoy': 'nt_yoy',       # CPI同比
                'cpi_mom': 'nt_mom'        # CPI环比
            },
        },
        {
            'name': 'ppi_data',
            'method': 'cn_ppi',
            'params': {
                'start_m': '{start_date}',
                'end_m': '{end_date}'
            },
            'mapping': {
                'date': 'month',           # DB字段: API字段
                'ppi': 'ppi_accu',         # PPI当月值 (使用累计值)
                'ppi_yoy': 'ppi_yoy',      # PPI同比
                'ppi_mom': 'ppi_mom'       # PPI环比
            }
        },
        {
            'name': 'pmi_data',
            'method': 'cn_pmi',
            'params': {
                'start_m': '{start_date}',
                'end_m': '{end_date}'
            },
            'mapping': {
                'date': 'MONTH',           # DB字段: API字段
                'pmi': 'PMI010000',        # PMI综合指数
                'pmi_l_scale': 'PMI010100', # 大型企业PMI
                'pmi_m_scale': 'PMI010200', # 中型企业PMI  
                'pmi_s_scale': 'PMI010300'  # 小型企业PMI
            }
        },
        {
            'name': 'money_supply_data',
            'method': 'cn_m',
            'params': {
                'start_m': '{start_date}',
                'end_m': '{end_date}'
            },
            'mapping': {
                'date': 'month',          # DB字段: API字段
                'm0': 'm0',               # M0货币供应量
                'm0_yoy': 'm0_yoy',       # M0同比
                'm0_mom': 'm0_mom',       # M0环比
                'm1': 'm1',               # M1货币供应量
                'm1_yoy': 'm1_yoy',       # M1同比
                'm1_mom': 'm1_mom',       # M1环比
                'm2': 'm2',               # M2货币供应量
                'm2_yoy': 'm2_yoy',       # M2同比
                'm2_mom': 'm2_mom'        # M2环比
            }
        }
    ]
}
