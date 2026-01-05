"""
Tushare Provider 实现

纯 API 封装，不包含业务逻辑
"""
import tushare as ts
from typing import Dict, Any, Optional
from loguru import logger

from app.core.modules.data_source.base_provider import BaseProvider


class TushareProvider(BaseProvider):
    """
    Tushare 数据提供者
    
    纯 API 封装，不包含业务逻辑
    """
    
    provider_name = "tushare"
    requires_auth = True
    auth_type = "token"
    
    # 声明每个 API 的限流（每分钟请求数）
    # 参考 legacy 代码中的实际配置
    api_limits = {
        "get_stock_list": 800,          # 股票列表，使用K线限流（800次/分钟）
        "get_daily_kline": 700,         # 日线数据
        "get_weekly_kline": 700,        # 周线数据
        "get_monthly_kline": 700,       # 月线数据
        "get_daily_basic": 700,         # 日线基本面数据
        "get_adj_factor": 800,          # 复权因子，使用K线限流
        "get_finance_data": 500,        # 财务数据（fina_indicator接口限制500次/分钟）
        "get_trade_cal": 200,           # 交易日历，宏观数据接口限制200次/分钟
        "get_gdp": 200,                 # GDP数据，宏观数据接口限制200次/分钟
        "get_cpi": 200,                 # CPI数据，宏观数据接口限制200次/分钟
        "get_ppi": 200,                 # PPI数据，宏观数据接口限制200次/分钟
        "get_pmi": 200,                 # PMI数据，宏观数据接口限制200次/分钟
        "get_shibor": 200,              # Shibor数据，宏观数据接口限制200次/分钟
        "get_lpr": 200,                 # LPR数据，宏观数据接口限制200次/分钟
        "get_money_supply": 200,        # 货币供应量，宏观数据接口限制200次/分钟
        "get_moneyflow_ind_ths": 200,   # 行业资金流向，宏观数据接口限制200次/分钟
        "get_index_daily": 500,         # 指数日线，指数接口限制500次/分钟
        "get_index_weekly": 500,        # 指数周线，指数接口限制500次/分钟
        "get_index_monthly": 500,       # 指数月线，指数接口限制500次/分钟
        "get_index_weight": 200,        # 指数权重，指数接口限制200次/分钟
    }
    
    default_rate_limit = 200  # 默认限流（保守值）
    
    def _initialize(self):
        """初始化 Tushare API 客户端"""
        token = self.config.get("token")
        if not token:
            raise ValueError("Tushare token is required")
        
        ts.set_token(token)
        self.api = ts.pro_api()
    
    # ========== API 方法（纯封装）==========
    
    def get_stock_list(self, **kwargs):
        """
        获取股票列表
        
        Tushare API: stock_basic
        
        Returns:
            DataFrame: 股票列表数据
        """
        try:
            return self.api.stock_basic(**kwargs)
        except Exception as e:
            raise self.handle_error(e, "get_stock_list")
    
    def get_daily_kline(self, ts_code: str, start_date: str, end_date: str, **kwargs):
        """
        获取日线数据
        
        Tushare API: daily
        
        Args:
            ts_code: 股票代码
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
        
        Returns:
            DataFrame: 日线数据
        """
        try:
            return self.api.daily(
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date,
                **kwargs
            )
        except Exception as e:
            raise self.handle_error(e, "get_daily_kline")
    
    def get_weekly_kline(self, ts_code: str, start_date: str, end_date: str, **kwargs):
        """
        获取周线数据
        
        Tushare API: weekly
        
        Args:
            ts_code: 股票代码
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
        
        Returns:
            DataFrame: 周线数据
        """
        try:
            return self.api.weekly(
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date,
                **kwargs
            )
        except Exception as e:
            raise self.handle_error(e, "get_weekly_kline")
    
    def get_monthly_kline(self, ts_code: str, start_date: str, end_date: str, **kwargs):
        """
        获取月线数据
        
        Tushare API: monthly
        
        Args:
            ts_code: 股票代码
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
        
        Returns:
            DataFrame: 月线数据
        """
        try:
            return self.api.monthly(
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date,
                **kwargs
            )
        except Exception as e:
            raise self.handle_error(e, "get_monthly_kline")
    
    def get_adj_factor(self, ts_code: str, start_date: str, end_date: str, **kwargs):
        """
        获取复权因子
        
        Tushare API: adj_factor
        
        Args:
            ts_code: 股票代码
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
        
        Returns:
            DataFrame: 复权因子数据
        """
        try:
            return self.api.adj_factor(
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date,
                **kwargs
            )
        except Exception as e:
            raise self.handle_error(e, "get_adj_factor")
    
    def get_finance_data(self, ts_code: str, start_date: str = None, end_date: str = None, **kwargs):
        """
        获取财务数据
        
        Tushare API: fina_indicator
        
        Args:
            ts_code: 股票代码
            start_date: 开始日期 (YYYYMMDD) 或季度 (YYYYQ[1-4])
            end_date: 结束日期 (YYYYMMDD) 或季度 (YYYYQ[1-4])
        
        Returns:
            DataFrame: 财务数据
        """
        try:
            params = {"ts_code": ts_code, **kwargs}
            if start_date:
                params["start_date"] = start_date
            if end_date:
                params["end_date"] = end_date
            return self.api.fina_indicator(**params)
        except Exception as e:
            raise self.handle_error(e, "get_finance_data")
    
    def get_gdp(self, start_date: str = None, end_date: str = None, **kwargs):
        """
        获取 GDP 数据
        
        Tushare API: cn_gdp
        
        Args:
            start_date: 开始季度 (YYYYQ[1-4])，会转换为 start_q 参数
            end_date: 结束季度 (YYYYQ[1-4])，会转换为 end_q 参数
        
        Returns:
            DataFrame: GDP数据
        """
        try:
            params = kwargs.copy()
            if start_date:
                params["start_q"] = start_date  # Tushare API 使用 start_q
            if end_date:
                params["end_q"] = end_date  # Tushare API 使用 end_q
            return self.api.cn_gdp(**params)
        except Exception as e:
            raise self.handle_error(e, "get_gdp")
    
    def get_cpi(self, start_date: str = None, end_date: str = None, **kwargs):
        """
        获取 CPI 数据
        
        Tushare API: cn_cpi
        
        Args:
            start_date: 开始月份 (YYYYMM)，会转换为 start_m 参数
            end_date: 结束月份 (YYYYMM)，会转换为 end_m 参数
        
        Returns:
            DataFrame: CPI数据
        """
        try:
            params = kwargs.copy()
            if start_date:
                params["start_m"] = start_date
            if end_date:
                params["end_m"] = end_date
            return self.api.cn_cpi(**params)
        except Exception as e:
            raise self.handle_error(e, "get_cpi")
    
    def get_ppi(self, start_date: str = None, end_date: str = None, **kwargs):
        """
        获取 PPI 数据
        
        Tushare API: cn_ppi
        
        Args:
            start_date: 开始月份 (YYYYMM)，会转换为 start_m 参数
            end_date: 结束月份 (YYYYMM)，会转换为 end_m 参数
        
        Returns:
            DataFrame: PPI数据
        """
        try:
            params = kwargs.copy()
            if start_date:
                params["start_m"] = start_date
            if end_date:
                params["end_m"] = end_date
            return self.api.cn_ppi(**params)
        except Exception as e:
            raise self.handle_error(e, "get_ppi")
    
    def get_pmi(self, start_date: str = None, end_date: str = None, **kwargs):
        """
        获取 PMI 数据
        
        Tushare API: cn_pmi
        
        Args:
            start_date: 开始月份 (YYYYMM)，会转换为 start_m 参数
            end_date: 结束月份 (YYYYMM)，会转换为 end_m 参数
        
        Returns:
            DataFrame: PMI数据
        """
        try:
            params = kwargs.copy()
            if start_date:
                params["start_m"] = start_date
            if end_date:
                params["end_m"] = end_date
            return self.api.cn_pmi(**params)
        except Exception as e:
            raise self.handle_error(e, "get_pmi")
    
    def get_shibor(self, start_date: str = None, end_date: str = None, **kwargs):
        """
        获取 Shibor 数据
        
        Tushare API: shibor
        
        Args:
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
        
        Returns:
            DataFrame: Shibor数据
        """
        try:
            params = kwargs.copy()
            if start_date:
                params["start_date"] = start_date
            if end_date:
                params["end_date"] = end_date
            return self.api.shibor(**params)
        except Exception as e:
            raise self.handle_error(e, "get_shibor")
    
    def get_lpr(self, start_date: str = None, end_date: str = None, **kwargs):
        """
        获取 LPR 数据
        
        Tushare API: shibor_lpr
        
        Args:
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
        
        Returns:
            DataFrame: LPR数据
        """
        try:
            params = kwargs.copy()
            if start_date:
                params["start_date"] = start_date
            if end_date:
                params["end_date"] = end_date
            return self.api.shibor_lpr(**params)
        except Exception as e:
            raise self.handle_error(e, "get_lpr")
    
    def get_daily_basic(self, ts_code: str, start_date: str = None, end_date: str = None, **kwargs):
        """
        获取日线基本面数据
        
        Tushare API: daily_basic
        
        Args:
            ts_code: 股票代码
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
        
        Returns:
            DataFrame: 日线基本面数据
        """
        try:
            params = {"ts_code": ts_code, **kwargs}
            if start_date:
                params["start_date"] = start_date
            if end_date:
                params["end_date"] = end_date
            return self.api.daily_basic(**params)
        except Exception as e:
            raise self.handle_error(e, "get_daily_basic")
    
    def get_money_supply(self, start_date: str = None, end_date: str = None, **kwargs):
        """
        获取货币供应量数据
        
        Tushare API: cn_m
        
        Args:
            start_date: 开始月份 (YYYYMM)，会转换为 start_m 参数
            end_date: 结束月份 (YYYYMM)，会转换为 end_m 参数
        
        Returns:
            DataFrame: 货币供应量数据
        """
        try:
            params = kwargs.copy()
            if start_date:
                params["start_m"] = start_date
            if end_date:
                params["end_m"] = end_date
            return self.api.cn_m(**params)
        except Exception as e:
            raise self.handle_error(e, "get_money_supply")
    
    def get_trade_cal(self, exchange: str = '', start_date: str = None, end_date: str = None, **kwargs):
        """
        获取交易日历
        
        Tushare API: trade_cal
        
        Args:
            exchange: 交易所代码（空字符串表示所有交易所）
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
        
        Returns:
            DataFrame: 交易日历数据，包含 cal_date 和 is_open 字段
        """
        try:
            params = {"exchange": exchange, **kwargs}
            if start_date:
                params["start_date"] = start_date
            if end_date:
                params["end_date"] = end_date
            return self.api.trade_cal(**params)
        except Exception as e:
            raise self.handle_error(e, "get_trade_cal")
    
    def get_moneyflow_ind_ths(self, start_date: str = None, end_date: str = None, **kwargs):
        """
        获取行业资金流向数据（同花顺）
        
        Tushare API: moneyflow_ind_ths
        
        Args:
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
        
        Returns:
            DataFrame: 行业资金流向数据
        """
        try:
            params = kwargs.copy()
            if start_date:
                params["start_date"] = start_date
            if end_date:
                params["end_date"] = end_date
            return self.api.moneyflow_ind_ths(**params)
        except Exception as e:
            raise self.handle_error(e, "get_moneyflow_ind_ths")
    
    def get_index_daily(self, ts_code: str, start_date: str = None, end_date: str = None, **kwargs):
        """
        获取指数日线数据
        
        Tushare API: index_daily
        
        Args:
            ts_code: 指数代码
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
        
        Returns:
            DataFrame: 指数日线数据
        """
        try:
            params = {"ts_code": ts_code, **kwargs}
            if start_date:
                params["start_date"] = start_date
            if end_date:
                params["end_date"] = end_date
            return self.api.index_daily(**params)
        except Exception as e:
            raise self.handle_error(e, "get_index_daily")
    
    def get_index_weekly(self, ts_code: str, start_date: str = None, end_date: str = None, **kwargs):
        """
        获取指数周线数据
        
        Tushare API: index_weekly
        
        Args:
            ts_code: 指数代码
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
        
        Returns:
            DataFrame: 指数周线数据
        """
        try:
            params = {"ts_code": ts_code, **kwargs}
            if start_date:
                params["start_date"] = start_date
            if end_date:
                params["end_date"] = end_date
            return self.api.index_weekly(**params)
        except Exception as e:
            raise self.handle_error(e, "get_index_weekly")
    
    def get_index_monthly(self, ts_code: str, start_date: str = None, end_date: str = None, **kwargs):
        """
        获取指数月线数据
        
        Tushare API: index_monthly
        
        Args:
            ts_code: 指数代码
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
        
        Returns:
            DataFrame: 指数月线数据
        """
        try:
            params = {"ts_code": ts_code, **kwargs}
            if start_date:
                params["start_date"] = start_date
            if end_date:
                params["end_date"] = end_date
            return self.api.index_monthly(**params)
        except Exception as e:
            raise self.handle_error(e, "get_index_monthly")
    
    def get_index_weight(self, index_code: str, start_date: str = None, end_date: str = None, **kwargs):
        """
        获取指数成分股权重数据
        
        Tushare API: index_weight
        
        Args:
            index_code: 指数代码
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
        
        Returns:
            DataFrame: 指数成分股权重数据
        """
        try:
            params = {"index_code": index_code, **kwargs}
            if start_date:
                params["start_date"] = start_date
            if end_date:
                params["end_date"] = end_date
            return self.api.index_weight(**params)
        except Exception as e:
            raise self.handle_error(e, "get_index_weight")
