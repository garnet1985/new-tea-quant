"""
AKShare Provider 实现

纯 API 封装，不包含业务逻辑

注意：
- AKShare 主要用于获取前复权K线数据，用于计算复权因子
- 只使用一个API：stock_zh_a_hist（获取前复权K线数据）
"""
import akshare as ak
from typing import Dict, Any, Optional
from loguru import logger

from core.modules.data_source.base_provider import BaseProvider


class AKShareProvider(BaseProvider):
    """
    AKShare 数据提供者
    
    纯 API 封装，不包含业务逻辑
    
    注意：
    - AKShare 主要用于获取前复权K线数据，用于计算复权因子
    - 只使用 stock_zh_a_hist API
    """
    
    provider_name = "akshare"
    requires_auth = False
    auth_type = None
    
    # API 限流：80次/分钟（buffer 10，实际70次/分钟）
    api_limits = {
        "get_qfq_kline": 80,  # 前复权K线数据（用于计算复权因子）
    }
    
    default_rate_limit = 80
    
    def _initialize(self):
        """初始化 AKShare（无需认证）"""
        logger.debug("AKShare provider initialized (no auth required)")
    
    # ========== API 方法（纯封装）==========
    
    def get_qfq_kline(
        self, 
        symbol: str, 
        period: str = "daily",
        start_date: str = None, 
        end_date: str = None,
        adjust: str = "qfq",
        **kwargs
    ):
        """
        获取前复权K线数据（用于计算复权因子）
        
        AKShare API: stock_zh_a_hist
        
        Args:
            symbol: 股票代码（如 "000001"，不带市场后缀）
            period: 周期（"daily"/"weekly"/"monthly"，默认 "daily"）
            start_date: 开始日期（YYYYMMDD格式，如 "20200101"）
            end_date: 结束日期（YYYYMMDD格式，如 "20241231"）
            adjust: 复权类型（"qfq"前复权/"hfq"后复权/"bfq"不复权，默认 "qfq"）
        
        Returns:
            DataFrame: 前复权K线数据，包含列：
                - 日期
                - 开盘、收盘、最高、最低
                - 成交量、成交额
                - 涨跌幅、涨跌额
                - 换手率
        
        注意：
        - 此API主要用于计算复权因子
        - 通过比较前复权价格和原始价格来计算复权因子
        """
        try:
            return ak.stock_zh_a_hist(
                symbol=symbol,
                period=period,
                start_date=start_date,
                end_date=end_date,
                adjust=adjust
            )
        except Exception as e:
            raise self.handle_error(e, "get_qfq_kline")
