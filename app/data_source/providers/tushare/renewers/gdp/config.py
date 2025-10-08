"""
GDP更新配置
"""

CONFIG = {
    'table_name': 'gdp',
    'job_mode': 'simple',
    'date_field': 'quarter',
    'renew_mode': 'incremental',
    'apis': [
        {
            'name': 'gdp_data',
            'method': 'cn_gdp',
            'params': {
                'start_date': '{start_date}',
                'end_date': '{end_date}'
            },
            'mapping': {
                'quarter': 'quarter',
                'gdp': 'gdp',
                'gdp_yoy': 'gdp_yoy',
                'pi': 'primary_industry',           # 第一产业
                'pi_yoy': 'primary_industry_yoy',   # 第一产业同比
                'si': 'secondary_industry',         # 第二产业
                'si_yoy': 'secondary_industry_yoy', # 第二产业同比
                'ti': 'tertiary_industry',          # 第三产业
                'ti_yoy': 'tertiary_industry_yoy'   # 第三产业同比
            }
        }
    ]
}
