"""
AKShare Provider 实现

纯 API 封装，不包含业务逻辑

注意：
- 使用 stock_zh_a_hist_tx（腾讯财经），限流较宽松
- akshare 的 get_tx_start_year 在 qfq fallback 时误用 ["day"]，实际应为 ["qfqday"]，
  模块加载时 monkey-patch 修复
"""
import akshare as ak
from typing import Dict, Any, Optional

from core.modules.data_source.base_class.base_provider import BaseProvider


def _patch_akshare_get_tx_start_year():
    """修复 akshare get_tx_start_year 在 qfq fallback 时 KeyError 'day' 的 bug。
    需 patch stock_hist_tx 模块（它 from import 了 get_tx_start_year，改源模块无效）。
    """
    try:
        import requests
        from akshare.utils import demjson

        def _patched(symbol: str = "sh000919") -> str:
            url = "https://web.ifzq.gtimg.cn/other/klineweb/klineWeb/weekTrends"
            params = {"code": symbol, "type": "qfq", "_var": "trend_qfq", "r": "0.3506048543943414"}
            r = requests.get(url, params=params)
            data_text = r.text
            if not demjson.decode(data_text[data_text.find("={") + 1:])["data"]:
                url = "https://proxy.finance.qq.com/ifzqgtimg/appstock/app/newfqkline/get"
                params = {"_var": "kline_dayqfq", "param": f"{symbol},day,,,320,qfq", "r": "0.751892490072597"}
                r = requests.get(url, params=params)
                data_text = r.text
                data = demjson.decode(data_text[data_text.find("={") + 1:])["data"][symbol]
                day_key = "day" if "day" in data else "qfqday"
                return data[day_key][0][0]
            return demjson.decode(data_text[data_text.find("={") + 1:])["data"][0][0]

        import akshare.stock_feature.stock_hist_tx as hist_tx
        hist_tx.get_tx_start_year = _patched
    except Exception:
        pass


_patch_akshare_get_tx_start_year()


class AKShareProvider(BaseProvider):
    """
    AKShare 数据提供者

    使用 stock_zh_a_hist_tx（腾讯财经），限流较东财宽松
    """

    provider_name = "akshare"
    requires_auth = False
    auth_type = None

    api_limits = {
        "get_qfq_kline": 80,
    }

    default_rate_limit = 80

    def _initialize(self):
        """初始化（无需认证）"""
        pass

    def get_qfq_kline(
        self,
        symbol: str,
        start_date: str = None,
        end_date: str = None,
        adjust: str = "qfq",
        **kwargs
    ):
        """
        获取前复权K线数据

        AKShare API: stock_zh_a_hist_tx（腾讯财经，限流较宽松）
        """
        try:
            return ak.stock_zh_a_hist_tx(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                adjust=adjust,
            )
        except Exception as e:
            raise self.handle_error(e, "get_qfq_kline")
