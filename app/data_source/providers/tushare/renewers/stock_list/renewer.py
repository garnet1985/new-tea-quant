"""
股票列表更新器（替代 stock_index，排除北交所）
"""
from typing import Dict, List, Any
from loguru import logger
from ...base_renewer import BaseRenewer


class StockListRenewer(BaseRenewer):
    """股票列表更新器"""

    def build_jobs(self, start_date: str, end_date: str) -> List[Dict]:
        return []

    def renew(self, latest_market_open_day: str = None):
        logger.info("🔄 开始更新股票列表（排除北交所）")
        try:
            api_data = self._fetch_api_data()
            if not api_data:
                logger.warning("⚠️ API返回空数据")
                return False

            formatted = self._format_data(api_data)
            if not formatted:
                logger.warning("⚠️ 格式化后无数据")
                return False

            # 排除北交所（.BJ）
            formatted = [r for r in formatted if not str(r.get('id', '')).endswith('.BJ')]

            table = self.db.get_table_instance('stock_list')
            if hasattr(table, 'renew_list'):
                table.renew_list(formatted)
                logger.info(f"✅ 股票列表更新完成，处理了 {len(formatted)} 只股票（已排除BJ）")
                return len(formatted)
            else:
                logger.error("❌ stock_list 表缺少 renew_list 方法")
                return False
        except Exception as e:
            logger.error(f"❌ 股票列表更新失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")
            return False

    def _fetch_api_data(self) -> List[Dict]:
        try:
            api_config = self.config['apis'][0]
            api_method = getattr(self.api, api_config['method'])
            result = api_method(**api_config['params'])
            if result is None or (hasattr(result, 'empty') and result.empty):
                return []
            return result.to_dict('records') if hasattr(result, 'to_dict') else list(result)
        except Exception as e:
            logger.error(f"❌ 获取API数据失败: {e}")
            return []

    def _format_data(self, api_data: List[Dict]) -> List[Dict]:
        formatted: List[Dict[str, Any]] = []
        mapping = self.config['apis'][0]['mapping']
        for item in api_data:
            mapped = {}
            for db_field, src in mapping.items():
                if callable(src):
                    mapped[db_field] = src(item)
                else:
                    mapped[db_field] = item.get(src)
            if mapped.get('id') and mapped.get('name'):
                formatted.append(mapped)
        return formatted


