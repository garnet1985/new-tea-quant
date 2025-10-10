"""
宏观经济价格指数更新配置
包含 CPI、PPI、PMI、货币供应量等宏观经济数据
"""

CONFIG = {
    'table_name': 'price_indexes',
    'job_mode': 'simple',
    'date_field': 'date',
    'renew_mode': 'upsert',
    'apis': [
        {
            'name': 'cpi_data',
            'method': 'cn_cpi',
            'params': {
                'start_m': '{start_month}',
                'end_m': '{end_month}'
            },
            'mapping': {
                'month': 'date',
                'nt_val': 'cpi',           # CPI当月值
                'nt_yoy': 'cpi_yoy',       # CPI同比
                'nt_mom': 'cpi_mom'        # CPI环比
            },
        },
        {
            'name': 'ppi_data',
            'method': 'cn_ppi',
            'params': {
                'start_m': '{start_month}',
                'end_m': '{end_month}'
            },
            'mapping': {
                'month': 'date',
                'ppi_accu': 'ppi',         # PPI当月值 (使用累计值)
                'ppi_yoy': 'ppi_yoy',      # PPI同比
                'ppi_mom': 'ppi_mom'       # PPI环比
            }
        },
        {
            'name': 'pmi_data',
            'method': 'cn_pmi',
            'params': {
                'start_m': '{start_month}',
                'end_m': '{end_month}'
            },
            'mapping': {
                'MONTH': 'date',
                'PMI010000': 'pmi',        # PMI综合指数
                'PMI010100': 'pmi_l_scale', # 大型企业PMI
                'PMI010200': 'pmi_m_scale', # 中型企业PMI  
                'PMI010300': 'pmi_s_scale'  # 小型企业PMI
            }
        },
        {
            'name': 'money_supply_data',
            'method': 'cn_m',
            'params': {
                'start_m': '{start_month}',
                'end_m': '{end_month}'
            },
            'mapping': {
                'month': 'date',
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
