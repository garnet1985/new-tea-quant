"""
东方财富 Provider 实现

纯 API 封装，不包含业务逻辑

注意：
- 东方财富 API 主要用于获取前复权K线数据，用于计算复权因子
- 直接使用 HTTP 请求，无需认证
- 限流：60次/分钟
- 东方财富通过 TLS 指纹识别脚本，requests 易被拒绝；优先使用 curl_cffi 模拟 Chrome
"""
import time
from typing import Dict, Any, Optional
from loguru import logger

from core.modules.data_source.base_class.base_provider import BaseProvider

# 优先使用 curl_cffi（模拟 Chrome TLS 指纹），否则回退到 requests
try:
    from curl_cffi import requests as curl_requests
    _HAS_CURL_CFFI = True
except ImportError:
    curl_requests = None
    _HAS_CURL_CFFI = False

import requests  # 始终导入，用于 fallback 及异常类型


class EastMoneyProvider(BaseProvider):
    """
    东方财富 数据提供者
    
    纯 API 封装，不包含业务逻辑
    
    注意：
    - 东方财富 API 主要用于获取前复权K线数据，用于计算复权因子
    - 直接使用 HTTP 请求，无需认证
    - 限流：60次/分钟
    """
    
    provider_name = "eastmoney"
    requires_auth = False
    auth_type = None
    
    # API 限流：30次/分钟（东方财富反爬趋严，保守限流）
    api_limits = {
        "get_qfq_kline": 30,
    }
    
    default_rate_limit = 30
    
    def _initialize(self):
        """初始化东方财富 Provider（无需认证）"""
        self.base_url = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
        self._quote_url = "https://quote.eastmoney.com/sz000001.html"
        self.default_headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Referer': 'https://quote.eastmoney.com/',
            'Origin': 'https://quote.eastmoney.com',
        }
    
    def _warmup_session(self):
        """首次请求前先访问行情页获取 cookies，模拟浏览器行为"""
        if not _HAS_CURL_CFFI:
            return None
        if getattr(self, '_session_warmed', False):
            return getattr(self, '_curl_session', None)
        try:
            # 使用 chrome 最新指纹，部分环境 chrome110 可能被识别
            session = curl_requests.Session(impersonate="chrome")
            session.get(self._quote_url, timeout=15)
            time.sleep(1.5)  # 模拟用户停留，降低被识别为脚本的概率
            self._curl_session = session
            self._session_warmed = True
            return session
        except Exception as e:
            logger.debug(f"[EastMoney] 行情页预热失败，将直接请求 API: {e}")
            return None
    
    # ========== API 方法（纯封装）==========
    
    def get_qfq_kline(
        self,
        secid: str,
        end_date: str = "20300101",
        start_date: str = None,
        limit: int = None,
        **kwargs
    ):
        """
        获取前复权K线数据（用于计算复权因子）
        
        东方财富 API: push2his.eastmoney.com/api/qt/stock/kline/get
        
        Args:
            secid: 股票代码（东方财富格式，如 "0.000001" 深市，"1.600000" 沪市）
            end_date: 结束日期（YYYYMMDD格式，如 "20241231"，默认 "20300101" 表示获取到最新）
            start_date: 起始日期（YYYYMMDD格式，可选，如果提供则只返回该日期之后的数据）
            limit: 返回数据条数限制（可选，与 start_date 互斥：有 start_date 时不应提供 limit）
        
        Returns:
            dict: API 返回的 JSON 数据，包含：
                - data.klines: 字符串数组，每个元素格式为 "日期,收盘价,..."
                - data.fields2: 字段说明
        
        注意：
        - 此API主要用于计算复权因子
        - 返回的 klines 是字符串数组，需要解析
        - 日期格式：YYYY-MM-DD
        - 收盘价在第二个字段（索引1）
        - start_date 和 limit 互斥：有 start_date 时使用 beg 参数，有 limit 时使用 lmt 参数
        """
        # 构建请求参数
        params = {
            'secid': secid,
            'ut': 'fa5fd1943c7b386f172d6893dbfba10b',
            'fields1': 'f1,f2,f3,f4,f5,f6',
            'fields2': 'f51,f53',  # f51=日期, f53=收盘价
            'klt': '101',  # 日线
            'fqt': '1',  # 前复权
            'end': end_date,
        }
        
        # 处理 start_date 和 limit 的互斥逻辑
        # 有 start_date 时使用 beg 参数，不设置 lmt
        # 有 limit 时使用 lmt 参数，不设置 beg
        if start_date:
            params['beg'] = start_date
            # 不设置 lmt，让 API 返回从 start_date 到 end_date 的所有数据
        elif limit is not None:
            params['lmt'] = str(limit)
        else:
            # 如果都没有提供，使用默认 limit
            params['lmt'] = '5000'
        
        # 构建完整的 URL（用于调试）
        from urllib.parse import urlencode
        full_url = f"{self.base_url}?{urlencode(params)}"
        
        # 重试机制：最多重试 5 次，指数退避（2s, 4s, 8s, 16s）
        max_retries = 5
        base_delay = 2.0  # 秒
        timeout = 30
        
        last_error = None
        for attempt in range(max_retries):
            try:
                if _HAS_CURL_CFFI:
                    session = self._warmup_session()
                    if session:
                        response = session.get(
                            self.base_url,
                            params=params,
                            headers=self.default_headers,
                            timeout=timeout,
                        )
                    else:
                        response = curl_requests.get(
                            self.base_url,
                            params=params,
                            headers=self.default_headers,
                            timeout=timeout,
                            impersonate="chrome",
                        )
                else:
                    response = requests.get(
                        self.base_url,
                        params=params,
                        headers=self.default_headers,
                        timeout=timeout,
                    )
                response.raise_for_status()
                return response.json()
                
            except Exception as e:
                # 连接类异常可重试；其他异常直接抛出
                last_error = e
                err_name = type(e).__name__
                err_str = str(e).lower()
                is_retryable = (
                    "Connection" in err_name or "connection" in err_str or
                    "CurlError" in err_name or "RemoteDisconnected" in err_str or
                    "aborted" in err_str or "closed" in err_str
                )
                if not is_retryable:
                    logger.error(f"❌ [EastMoney API] 请求失败，URL: {full_url}")
                    logger.error(f"   错误详情: {e}")
                    raise self.handle_error(e, "get_qfq_kline")
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    logger.warning(
                        f"⚠️ [EastMoney API] 请求失败（尝试 {attempt + 1}/{max_retries}），"
                        f"{delay:.0f} 秒后重试: {e}"
                    )
                    time.sleep(delay)
                    continue
                break
        
        logger.error(f"❌ [EastMoney API] 请求失败（已重试 {max_retries} 次），URL: {full_url}")
        logger.error(f"   错误详情: {last_error}")
        raise self.handle_error(last_error or RuntimeError("未知错误"), "get_qfq_kline")

