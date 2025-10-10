"""
LPR利率更新配置
"""

CONFIG = {
    'table_name': 'lpr',
    'job_mode': 'simple',
    'date_field': 'date',
    'renew_mode': 'incremental',
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
                'date': 'date',
                'lpr_1_y': '1y',
                'lpr_5_y': '5y'
            }
        }
    ]
}
