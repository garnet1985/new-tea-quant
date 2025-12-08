from app.data_source.base_provider import BaseProvider


class AKShareProvider(BaseProvider):
    """
    AKShare 数据提供者
    
    纯 API 封装，不包含业务逻辑
    """
    
    provider_name = "akshare"
    requires_auth = False
    auth_type = None
    
    # AKShare 没有明确的限流限制，但建议控制频率
    api_limits = {
        "get_stock_list": 60,
        "get_adj_factor": 60,
    }
    
    default_rate_limit = 60
    
    def _initialize(self):
        """初始化 AKShare（无需认证）"""
        pass
    
    # ========== API 方法（纯封装）==========
    
    def get_stock_list(self, **kwargs):
        """获取股票列表"""
        pass
    
    def get_adj_factor(self, symbol: str, **kwargs):
        """获取复权因子"""
        pass

