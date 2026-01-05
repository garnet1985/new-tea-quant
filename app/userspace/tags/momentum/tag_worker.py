"""
Momentum TagWorker - 动量因子计算（60天）

计算公式：
MOM = (P_t-60d / P_t-5d) - 1

其中：
- P_t-60d: 前60根K线中，前55根（除去最近5根）的平均收盘价
- P_t-5d: 前60根K线中，最近5根的平均收盘价
- 必须要有60根K线才能计算，不足60根时跳过当次计算
"""
from typing import Dict, Any, Optional, List
from datetime import datetime
from app.core.modules.tag.core.base_tag_worker import BaseTagWorker
import logging

logger = logging.getLogger(__name__)


class MomentumTagWorker(BaseTagWorker):
    """
    动量因子 TagWorker（60天）
    
    计算过去60个交易日相对于过去5个交易日的动量值
    公式：MOM = (P_t-60d / P_t-5d) - 1
    
    其中：
    - P_t-60d: 当前时间点往前数60根K线，取前55根（除去最近5根）的平均收盘价
    - P_t-5d: 当前时间点往前数60根K线，取最近5根的平均收盘价
    - 必须要有60根K线才能计算，不足60根时跳过当次计算
    
    逻辑：
    1. 使用self.tracker记录时间点
    2. 检测月份变化
    3. 当月份变化时，在当天（as_of_date）往前数K线计算动量
    4. 必须要有60根K线才能计算，不足60根时跳过当次计算
    5. tag的value包含年月和动量值
    """
    
    def on_before_execute_tagging(self):
        """初始化 last_processed_date（使用 None，让月份变化检测从 start_date 开始）"""
        # 在 INCREMENTAL 模式下，框架已经确保 start_date 是正确的起始日期
        # 使用 None 让 _is_month_changed 在第一个交易日返回 True（视为首次处理）
        # 这样可以避免使用不准确的"前一天"（可能不是交易日）
        last_processed_date = None
        
        # 为所有 tag_definitions 初始化相同的 last_processed_date
        entity_id = self.entity['id']
        for tag_definition in self.tag_definitions:
            self.tracker[self._get_tracker_key(entity_id, tag_definition.id)] = last_processed_date
    
    def calculate_tag(
        self,
        as_of_date: str,
        historical_data: Dict[str, Any],
        tag_definition: Any
    ) -> Optional[Dict[str, Any]]:
        """计算动量tag（仅在月份变化时计算）"""
        entity_id = self.entity['id']
        daily_klines = historical_data.get("klines", {}).get("daily", [])
        
        if not daily_klines:
            return None
        
        # 过滤并检查数据量
        filtered_daily = [k for k in daily_klines if k.get("date", "") <= as_of_date]
        if len(filtered_daily) < 60:
            return None
        
        # 检查月份变化
        tracker_key = self._get_tracker_key(entity_id, tag_definition.id)
        last_processed_date = self.tracker.get(tracker_key)
        
        if not self._is_month_changed(last_processed_date, as_of_date):
            self.tracker[tracker_key] = as_of_date
            return None
        
        # 月份变化，计算动量
        last_month_end_date = self._find_last_month_end_trading_day(filtered_daily, as_of_date)
        if not last_month_end_date:
            return None
        
        momentum = self._calculate_momentum_at_date(filtered_daily, as_of_date)
        if momentum is None:
            return None
        
        self.tracker[tracker_key] = as_of_date
        return {
            "value": {
                "year_month": self._get_year_month(last_month_end_date),
                "momentum": momentum
            }
        }
    
    def _get_tracker_key(self, entity_id: str, tag_definition_id: int) -> str:
        """获取 tracker key"""
        return f"last_processed_date_{entity_id}_{tag_definition_id}"
    
    def _is_month_changed(self, last_date: Optional[str], current_date: str) -> bool:
        """检查月份是否发生变化（None 视为首次处理，返回 True）"""
        if last_date is None:
            return True
        
        try:
            last_dt = datetime.strptime(last_date, '%Y%m%d')
            current_dt = datetime.strptime(current_date, '%Y%m%d')
            return (last_dt.year, last_dt.month) != (current_dt.year, current_dt.month)
        except Exception:
            return False
    
    def _find_last_month_end_trading_day(self, daily_klines: list, as_of_date: str) -> Optional[str]:
        """找到上一个月的最后一个交易日"""
        try:
            current_dt = datetime.strptime(as_of_date, '%Y%m%d')
            # 计算上个月的年月
            if current_dt.month == 1:
                last_month_year, last_month = current_dt.year - 1, 12
            else:
                last_month_year, last_month = current_dt.year, current_dt.month - 1
            
            # 从新到旧查找上个月最后一个交易日
            for kline in reversed(daily_klines):
                date_str = kline.get("date")
                if not date_str:
                    continue
                
                try:
                    kline_dt = datetime.strptime(date_str, '%Y%m%d')
                    if (kline_dt.year, kline_dt.month) == (last_month_year, last_month):
                        return date_str
                    elif (kline_dt.year, kline_dt.month) < (last_month_year, last_month):
                        break
                except Exception:
                    continue
            
            return None
        except Exception:
            return None
    
    def _calculate_momentum_at_date(self, filtered_daily: list, reference_date: str) -> Optional[float]:
        """计算动量值：MOM = (P_t-60d / P_t-5d) - 1（需要60根K线）"""
        # 找到参考日期位置
        try:
            ref_index = next(i for i, k in enumerate(filtered_daily) if k.get("date") == reference_date)
        except StopIteration:
            return None
        
        if ref_index + 1 < 60:  # 需要60根K线
            return None
        
        # 提取最后60根K线
        klines_slice = filtered_daily[ref_index - 59:ref_index + 1]
        if len(klines_slice) != 60:
            return None
        
        # 提取收盘价（前55根和最近5根）
        early_prices = self._extract_prices(klines_slice, 0, 55)
        recent_prices = self._extract_prices(klines_slice, 55, 60)
        
        if not early_prices or not recent_prices:
            return None
        
        # 计算平均价格和动量
        price_t_60d = sum(early_prices) / len(early_prices)
        price_t_5d = sum(recent_prices) / len(recent_prices)
        
        if price_t_5d == 0:
            return None
        
        return (price_t_60d / price_t_5d) - 1
    
    def _extract_prices(self, klines: List[Dict], start: int, end: int) -> List[float]:
        """提取K线收盘价列表"""
        prices = []
        for i in range(start, end):
            try:
                close_price = klines[i].get("close")
                if close_price is None:
                    return []
                prices.append(float(close_price))
            except (ValueError, TypeError):
                return []
        return prices
    
    def _get_year_month(self, date_str: str) -> str:
        """获取日期的年月（YYYYMM格式）"""
        try:
            return datetime.strptime(date_str, '%Y%m%d').strftime('%Y%m')
        except Exception:
            return date_str[:6]  # 解析失败，返回前6位
