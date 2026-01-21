"""
新浪财经 Provider 实现

纯 API 封装，不包含业务逻辑

注意：
- 新浪财经 API 主要用于获取K线数据
- 直接使用 HTTP 请求，无需认证
- 限流：根据实际使用情况设置
"""
import requests
from typing import Dict, Any, Optional
from loguru import logger

from core.modules.data_source.base_class.base_provider import BaseProvider


class SinaProvider(BaseProvider):
    """
    新浪财经 数据提供者
    
    纯 API 封装，不包含业务逻辑
    
    注意：
    - 新浪财经 API 主要用于获取K线数据
    - 直接使用 HTTP 请求，无需认证
    - 限流：根据实际使用情况设置
    """
    
    provider_name = "sina"
    requires_auth = False
    auth_type = None
    
    # API 限流配置
    api_limits = {
        "get_daily_kline": 60,  # 日K线数据
    }
    
    default_rate_limit = 60
    
    def _initialize(self):
        """初始化新浪财经 Provider（无需认证）"""
        self.base_url = "http://api.finance.sina.com.cn/stock/hs_kline.json"
        self.default_headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        }
        logger.debug("Sina provider initialized (no auth required)")
    
    # ========== API 方法（纯封装）==========
    
    def get_daily_kline(
        self,
        symbol: str,
        datalen: int = None,
        **kwargs
    ):
        """
        获取日K线数据
        
        新浪财经 API: http://api.finance.sina.com.cn/stock/hs_kline.json
        
        Args:
            symbol: 股票代码（新浪格式，如 "sh000001" 上证指数，"sz399001" 深证成指）
            datalen: 返回数据条数限制（可选，默认返回所有数据）
        
        Returns:
            dict: API 返回的 JSON 数据，包含：
                - data: 数组，每个元素为 ["日期", "开盘", "最高", "最低", "收盘", "成交量"]
        
        注意：
        - 此API主要用于获取K线数据
        - 返回的 data 是数组，每个元素是数组格式
        - 日期格式：YYYY-MM-DD
        - 第一个元素是日期，第二个是开盘价，第三个是最高价，第四个是最低价，第五个是收盘价，第六个是成交量
        """
        try:
            params = {
                'symbol': symbol,
                'scale': 'daily',  # 日K线
            }
            
            if datalen is not None:
                params['datalen'] = str(datalen)
            
            response = requests.get(
                self.base_url,
                params=params,
                headers=self.default_headers,
                timeout=10
            )
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            raise self.handle_error(e, "get_daily_kline")
        except Exception as e:
            raise self.handle_error(e, "get_daily_kline")
