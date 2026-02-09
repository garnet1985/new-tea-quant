"""
Renew Common Helper

提供所有 renew service 共用的工具方法（静态方法）。
"""
from typing import Dict, Any, Tuple, Optional
from loguru import logger

from core.global_enums.enums import TermType
from core.utils.date.date_utils import DateUtils
from core.infra.project_context import ConfigManager


class RenewCommonHelper:
    """
    Renew 公共辅助类
    
    提供所有 renew service 共用的静态方法。
    """
    
    @staticmethod
    def get_default_date_range(data_manager, date_format: str, context: Dict[str, Any] = None) -> Tuple[str, str]:
        """
        获取默认日期范围（数据库为空时使用）
        
        公共逻辑：从系统默认时间开始到最近完成的交易日
        
        Args:
            data_manager: DataManager 实例（用于查询数据库）
            date_format: 日期格式（quarter | month | day）
            context: 执行上下文（可能包含 latest_completed_trading_date）
        
        Returns:
            Tuple[str, str]: (start_date, end_date)
        """
        context = context or {}
        
        # 获取系统默认开始日期
        default_start_date = ConfigManager.get_default_start_date()
        
        # 获取最近完成的交易日（优先从 context 读取）
        latest_completed_trading_date = context.get("latest_completed_trading_date")
        if not latest_completed_trading_date and data_manager:
            try:
                latest_completed_trading_date = data_manager.service.calendar.get_latest_completed_trading_date()
            except Exception as e:
                logger.warning(f"获取最新交易日失败: {e}，使用当前日期")
                latest_completed_trading_date = DateUtils.today()
        
        if not latest_completed_trading_date:
            latest_completed_trading_date = DateUtils.today()
        
        # 根据 date_format 转换日期格式
        start_date = RenewCommonHelper.convert_date_to_format(default_start_date, date_format)
        end_date = RenewCommonHelper.convert_date_to_format(latest_completed_trading_date, date_format)
        
        return start_date, end_date
    
    @staticmethod
    def convert_date_to_format(date_str: str, date_format: str) -> str:
        """
        将日期字符串转换为指定格式
        
        Args:
            date_str: 日期字符串（YYYYMMDD）
            date_format: 目标格式（quarter | month | day）
        
        Returns:
            转换后的日期字符串
        """
        # 支持枚举和字符串两种格式（兼容性）
        if isinstance(date_format, TermType):
            date_format = date_format.value
        
        if date_format == TermType.QUARTERLY.value:
            year = int(date_str[:4])
            month = int(date_str[4:6])
            if month <= 3:
                quarter = 1
            elif month <= 6:
                quarter = 2
            elif month <= 9:
                quarter = 3
            else:
                quarter = 4
            return f"{year}Q{quarter}"
        elif date_format == TermType.MONTHLY.value:
            return date_str[:6]  # YYYYMM
        else:  # date_format == TermType.DAILY.value
            return date_str  # YYYYMMDD
    
    @staticmethod
    def get_end_date(date_format: str, context: Dict[str, Any]) -> str:
        """
        获取结束日期（所有股票统一使用 latest_completed_trading_date）。

        Args:
            date_format: 日期格式（quarter | month | day）
            context: 执行上下文

        Returns:
            str: 结束日期
        """
        latest_completed_trading_date = context.get("latest_completed_trading_date")
        if latest_completed_trading_date:
            if date_format == "day":
                return latest_completed_trading_date
            else:
                period_type = DateUtils.normalize_period_type(date_format)
                return DateUtils.to_period_str(latest_completed_trading_date, period_type)
        else:
            current_date = DateUtils.today()
            period_type = DateUtils.normalize_period_type(date_format)
            current_period = DateUtils.to_period_str(current_date, period_type)
            return current_period
    
    @staticmethod
    def get_needs_stock_grouping(context: Dict[str, Any]) -> Optional[bool]:
        """
        从 context 中获取配置，判断是否需要按股票分组。

        Args:
            context: 执行上下文

        Returns:
            Optional[bool]: 是否需要分组，None 表示未配置
        """
        if not context:
            return None
        config = context.get("config")
        if not config:
            return None
        
        from core.modules.data_source.data_class.config import DataSourceConfig

        if isinstance(config, DataSourceConfig):
            return config.is_per_entity() or config.get_needs_stock_grouping()
        return None
    
    @staticmethod
    def query_latest_date(
        data_manager,
        table_name: str,
        date_field: str,
        date_format: str,
        needs_stock_grouping: Optional[bool] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, str]]:
        """
        查询数据库最新日期（公共方法）

        逻辑：
        1. 通过 DataManager.get_table() 获取表的 model
        2. 根据配置或表的主键结构判断是否需要按实体分组
        3. 需要分组时，实体标识字段优先用 context 中 config.result_group_by.key 或 keys，
           未提供时从表主键推断（除日期外的第一个主键）

        Args:
            data_manager: DataManager 实例
            table_name: 数据库表名
            date_field: 日期字段名
            date_format: 日期格式
            needs_stock_grouping: 是否需要按实体分组（None 表示自动判断）
            context: 执行上下文；若提供且 per-entity，用 config.get_group_by_key() 作为实体标识字段

        Returns:
            - 需要分组：Dict[str, str] {entity_id: latest_date}，表为空返回 None
            - 不需要分组：None（调用方单独处理）
        """
        if not data_manager:
            return None
        
        try:
            # 步骤 1：通过 DataManager 获取 model（内部方法，仅供 service 使用）
            model = data_manager.get_table(table_name)
            if not model:
                return None
            
            # 步骤 2：判断是否需要分组（优先级：配置 > 自动判断）
            if needs_stock_grouping is None:
                # 如果未配置，根据主键结构自动判断
                try:
                    primary_keys = model.get_primary_keys()
                    # 过滤掉日期字段，得到分组键
                    group_keys = [k for k in primary_keys if k != date_field]
                    needs_grouping = len(group_keys) > 0
                except Exception:
                    # 如果无法获取主键，默认需要分组（保守策略）
                    needs_grouping = True
            else:
                needs_grouping = needs_stock_grouping
            
            # 步骤 3：根据是否需要分组，查询最新日期
            if not needs_grouping:
                # 不需要分组：返回 None，调用方需要单独处理（查询整个表的最新日期）
                return None
            
            # 需要分组：查询每个实体的最新日期
            try:
                # 优先从 config 读取 group_fields（支持多字段分组）
                group_fields = None
                if context:
                    config = context.get("config")
                    if config:
                        group_fields = config.get_group_fields()
                
                # 如果未配置 group_fields，从主键推断（向后兼容）
                if not group_fields:
                    primary_keys = model.get_primary_keys()
                    group_fields = [k for k in primary_keys if k != date_field]
                    # date_field=last_update 时按「实体」分组，应只用实体 id 而非复合主键
                    # 例：adj_factor_events 主键 (id, event_date)，取 MAX(last_update) 应按 id 分组
                    if date_field == "last_update" and len(group_fields) > 1:
                        group_fields = [group_fields[0]]
                
                if not group_fields:
                    return None
                
                latest_records = model.load_latests(
                    date_field=date_field, group_fields=group_fields
                )
                if not latest_records:
                    logger.warning(f"⚠️ [query_latest_date] load_latests 返回空结果: table={table_name}, group_fields={group_fields}")
                    return None

                # 判断是单字段还是多字段分组
                is_multi_field = len(group_fields) > 1
                
                result = {}
                for record in latest_records:
                    latest_date = record.get(date_field)
                    if not latest_date:
                        logger.debug(f"⚠️ [query_latest_date] 记录缺少日期字段: {record}")
                        continue
                    
                    if is_multi_field:
                        # 多字段分组：使用分隔符 "::" 连接多个字段值作为复合键
                        composite_key_parts = [str(record.get(field, "")) for field in group_fields]
                        composite_key = "::".join(composite_key_parts)
                        result[composite_key] = latest_date
                    else:
                        # 单字段分组：使用单个字段值作为 key（向后兼容）
                        entity_id = record.get(group_fields[0])
                        if entity_id is not None:
                            result[str(entity_id)] = latest_date
                return result if result else None
            except (AttributeError, Exception) as e:
                # 如果 load_latests 不存在或失败，降级到简单查询
                logger.debug(f"使用 load_latests 失败: {e}，降级到简单查询")
                # 对于需要分组的情况，降级查询无法获取 per stock 信息，返回 None
                return None
        except Exception as e:
            logger.warning(f"查询数据库失败 {table_name}.{date_field}: {e}")
        
        return None
    
    @staticmethod
    def calculate_date_range_for_non_grouped(
        data_manager,
        table_name: str,
        date_field: str,
        date_format: str,
        end_date: str,
        context: Dict[str, Any],
        calculate_start_date_fn
    ) -> Tuple[str, str]:
        """
        处理不需要分组的情况：查询整个表的最新日期，计算日期范围。

        Args:
            data_manager: DataManager 实例
            table_name: 数据库表名
            date_field: 日期字段名
            date_format: 日期格式
            end_date: 结束日期
            context: 执行上下文
            calculate_start_date_fn: 计算起始日期的函数 (latest_value, end_date, date_format) -> start_date

        Returns:
            Tuple[str, str]: (start_date, end_date)
        """
        if not data_manager:
            start_date, _ = RenewCommonHelper.get_default_date_range(data_manager, date_format, context)
            return start_date, end_date

        try:
            model = data_manager.get_table(table_name)
            if model:
                latest_record = model.load_one("1=1", order_by=f"{date_field} DESC")
                if latest_record:
                    latest_value = latest_record.get(date_field)
                    if latest_value:
                        start_date = calculate_start_date_fn(latest_value, end_date, date_format)
                        return start_date, end_date
        except Exception as e:
            logger.warning(f"查询非分组表最新日期失败: {e}")

        # 降级：使用默认日期范围
        start_date, _ = RenewCommonHelper.get_default_date_range(data_manager, date_format, context)
        return start_date, end_date
    
    @staticmethod
    def calculate_date_range_for_grouped(
        latest_dates_dict: Dict[str, str],
        end_date: str,
        date_format: str,
        context: Dict[str, Any],
        data_manager,
        calculate_start_date_fn
    ) -> Dict[str, Tuple[str, str]]:
        """
        处理需要分组的情况：为每个股票计算日期范围。

        Args:
            latest_dates_dict: {stock_id: latest_date} 字典
            end_date: 结束日期
            date_format: 日期格式
            context: 执行上下文
            data_manager: DataManager 实例
            calculate_start_date_fn: 计算起始日期的函数 (latest_date, end_date, date_format) -> start_date

        Returns:
            Dict[str, Tuple[str, str]]: {stock_id: (start_date, end_date)}
        """
        stock_list = context.get("stock_list", [])
        if not stock_list:
            logger.warning("需要按股票分组但 stock_list 为空，返回空字典")
            return {}

        # 获取默认起始日期（用于新股票）
        default_start_date, _ = RenewCommonHelper.get_default_date_range(data_manager, date_format, context)

        # 为每个股票计算日期范围
        result = {}
        for stock_id in stock_list:
            stock_id_str = str(stock_id)
            latest_date = latest_dates_dict.get(stock_id_str)

            if latest_date:
                start_date = calculate_start_date_fn(latest_date, end_date, date_format)
            else:
                # 没找到（新股票）：使用系统默认起始时间
                start_date = default_start_date

            result[stock_id_str] = (start_date, end_date)

        return result
