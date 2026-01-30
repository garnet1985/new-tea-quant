"""
东方财富 Provider 实现

纯 API 封装，不包含业务逻辑

注意：
- 东方财富 API 主要用于获取前复权K线数据，用于计算复权因子
- 直接使用 HTTP 请求，无需认证
- 限流：60次/分钟
"""
import requests
from typing import Dict, Any, Optional
from loguru import logger

from core.modules.data_source.base_class.base_provider import BaseProvider


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
    
    # API 限流：60次/分钟
    api_limits = {
        "get_qfq_kline": 60,  # 前复权K线数据（用于计算复权因子）
    }
    
    default_rate_limit = 60
    
    def _initialize(self):
        """初始化东方财富 Provider（无需认证）"""
        self.base_url = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
        self.default_headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Referer': 'https://quote.eastmoney.com/',
        }
    
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
        try:
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
            
            response = requests.get(
                self.base_url,
                params=params,
                headers=self.default_headers,
                timeout=10
            )
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            raise self.handle_error(e, "get_qfq_kline")
        except Exception as e:
            raise self.handle_error(e, "get_qfq_kline")

