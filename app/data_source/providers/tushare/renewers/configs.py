"""
通用更新器配置
定义各种数据类型的更新配置
"""
from app.data_source.providers.tushare.main_service import TushareService


def safe_float(value):
    """安全转换为float"""
    return TushareService.safe_to_float(value)


def safe_str(value):
    """安全转换为字符串"""
    if value is None:
        return ""
    return str(value).strip()


# 行业资金流向配置
INDUSTRY_CAPITAL_FLOW_CONFIG = {
    'table_name': 'industry_capital_flow',
    'api_method': 'moneyflow_ind_ths',
    'mode': 'simple',
    'field_mapping': {
        'date': 'trade_date',
        'industry': 'industry',
        'industry_id': 'ts_code',
        'company_number': lambda x: safe_float(x.get('company_num', 0)),
        'net_buy_amount': lambda x: safe_float(x.get('net_buy_amount', 0)),
        'net_sell_amount': lambda x: safe_float(x.get('net_sell_amount', 0)),
        'net_amount': lambda x: safe_float(x.get('net_amount', 0)),
        'index_change_percent': lambda x: safe_float(x.get('pct_change', 0))
    },
    'primary_keys': ['date', 'industry_id'],
    'required_fields': ['date', 'industry', 'industry_id']
}

# LPR配置
LPR_CONFIG = {
    'table_name': 'lpr',
    'api_method': 'shibor_lpr',
    'mode': 'simple',
    'field_mapping': {
        'date': 'date',
        'LPR_1Y': lambda x: safe_float(x.get('1y') or x.get('lpr_1y') or x.get('LPR_1Y')),
        'LPR_5Y': lambda x: safe_float(x.get('5y') or x.get('lpr_5y') or x.get('LPR_5Y'))
    },
    'primary_keys': ['date'],
    'api_params': {'fields': 'date,1y,5y'},
    'data_converter': lambda df: [
        {
            'date': str(r.get('date') or r.get('DATE') or '').strip(),
            'LPR_1Y': safe_float(r.get('1y') or r.get('lpr_1y') or r.get('LPR_1Y')),
            'LPR_5Y': safe_float(r.get('5y') or r.get('lpr_5y') or r.get('LPR_5Y'))
        }
        for _, r in df.iterrows()
    ] if df is not None and not df.empty else []
}

# Shibor配置
SHIBOR_CONFIG = {
    'table_name': 'shibor',
    'api_method': 'shibor',
    'mode': 'simple',
    'field_mapping': {
        'date': 'date',
        'one_night': lambda x: safe_float(x.get('on') or x.get('ON')),
        'one_week': lambda x: safe_float(x.get('1w') or x.get('1W')),
        'one_month': lambda x: safe_float(x.get('1m') or x.get('1M')),
        'three_month': lambda x: safe_float(x.get('3m') or x.get('3M')),
        'one_year': lambda x: safe_float(x.get('1y') or x.get('1Y'))
    },
    'primary_keys': ['date'],
    'api_params': {'fields': 'date,on,1w,1m,3m,1y'},
    'data_converter': lambda df: [
        {
            'date': str(r.get('date') or r.get('DATE') or '').strip(),
            'one_night': safe_float(r.get('on') or r.get('ON')),
            'one_week': safe_float(r.get('1w') or r.get('1W')),
            'one_month': safe_float(r.get('1m') or r.get('1M')),
            'three_month': safe_float(r.get('3m') or r.get('3M')),
            'one_year': safe_float(r.get('1y') or r.get('1Y'))
        }
        for _, r in df.iterrows()
    ] if df is not None and not df.empty else []
}

# GDP配置
GDP_CONFIG = {
    'table_name': 'gdp',
    'api_method': 'cn_gdp',
    'mode': 'simple',
    'field_mapping': {
        'quarter': 'quarter',
        'gdp': lambda x: safe_float(x.get('gdp') or x.get('GDP')),
        'gdp_yoy': lambda x: safe_float(x.get('gdp_yoy') or x.get('GDP_YOY')),
        'primary_industry': lambda x: safe_float(x.get('pi') or x.get('PI')),
        'primary_industry_yoy': lambda x: safe_float(x.get('pi_yoy') or x.get('PI_YOY')),
        'secondary_industry': lambda x: safe_float(x.get('si') or x.get('SI')),
        'secondary_industry_yoy': lambda x: safe_float(x.get('si_yoy') or x.get('SI_YOY')),
        'tertiary_industry': lambda x: safe_float(x.get('ti') or x.get('TI')),
        'tertiary_industry_yoy': lambda x: safe_float(x.get('ti_yoy') or x.get('TI_YOY'))
    },
    'primary_keys': ['quarter'],
    'api_params': {'fields': 'quarter,gdp,gdp_yoy,pi,pi_yoy,si,si_yoy,ti,ti_yoy'},
    'date_param_mapping': {'start': 'start_m', 'end': 'end_m'},
    'date_field': 'quarter',
    'data_converter': lambda df: [
        {
            'quarter': str(r.get('quarter') or r.get('QUARTER') or '').strip(),
            'gdp': safe_float(r.get('gdp') or r.get('GDP')),
            'gdp_yoy': safe_float(r.get('gdp_yoy') or r.get('GDP_YOY')),
            'primary_industry': safe_float(r.get('pi') or r.get('PI')),
            'primary_industry_yoy': safe_float(r.get('pi_yoy') or r.get('PI_YOY')),
            'secondary_industry': safe_float(r.get('si') or r.get('SI')),
            'secondary_industry_yoy': safe_float(r.get('si_yoy') or r.get('SI_YOY')),
            'tertiary_industry': safe_float(r.get('ti') or r.get('TI')),
            'tertiary_industry_yoy': safe_float(r.get('ti_yoy') or r.get('TI_YOY'))
        }
        for _, r in df.iterrows()
    ] if df is not None and not df.empty else []
}

# 股票指数指标配置
STOCK_INDEX_INDICATOR_CONFIG = {
    'table_name': 'stock_index_indicator',
    'api_method': 'index_daily',
    'mode': 'multithread',
    'field_mapping': {
        'id': 'ts_code',
        'term': lambda x: 'daily',
        'date': 'trade_date',
        'open': lambda x: safe_float(x.get('open')),
        'close': lambda x: safe_float(x.get('close')),
        'highest': lambda x: safe_float(x.get('high')),
        'lowest': lambda x: safe_float(x.get('low')),
        'priceChangeDelta': lambda x: safe_float(x.get('pct_chg')),
        'priceChangeRateDelta': lambda x: safe_float(x.get('pct_chg')),
        'preClose': lambda x: safe_float(x.get('pre_close')),
        'volume': lambda x: safe_float(x.get('vol')),
        'amount': lambda x: safe_float(x.get('amount'))
    },
    'primary_keys': ['id', 'term', 'date'],
    'max_workers': 4,
    'job_builder': lambda start_date, end_date: [
        {
            'start_date': start_date,
            'end_date': end_date,
            'api_method': 'index_daily',
            'api_params': {'ts_code': index_id}
        }
        for index_id in ['000001.SH', '399001.SZ', '000300.SH', '399006.SZ', '000688.SH']
    ]
}

# 股票指数指标权重配置
STOCK_INDEX_INDICATOR_WEIGHT_CONFIG = {
    'table_name': 'stock_index_indicator_weight',
    'api_method': 'index_weight',
    'mode': 'multithread',
    'field_mapping': {
        'id': 'index_code',
        'date': 'trade_date',
        'stock_id': 'con_code',
        'weight': lambda x: safe_float(x.get('weight'))
    },
    'primary_keys': ['id', 'date', 'stock_id'],
    'max_workers': 4,
    'data_filter': lambda item: item.get('weight', 0) > 0,
    'job_builder': lambda start_date, end_date: [
        {
            'start_date': start_date,
            'end_date': end_date,
            'api_method': 'index_weight',
            'api_params': {'index_code': index_id}
        }
        for index_id in ['000001.SH', '399001.SZ', '000300.SH', '399006.SZ', '000688.SH']
    ]
}

# 价格指数配置（多表合并）
PRICE_INDEXES_CONFIG = {
    'table_name': 'price_indexes',
    'api_method': 'multi_table_merge',  # 特殊标识
    'mode': 'simple',
    'field_mapping': {
        'id': lambda x: 'CN',
        'date': lambda x: x.get('date'),
        'CPI': lambda x: x.get('CPI', 0.0),
        'CPI_yoy': lambda x: x.get('CPI_yoy', 0.0),
        'CPI_mom': lambda x: x.get('CPI_mom', 0.0),
        'PPI': lambda x: x.get('PPI', 0.0),
        'PPI_yoy': lambda x: x.get('PPI_yoy', 0.0),
        'PPI_mom': lambda x: x.get('PPI_mom', 0.0),
        'PMI': lambda x: x.get('PMI', 0.0),
        'PMI_l_scale': lambda x: x.get('PMI_l_scale', 0.0),
        'PMI_m_scale': lambda x: x.get('PMI_m_scale', 0.0),
        'PMI_s_scale': lambda x: x.get('PMI_s_scale', 0.0),
        'M0': lambda x: x.get('M0', 0.0),
        'M0_yoy': lambda x: x.get('M0_yoy', 0.0),
        'M0_mom': lambda x: x.get('M0_mom', 0.0),
        'M1': lambda x: x.get('M1', 0.0),
        'M1_yoy': lambda x: x.get('M1_yoy', 0.0),
        'M1_mom': lambda x: x.get('M1_mom', 0.0),
        'M2': lambda x: x.get('M2', 0.0),
        'M2_yoy': lambda x: x.get('M2_yoy', 0.0),
        'M2_mom': lambda x: x.get('M2_mom', 0.0)
    },
    'primary_keys': ['id', 'date'],
    'custom_fetcher': 'price_indexes_fetcher'  # 自定义获取器
}

# 股票指数配置
STOCK_INDEX_CONFIG = {
    'table_name': 'stock_index',
    'api_method': 'stock_basic',
    'mode': 'simple',
    'field_mapping': {
        'id': 'ts_code',
        'name': 'name',
        'industry': 'industry',
        'type': 'market',
        'exchangeCenter': 'exchange',
        'isAlive': lambda x: 1,
        'lastUpdate': lambda x: "2025-09-26 00:00:00"
    },
    'primary_keys': ['id'],
    'date_field': 'lastUpdate',  # 使用lastUpdate字段进行增量更新
    'api_params': {
        'exchange': '',
        'list_status': 'L',
        'fields': 'ts_code,symbol,name,area,industry,market,exchange,list_date'
    },
    'return_data': True,  # 需要返回数据
    'return_data_getter': lambda renewer: renewer._load_stock_index_data()  # 自定义数据获取器
}

# 配置映射
CONFIG_MAP = {
    'industry_capital_flow': INDUSTRY_CAPITAL_FLOW_CONFIG,
    'lpr': LPR_CONFIG,
    'shibor': SHIBOR_CONFIG,
    'gdp': GDP_CONFIG,
    'stock_index_indicator': STOCK_INDEX_INDICATOR_CONFIG,
    'stock_index_indicator_weight': STOCK_INDEX_INDICATOR_WEIGHT_CONFIG,
    'price_indexes': PRICE_INDEXES_CONFIG,
    'stock_index': STOCK_INDEX_CONFIG
}
