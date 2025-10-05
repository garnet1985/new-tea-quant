"""
企业财务更新配置
"""

CONFIG = {
    'table_name': 'corporate_finance',
    'job_mode': 'multithread',
    'date_field': 'end_date',
    'renew_mode': 'upsert',
    'multithread': {
        'workers': 3,
        'rate_limit': {
            'max_per_minute': 150,
            'buffer': 15
        }
    },
    'rate_limit': {
        'max_per_minute': 150,
        'buffer': 15
    },
    'apis': [
        {
            'name': 'income_statement',
            'method': 'income',
            'params': {
                'ts_code': '{ts_code}',
                'start_date': '{start_date}',
                'end_date': '{end_date}',
                'fields': 'ts_code,ann_date,f_ann_date,end_date,report_type,comp_type,revenue,total_cogs'
            }
        },
        {
            'name': 'balance_sheet',
            'method': 'balancesheet',
            'params': {
                'ts_code': '{ts_code}',
                'start_date': '{start_date}',
                'end_date': '{end_date}',
                'fields': 'ts_code,ann_date,f_ann_date,end_date,report_type,comp_type,total_share,float_share'
            }
        }
    ]
}
