from dataclasses import dataclass
from typing import Any, Optional, Callable, Dict


@dataclass
class Field:
    """Schema 字段定义"""
    type: type
    required: bool = True
    default: Optional[Any] = None
    description: str = ""
    validator: Optional[Callable] = None


class DataSourceSchema:
    """
    数据源 Schema 定义
    
    定义 Handler 的 normalize 方法需要将 Provider 返回的数据转换成什么格式
    schema 中的 key 是数据库字段名（normalize 后的输出字段名）
    """
    
    def __init__(self, name: str, schema: Dict[str, Field], description: str = ""):
        self.name = name
        self.schema = schema
        self.description = description
    
    def validate(self, data: dict) -> bool:
        """
        验证数据是否符合 schema
        
        验证规则：
        1. 数据必须是字典，且包含 'data' 键
        2. 'data' 必须是一个列表
        3. 列表中的每条记录必须包含所有 required 字段
        4. 字段类型必须匹配（如果提供了值）
        """
        if not isinstance(data, dict):
            return False
        
        if 'data' not in data:
            return False
        
        data_list = data['data']
        if not isinstance(data_list, list):
            return False
        
        # 如果列表为空，认为验证通过（可能是没有数据）
        if len(data_list) == 0:
            return True
        
        # 验证列表中的每条记录
        for record in data_list:
            if not isinstance(record, dict):
                return False
            
            # 检查所有 required 字段是否存在
            for field_name, field_def in self.schema.items():
                if field_def.required:
                    if field_name not in record:
                        return False
                    
                    # 检查字段类型（如果值不是 None）
                    value = record[field_name]
                    if value is not None:
                        # 允许类型转换（int/float 可以互相转换）
                        expected_type = field_def.type
                        if expected_type == int and isinstance(value, (int, float)):
                            continue
                        elif expected_type == float and isinstance(value, (int, float)):
                            continue
                        elif not isinstance(value, expected_type):
                            return False
        
        return True


# ========== 股票相关数据源 ==========

STOCK_LIST = DataSourceSchema(
    name="stock_list",
    description="股票列表",
    schema={
        "id": Field(str, required=True, description="股票代码ts_code"),
        "name": Field(str, required=True, description="股票名称"),
        "industry": Field(str, required=True, description="所属行业"),
        "type": Field(str, required=True, description="股票类型（市场）"),
        "exchange_center": Field(str, required=True, description="交易所"),
        "is_active": Field(int, required=True, description="是否活跃（1=活跃）"),
        "last_update": Field(str, required=True, description="最后更新时间（YYYY-MM-DD）"),
    }
)

KLINE = DataSourceSchema(
    name="kline",
    description="K线数据（支持 daily/weekly/monthly 周期）",
    schema={
        "id": Field(str, required=True, description="股票代码ts_code"),
        "term": Field(str, required=True, description="K线周期（daily/weekly/monthly）"),
        "date": Field(str, required=True, description="交易日期（YYYYMMDD）"),
        "open": Field(float, required=True, description="开盘价"),
        "close": Field(float, required=True, description="收盘价"),
        "highest": Field(float, required=True, description="最高价"),
        "lowest": Field(float, required=True, description="最低价"),
        "pre_close": Field(float, required=True, description="昨收价（除权价，前复权）"),
        "price_change_delta": Field(float, required=True, description="涨跌额"),
        "price_change_rate_delta": Field(float, required=True, description="涨跌幅"),
        "volume": Field(int, required=True, description="成交量"),
        "amount": Field(float, required=True, description="成交额"),
        # 以下字段来自 daily_basic API（可选，主要用于日线数据）
        "turnover_rate": Field(float, required=False, description="换手率"),
        "free_turnover_rate": Field(float, required=False, description="自由流通股换手率"),
        "volume_ratio": Field(float, required=False, description="量比"),
        "pe": Field(float, required=False, description="市盈率"),
        "pe_ttm": Field(float, required=False, description="市盈率TTM"),
        "pb": Field(float, required=False, description="市净率"),
        "ps": Field(float, required=False, description="市销率"),
        "ps_ttm": Field(float, required=False, description="市销率TTM"),
        "dv_ratio": Field(float, required=False, description="分红比例"),
        "dv_ttm": Field(float, required=False, description="分红比例TTM"),
        "total_share": Field(int, required=False, description="总股本"),
        "float_share": Field(int, required=False, description="流通股本"),
        "free_share": Field(int, required=False, description="自由流通股本"),
        "total_market_value": Field(float, required=False, description="总市值"),
        "circ_market_value": Field(float, required=False, description="流通市值"),
    }
)

CORPORATE_FINANCE = DataSourceSchema(
    name="corporate_finance",
    description="企业财务数据（季度）",
    schema={
        "id": Field(str, required=True, description="股票代码ts_code"),
        "quarter": Field(str, required=True, description="季度（YYYYQ[1-4]）"),
        # 盈利能力指标
        "eps": Field(float, required=True, description="每股收益"),
        "dt_eps": Field(float, required=True, description="稀释每股收益"),
        "roe": Field(float, required=True, description="净资产收益率"),
        "roe_dt": Field(float, required=True, description="扣非净资产收益率"),
        "roa": Field(float, required=True, description="总资产收益率"),
        "netprofit_margin": Field(float, required=True, description="销售净利率"),
        "gross_profit_margin": Field(float, required=True, description="毛利率"),
        "op_income": Field(float, required=True, description="经营活动净收益"),
        "roic": Field(float, required=True, description="投入资本回报率"),
        "ebit": Field(float, required=True, description="息税前利润"),
        "ebitda": Field(float, required=True, description="息税折旧摊销前利润"),
        "dtprofit_to_profit": Field(float, required=True, description="扣非净利润/净利润"),
        "profit_dedt": Field(float, required=True, description="净利润/扣非净利润"),
        # 成长能力指标
        "or_yoy": Field(float, required=True, description="营业收入同比增长率(%)"),
        "netprofit_yoy": Field(float, required=True, description="净利润同比增长率(%)"),
        "basic_eps_yoy": Field(float, required=True, description="每股收益同比增长率(%)"),
        "dt_eps_yoy": Field(float, required=True, description="稀释每股收益同比增长率(%)"),
        "tr_yoy": Field(float, required=True, description="营业总收入同比增长率(%)"),
        # 偿债能力指标
        "netdebt": Field(float, required=True, description="净债务"),
        "debt_to_eqt": Field(float, required=True, description="产权比率"),
        "debt_to_assets": Field(float, required=True, description="资产负债率"),
        "interestdebt": Field(float, required=True, description="带息债务"),
        "assets_to_eqt": Field(float, required=True, description="权益乘数"),
        "quick_ratio": Field(float, required=True, description="速动比率"),
        "current_ratio": Field(float, required=True, description="流动比率"),
        # 运营能力指标
        "ar_turn": Field(float, required=True, description="应收账款周转率"),
        # 资产状况指标
        "bps": Field(float, required=True, description="每股净资产"),
        # 现金流指标
        "ocfps": Field(float, required=True, description="每股经营活动产生的现金流量净额"),
        "fcff": Field(float, required=True, description="企业自由现金流量"),
        "fcfe": Field(float, required=True, description="股东自由现金流量"),
    }
)

# ========== 宏观经济数据源 ==========

GDP = DataSourceSchema(
    name="gdp",
    description="GDP数据（季度）",
    schema={
        "quarter": Field(str, required=True, description="季度（YYYYQ[1-4]）"),
        "gdp": Field(float, required=True, description="GDP"),
        "gdp_yoy": Field(float, required=True, description="GDP同比"),
        "primary_industry": Field(float, required=True, description="第一产业"),
        "primary_industry_yoy": Field(float, required=True, description="第一产业同比"),
        "secondary_industry": Field(float, required=True, description="第二产业"),
        "secondary_industry_yoy": Field(float, required=True, description="第二产业同比"),
        "tertiary_industry": Field(float, required=True, description="第三产业"),
        "tertiary_industry_yoy": Field(float, required=True, description="第三产业同比"),
    }
)

# 注意：CPI、PPI、PMI、货币供应量合并到 price_indexes 表中
PRICE_INDEXES = DataSourceSchema(
    name="price_indexes",
    description="价格指数数据（月度，包含CPI/PPI/PMI/货币供应量）",
    schema={
        "date": Field(str, required=True, description="月份（YYYYMM）"),
        # CPI 指标
        "cpi": Field(float, required=True, description="CPI当月值"),
        "cpi_yoy": Field(float, required=True, description="CPI同比"),
        "cpi_mom": Field(float, required=True, description="CPI环比"),
        # PPI 指标
        "ppi": Field(float, required=True, description="PPI当月值"),
        "ppi_yoy": Field(float, required=True, description="PPI同比"),
        "ppi_mom": Field(float, required=True, description="PPI环比"),
        # PMI 指标
        "pmi": Field(float, required=True, description="PMI综合指数"),
        "pmi_l_scale": Field(float, required=True, description="大型企业PMI"),
        "pmi_m_scale": Field(float, required=True, description="中型企业PMI"),
        "pmi_s_scale": Field(float, required=True, description="小型企业PMI"),
        # 货币供应量指标
        "m0": Field(float, required=True, description="M0货币供应量"),
        "m0_yoy": Field(float, required=True, description="M0同比"),
        "m0_mom": Field(float, required=True, description="M0环比"),
        "m1": Field(float, required=True, description="M1货币供应量"),
        "m1_yoy": Field(float, required=True, description="M1同比"),
        "m1_mom": Field(float, required=True, description="M1环比"),
        "m2": Field(float, required=True, description="M2货币供应量"),
        "m2_yoy": Field(float, required=True, description="M2同比"),
        "m2_mom": Field(float, required=True, description="M2环比"),
    }
)

SHIBOR = DataSourceSchema(
    name="shibor",
    description="Shibor利率数据（日度）",
    schema={
        "date": Field(str, required=True, description="日期（YYYYMMDD）"),
        "one_night": Field(float, required=True, description="隔夜"),
        "one_week": Field(float, required=True, description="1周"),
        "one_month": Field(float, required=True, description="1个月"),
        "three_month": Field(float, required=True, description="3个月"),
        "one_year": Field(float, required=True, description="1年"),
    }
)

LPR = DataSourceSchema(
    name="lpr",
    description="LPR利率数据（日度）",
    schema={
        "date": Field(str, required=True, description="日期（YYYYMMDD）"),
        "lpr_1_y": Field(float, required=True, description="1年期LPR"),
        "lpr_5_y": Field(float, required=False, description="5年期LPR（可能为空）"),
    }
)

CPI = DataSourceSchema(
    name="cpi",
    description="CPI价格指数数据（月度）",
    schema={
        "date": Field(str, required=True, description="月份（YYYYMM）"),
        "cpi": Field(float, required=True, description="CPI当月值"),
        "cpi_yoy": Field(float, required=True, description="CPI同比"),
        "cpi_mom": Field(float, required=True, description="CPI环比"),
    }
)

PPI = DataSourceSchema(
    name="ppi",
    description="PPI价格指数数据（月度）",
    schema={
        "date": Field(str, required=True, description="月份（YYYYMM）"),
        "ppi": Field(float, required=True, description="PPI当月值"),
        "ppi_yoy": Field(float, required=True, description="PPI同比"),
        "ppi_mom": Field(float, required=True, description="PPI环比"),
    }
)

PMI = DataSourceSchema(
    name="pmi",
    description="PMI采购经理人指数数据（月度）",
    schema={
        "date": Field(str, required=True, description="月份（YYYYMM）"),
        "pmi": Field(float, required=True, description="PMI综合指数"),
        "pmi_l_scale": Field(float, required=True, description="大型企业PMI"),
        "pmi_m_scale": Field(float, required=True, description="中型企业PMI"),
        "pmi_s_scale": Field(float, required=True, description="小型企业PMI"),
    }
)

MONEY_SUPPLY = DataSourceSchema(
    name="money_supply",
    description="货币供应量数据（月度）",
    schema={
        "date": Field(str, required=True, description="月份（YYYYMM）"),
        "m0": Field(float, required=True, description="M0货币供应量"),
        "m0_yoy": Field(float, required=True, description="M0同比"),
        "m0_mom": Field(float, required=True, description="M0环比"),
        "m1": Field(float, required=True, description="M1货币供应量"),
        "m1_yoy": Field(float, required=True, description="M1同比"),
        "m1_mom": Field(float, required=True, description="M1环比"),
        "m2": Field(float, required=True, description="M2货币供应量"),
        "m2_yoy": Field(float, required=True, description="M2同比"),
        "m2_mom": Field(float, required=True, description="M2环比"),
    }
)

# ========== 其他数据源 ==========

ADJ_FACTOR = DataSourceSchema(
    name="adj_factor",
    description="复权因子数据（旧表，每日存储）",
    schema={
        "id": Field(str, required=True, description="股票代码ts_code"),
        "date": Field(str, required=True, description="复权事件日期（YYYYMMDD）"),
        "qfq": Field(float, required=True, description="前复权因子"),
        "hfq": Field(float, required=True, description="后复权因子"),
        "last_update": Field(str, required=False, description="记录创建时间（可选，数据库自动生成）"),
    }
)

ADJ_FACTOR_EVENT = DataSourceSchema(
    name="adj_factor_event",
    description="复权因子事件数据（新表，只存储除权日）",
    schema={
        "id": Field(str, required=True, description="股票代码ts_code"),
        "event_date": Field(str, required=True, description="除权除息日期（YYYYMMDD）"),
        "tushare_factor": Field(float, required=True, description="Tushare 复权因子 F(t)"),
        "qfq_diff": Field(float, required=False, description="与 EastMoney 前复权价格的固定差异（raw_price - eastmoney_qfq）"),
    }
)


# ========== 系统数据源 ==========

LATEST_TRADING_DATE = DataSourceSchema(
    name="latest_trading_date",
    description="最新交易日",
    schema={
        "date": Field(str, required=True, description="最新交易日（YYYYMMDD格式）"),
    }
)

DEFAULT_SCHEMAS = {
    "stock_list": STOCK_LIST,
    "kline": KLINE,
    "corporate_finance": CORPORATE_FINANCE,
    "gdp": GDP,
    "price_indexes": PRICE_INDEXES,  # 包含 CPI/PPI/PMI/货币供应量（合并版本）
    "cpi": CPI,
    "ppi": PPI,
    "pmi": PMI,
    "money_supply": MONEY_SUPPLY,
    "shibor": SHIBOR,
    "lpr": LPR,
    "adj_factor": ADJ_FACTOR,
    "adj_factor_event": ADJ_FACTOR_EVENT,
    "latest_trading_date": LATEST_TRADING_DATE,
}

