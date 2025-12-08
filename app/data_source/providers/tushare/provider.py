from app.data_source.base_provider import BaseProvider


class TushareProvider(BaseProvider):
    """
    Tushare 数据提供者
    
    纯 API 封装，不包含业务逻辑
    """
    
    provider_name = "tushare"
    requires_auth = True
    auth_type = "token"
    
    # 声明每个 API 的限流（每分钟请求数）
    api_limits = {
        "get_stock_list": 100,
        "get_daily_kline": 100,
        "get_weekly_kline": 50,
        "get_monthly_kline": 30,
        "get_adj_factor": 80,
        "get_finance_data": 60,
        "get_gdp": 100,
        "get_cpi": 100,
        "get_ppi": 100,
        "get_pmi": 100,
        "get_shibor": 100,
        "get_lpr": 100,
        "get_money_supply": 100,
    }
    
    default_rate_limit = 100
    
    def _initialize(self):
        """初始化 Tushare API 客户端"""
        pass
    
    # ========== API 方法（纯封装）==========
    
    def get_stock_list(self, **kwargs):
        """获取股票列表"""
        pass
    
    def get_daily_kline(self, ts_code: str, start_date: str, end_date: str, **kwargs):
        """获取日线数据"""
        pass
    
    def get_weekly_kline(self, ts_code: str, start_date: str, end_date: str, **kwargs):
        """获取周线数据"""
        pass
    
    def get_monthly_kline(self, ts_code: str, start_date: str, end_date: str, **kwargs):
        """获取月线数据"""
        pass
    
    def get_adj_factor(self, ts_code: str, start_date: str, end_date: str, **kwargs):
        """获取复权因子"""
        pass
    
    def get_finance_data(self, ts_code: str, period: str, **kwargs):
        """获取财务数据"""
        pass
    
    def get_gdp(self, start_date: str, end_date: str, **kwargs):
        """获取 GDP 数据"""
        pass
    
    def get_cpi(self, start_date: str, end_date: str, **kwargs):
        """获取 CPI 数据"""
        pass
    
    def get_ppi(self, start_date: str, end_date: str, **kwargs):
        """获取 PPI 数据"""
        pass
    
    def get_pmi(self, start_date: str, end_date: str, **kwargs):
        """获取 PMI 数据"""
        pass
    
    def get_shibor(self, start_date: str, end_date: str, **kwargs):
        """获取 Shibor 数据"""
        pass
    
    def get_lpr(self, start_date: str, end_date: str, **kwargs):
        """获取 LPR 数据"""
        pass
    
    def get_money_supply(self, start_date: str, end_date: str, **kwargs):
        """获取货币供应量数据"""
        pass

