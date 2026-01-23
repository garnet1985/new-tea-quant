"""
价格指数 Handler - 合并 CPI、PPI、PMI、货币供应量数据

从 Tushare 获取 CPI、PPI、PMI、货币供应量数据，合并到 price_indexes 表中。

业务逻辑：
1. 调用四个 API：get_cpi, get_ppi, get_pmi, get_money_supply
2. 按月份合并数据（通过配置 merge_by_key: "date" 实现）
3. 保存到 price_indexes 表
"""
from typing import List, Dict, Any
from loguru import logger

from core.modules.data_source.base_class.base_handler import BaseHandler


class PriceIndexesHandler(BaseHandler):
    """
    价格指数 Handler - 合并 CPI、PPI、PMI、货币供应量数据
    
    特点：
    - 需要多个 API 调用（Tushare get_cpi + get_ppi + get_pmi + get_money_supply）
    - 增量更新（incremental）
    - 按月份合并数据（通过配置 merge_by_key: "date" 实现）
    - 滚动刷新机制：每次运行都刷新最近 N 个月的数据（确保数据一致性）
    
    配置（在 config.json 中）：
    - renew_mode: "rolling"
    - date_format: "month"
    - rolling_unit: "month", rolling_length: 12
    - merge_by_key: "date"  # 按 date 字段合并多个 API 的结果
    - apis: {...} (包含 4 个 API 配置：cpi_data, ppi_data, pmi_data, money_supply_data)
    """
    
    def on_after_mapping(self, context: Dict[str, Any], mapped_records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        字段映射后的钩子：标准化月份格式并设置默认值
        
        Args:
            context: 执行上下文
            mapped_records: 已应用 field_mapping 的记录列表
            
        Returns:
            List[Dict[str, Any]]: 处理后的记录列表
        """
        if not mapped_records:
            return mapped_records
        
        formatted = []
        for record in mapped_records:
            # 标准化月份格式（date 字段）
            date_value = record.get('date')
            if date_value:
                normalized_date = self._normalize_month(str(date_value))
                if normalized_date:
                    record['date'] = normalized_date
                else:
                    # 如果月份格式无法解析，跳过该记录
                    logger.warning(f"月份格式异常: {date_value}，跳过该记录")
                    continue
            else:
                # 如果缺少 date 字段，跳过该记录
                logger.warning("记录缺少 date 字段，跳过该记录")
                continue
            
            # 设置默认值（确保所有必需字段都有值）
            record.setdefault('cpi', 0.0)
            record.setdefault('cpi_yoy', 0.0)
            record.setdefault('cpi_mom', 0.0)
            record.setdefault('ppi', 0.0)
            record.setdefault('ppi_yoy', 0.0)
            record.setdefault('ppi_mom', 0.0)
            record.setdefault('pmi', 0.0)
            record.setdefault('pmi_l_scale', 0.0)
            record.setdefault('pmi_m_scale', 0.0)
            record.setdefault('pmi_s_scale', 0.0)
            record.setdefault('m0', 0.0)
            record.setdefault('m0_yoy', 0.0)
            record.setdefault('m0_mom', 0.0)
            record.setdefault('m1', 0.0)
            record.setdefault('m1_yoy', 0.0)
            record.setdefault('m1_mom', 0.0)
            record.setdefault('m2', 0.0)
            record.setdefault('m2_yoy', 0.0)
            record.setdefault('m2_mom', 0.0)
            
            formatted.append(record)
        
        # 按日期排序
        formatted.sort(key=lambda x: x.get('date', ''))
        
        logger.info(f"✅ 价格指数数据处理完成，共 {len(formatted)} 条记录（合并 CPI/PPI/PMI/货币供应量）")
        
        return formatted
    
    def _normalize_month(self, month: str) -> str:
        """
        标准化月份格式为 YYYYMM
        
        Args:
            month: 月份字符串，可能是 YYYYMM、YYYY-MM、YYYYMMDD 等格式
        
        Returns:
            str: YYYYMM 格式的月份字符串，如果无法解析返回空字符串
        """
        if not month:
            return ""
        
        # 移除所有非数字字符
        month_clean = ''.join(c for c in month if c.isdigit())
        
        if len(month_clean) == 6:
            # YYYYMM 格式
            return month_clean
        elif len(month_clean) == 8:
            # YYYYMMDD 格式，取前 6 位
            return month_clean[:6]
        elif len(month_clean) == 4:
            # YYYY 格式，需要补充月份（这种情况不应该出现，但为了容错）
            logger.warning(f"月份格式异常: {month}，无法解析")
            return ""
        else:
            logger.warning(f"月份格式异常: {month}，无法解析")
            return ""
    
    def on_after_normalize(self, context: Dict[str, Any], normalized_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        标准化后处理：数据清洗（NaN 清理），不负责保存。
        
        注意：data source 不负责 save，save 由上层（data_manager/service）自己处理。
        """
        # 可选：清洗 NaN 值
        return self.clean_nan_in_normalized_data(normalized_data, default=0.0)
