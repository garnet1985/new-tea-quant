"""
PMI Handler - 采购经理人指数

从 Tushare 获取 PMI 数据，写入 sys_pmi 表。
"""
from typing import List, Dict, Any
from loguru import logger

from core.modules.data_source.base_class.base_handler import BaseHandler


class PmiHandler(BaseHandler):
    """PMI 数据 Handler，绑定表 sys_pmi。"""

    def on_after_mapping(self, context: Dict[str, Any], mapped_records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """标准化月份格式为 YYYYMM。"""
        if not mapped_records:
            return mapped_records
        formatted = []
        for record in mapped_records:
            date_value = record.get("date")
            if not date_value:
                logger.warning("记录缺少 date 字段，跳过")
                continue
            normalized = self._normalize_month(str(date_value))
            if not normalized:
                logger.warning(f"月份格式异常: {date_value}，跳过")
                continue
            record["date"] = normalized
            record.setdefault("pmi", 0.0)
            record.setdefault("pmi_l_scale", 0.0)
            record.setdefault("pmi_m_scale", 0.0)
            record.setdefault("pmi_s_scale", 0.0)
            formatted.append(record)
        formatted.sort(key=lambda x: x.get("date", ""))
        return formatted

    def _normalize_month(self, month: str) -> str:
        """标准化为 YYYYMM。"""
        if not month:
            return ""
        clean = "".join(c for c in month if c.isdigit())
        if len(clean) == 6:
            return clean
        if len(clean) == 8:
            return clean[:6]
        return ""
