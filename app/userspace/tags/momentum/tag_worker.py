"""
Momentum TagWorker - 动量因子计算（60天）

计算公式：
MOM = (P_t-60d / P_t-5d) - 1

其中：
- P_t-60d: 过去60个交易日的收盘价
- P_t-5d: 过去5个交易日的收盘价

说明：
- base_term 为 DAILY（日线），用于迭代每个交易日
- 检测月份变化，当月份变化时计算上个月的动量
- 使用日线数据计算动量值
- tag的value包含年月和动量值，格式：YYYYMM:value
"""
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from app.core.modules.tag.core.base_tag_worker import BaseTagWorker
import logging

logger = logging.getLogger(__name__)


class MomentumTagWorker(BaseTagWorker):
    """
    动量因子 TagWorker（60天）
    
    计算过去60个交易日相对于过去5个交易日的动量值
    公式：MOM = (P_t-60d / P_t-5d) - 1
    
    逻辑：
    1. 检查日线数据是否足够60根
    2. 跟踪上次处理的日期，检测月份变化
    3. 当月份变化时，计算上个月的动量（从上个月最后一个交易日前推60个交易日）
    4. tag的value包含年月和动量值
    """
    
    def calculate_tag(
        self,
        entity_id: str,
        entity_type: str,
        as_of_date: str,
        historical_data: Dict[str, Any],
        tag_config: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        计算动量tag
        
        Args:
            entity_id: 实体ID（股票代码）
            entity_type: 实体类型
            as_of_date: 业务日期（YYYYMMDD格式）
            historical_data: 历史数据字典，包含klines等
            tag_config: Tag配置（已合并calculator和tag配置）
            
        Returns:
            Dict[str, Any] 或 None:
                - 如果返回None，不创建tag
                - 如果返回字典，格式：
                    {
                        "value": str,  # 年月和动量值（格式：YYYYMM:value）
                        "start_date": str,  # 可选，起始日期（YYYYMMDD）
                        "end_date": str,  # 可选，结束日期（YYYYMMDD）
                    }
        """
        # 1. 获取日线数据
        klines = historical_data.get("klines", {})
        daily_klines = klines.get("daily", [])
        
        if not daily_klines:
            logger.warning(
                f"缺少日线数据: entity_id={entity_id}, as_of_date={as_of_date}"
            )
            return None
        
        # 2. 检查日线数据是否足够60根
        filtered_daily = [
            k for k in daily_klines
            if k.get("date", "") <= as_of_date
        ]
        
        if len(filtered_daily) < 60:
            logger.debug(
                f"日线数据不足60个交易日: entity_id={entity_id}, as_of_date={as_of_date}, "
                f"available_days={len(filtered_daily)}"
            )
            return None
        
        # 3. 按日期排序（从旧到新）
        filtered_daily.sort(key=lambda x: x.get("date", ""))
        
        # 4. 获取或初始化上次处理的日期（使用tracker缓存）
        tracker_key = f"last_processed_date_{entity_id}"
        last_processed_date = self.tracker.get(tracker_key)
        
        # 如果tracker中没有，从数据库查询（首次处理或tracker未初始化）
        if last_processed_date is None:
            last_processed_date = self._get_last_processed_date(entity_id, tag_config)
            # 存入tracker
            self.tracker[tracker_key] = last_processed_date
        
        # 5. 检查月份是否发生变化
        if not self._is_month_changed(last_processed_date, as_of_date):
            # 月份未变化，更新tracker中的last_processed_date为当前日期
            self.tracker[tracker_key] = as_of_date
            return None
        
        # 6. 月份变化了，计算上个月的动量
        # 6.1 找到上一个月的最后一个交易日（在as_of_date之前）
        last_month_end_date = self._find_last_month_end_trading_day(
            filtered_daily, as_of_date
        )
        
        if not last_month_end_date:
            logger.warning(
                f"无法找到上个月最后一个交易日: entity_id={entity_id}, as_of_date={as_of_date}"
            )
            return None
        
        # 6.2 从上个月最后一个交易日前推60个交易日，计算动量
        momentum = self._calculate_momentum_at_date(
            filtered_daily, last_month_end_date
        )
        
        if momentum is None:
            logger.warning(
                f"计算动量失败: entity_id={entity_id}, last_month_end_date={last_month_end_date}"
            )
            return None
        
        # 7. 获取上个月的年月信息
        last_month_year_month = self._get_year_month(last_month_end_date)
        
        # 8. 更新tracker中的last_processed_date为当前日期
        tracker_key = f"last_processed_date_{entity_id}"
        self.tracker[tracker_key] = as_of_date
        
        # 9. 返回结果（value格式：YYYYMM:动量值）
        return {
            "value": f"{last_month_year_month}:{momentum:.4f}",
            # 不设置start_date和end_date，表示这是一个点状tag
        }
    
    def _get_last_processed_date(
        self, 
        entity_id: str, 
        tag_config: Dict[str, Any]
    ) -> Optional[str]:
        """
        获取上次处理的日期（从数据库查询该entity的最后一个tag的as_of_date）
        
        Args:
            entity_id: 实体ID
            tag_config: Tag配置
            
        Returns:
            Optional[str]: 上次处理的日期（YYYYMMDD格式），如果没有则返回None
        """
        if not self.tag_data_service:
            return None
        
        try:
            # 获取tag_definition_id
            tag_name = tag_config.get("tag_meta", {}).get("name")
            if not tag_name:
                return None
            
            # 获取scenario和tag definition
            scenario = self.tag_data_service.get_scenario(
                self.scenario_name, 
                self.scenario_version
            )
            if not scenario:
                return None
            
            tag_defs = self.tag_data_service.list_tag_definitions(
                scenario_id=scenario["id"]
            )
            
            tag_def = None
            for td in tag_defs:
                if td.get("name") == tag_name:
                    tag_def = td
                    break
            
            if not tag_def:
                return None
            
            # 查询该entity的最后一个tag的as_of_date
            from app.core.modules.data_manager.base_tables.tag_value.model import TagValueModel
            tag_value_model = TagValueModel()
            
            # 查询该entity和tag_definition的最大as_of_date
            sql = """
                SELECT MAX(as_of_date) as max_date 
                FROM tag_value 
                WHERE entity_id = %s AND tag_definition_id = %s
            """
            
            result = tag_value_model.db.execute_sync_query(
                sql, 
                (entity_id, tag_def["id"])
            )
            
            if result and result[0].get("max_date"):
                max_date = result[0]["max_date"]
                # 转换为YYYYMMDD格式
                if isinstance(max_date, str):
                    return max_date.replace("-", "")
                elif hasattr(max_date, "strftime"):
                    return max_date.strftime("%Y%m%d")
                else:
                    return str(max_date).replace("-", "")
            
            return None
            
        except Exception as e:
            logger.warning(
                f"获取上次处理日期失败: entity_id={entity_id}, error={e}"
            )
            return None
    
    def _is_month_changed(
        self, 
        last_date: Optional[str], 
        current_date: str
    ) -> bool:
        """
        检查月份是否发生变化
        
        Args:
            last_date: 上次处理的日期（YYYYMMDD格式），如果为None表示首次处理
            current_date: 当前日期（YYYYMMDD格式）
            
        Returns:
            bool: 如果月份发生变化返回True，否则返回False
        """
        if last_date is None:
            # 首次处理，检查当前日期是否有足够数据
            return True
        
        try:
            last_dt = datetime.strptime(last_date, '%Y%m%d')
            current_dt = datetime.strptime(current_date, '%Y%m%d')
            
            # 检查年月是否不同
            return (last_dt.year != current_dt.year) or (last_dt.month != current_dt.month)
            
        except Exception as e:
            logger.error(f"判断月份变化时出错: last_date={last_date}, current_date={current_date}, error={e}")
            return False
    
    def _find_last_month_end_trading_day(
        self, 
        daily_klines: list, 
        as_of_date: str
    ) -> Optional[str]:
        """
        找到上一个月的最后一个交易日（在as_of_date之前）
        
        Args:
            daily_klines: 日线数据列表（已排序，从旧到新）
            as_of_date: 当前日期（YYYYMMDD格式）
            
        Returns:
            Optional[str]: 上个月最后一个交易日的日期（YYYYMMDD格式），如果找不到返回None
        """
        try:
            current_dt = datetime.strptime(as_of_date, '%Y%m%d')
            current_year = current_dt.year
            current_month = current_dt.month
            
            # 计算上个月的年月
            if current_month == 1:
                last_month_year = current_year - 1
                last_month = 12
            else:
                last_month_year = current_year
                last_month = current_month - 1
            
            # 在日线数据中查找上个月最后一个交易日
            # 遍历日线数据（从新到旧），找到上个月最后一个交易日
            last_month_end_date = None
            for kline in reversed(daily_klines):
                date_str = kline.get("date", "")
                if not date_str:
                    continue
                
                try:
                    kline_dt = datetime.strptime(date_str, '%Y%m%d')
                    kline_year = kline_dt.year
                    kline_month = kline_dt.month
                    
                    # 如果找到上个月的交易日
                    if kline_year == last_month_year and kline_month == last_month:
                        last_month_end_date = date_str
                        break
                    # 如果已经过了上个月，停止查找
                    elif (kline_year < last_month_year) or \
                         (kline_year == last_month_year and kline_month < last_month):
                        break
                        
                except Exception:
                    continue
            
            return last_month_end_date
            
        except Exception as e:
            logger.error(f"查找上个月最后一个交易日时出错: as_of_date={as_of_date}, error={e}")
            return None
    
    def _calculate_momentum_at_date(
        self, 
        daily_klines: list, 
        reference_date: str
    ) -> Optional[float]:
        """
        在指定日期计算动量值
        
        从reference_date前推60个交易日，计算：
        MOM = (P_t-60d / P_t-5d) - 1
        
        Args:
            daily_klines: 日线数据列表（已排序，从旧到新）
            reference_date: 参考日期（YYYYMMDD格式），从这个日期前推
            
        Returns:
            Optional[float]: 动量值，如果计算失败返回None
        """
        # 找到reference_date在daily_klines中的位置
        ref_index = None
        for i, kline in enumerate(daily_klines):
            if kline.get("date", "") == reference_date:
                ref_index = i
                break
        
        if ref_index is None:
            logger.warning(f"无法找到参考日期在日线数据中的位置: reference_date={reference_date}")
            return None
        
        # 检查是否有足够的数据（需要至少60个交易日）
        if ref_index < 59:
            logger.warning(
                f"参考日期之前的数据不足60个交易日: reference_date={reference_date}, "
                f"available_days={ref_index + 1}"
            )
            return None
        
        # 获取P_t-60d和P_t-5d的收盘价
        # ref_index是reference_date的位置，所以：
        # - P_t-60d: ref_index - 59（倒数第60个）
        # - P_t-5d: ref_index - 4（倒数第5个）
        price_t_60d = daily_klines[ref_index - 59].get("close")
        price_t_5d = daily_klines[ref_index - 4].get("close")
        
        if price_t_60d is None or price_t_5d is None:
            logger.warning(
                f"日线数据缺少收盘价: reference_date={reference_date}, "
                f"price_t_60d={price_t_60d}, price_t_5d={price_t_5d}"
            )
            return None
        
        # 转换为浮点数
        try:
            price_t_60d = float(price_t_60d)
            price_t_5d = float(price_t_5d)
        except (ValueError, TypeError) as e:
            logger.warning(
                f"日线收盘价格式错误: reference_date={reference_date}, "
                f"price_t_60d={price_t_60d}, price_t_5d={price_t_5d}, error={e}"
            )
            return None
        
        # 计算动量值：MOM = (P_t-60d / P_t-5d) - 1
        if price_t_5d == 0:
            logger.warning(
                f"过去5个交易日收盘价为0: reference_date={reference_date}"
            )
            return None
        
        momentum = (price_t_60d / price_t_5d) - 1
        return momentum
    
    def _get_year_month(self, date_str: str) -> str:
        """
        获取日期的年月（YYYYMM格式）
        
        Args:
            date_str: 日期字符串（YYYYMMDD格式）
            
        Returns:
            str: 年月字符串（YYYYMM格式）
        """
        try:
            date = datetime.strptime(date_str, '%Y%m%d')
            return date.strftime('%Y%m')
        except Exception as e:
            logger.error(f"获取年月时出错: date_str={date_str}, error={e}")
            return date_str[:6]  # 如果解析失败，返回前6位
