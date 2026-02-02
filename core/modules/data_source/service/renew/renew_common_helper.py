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
                latest_completed_trading_date = DateUtils.get_current_date_str()
        
        if not latest_completed_trading_date:
            latest_completed_trading_date = DateUtils.get_current_date_str()
        
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
                return DateUtils.format_period(
                    DateUtils.get_current_period(latest_completed_trading_date, date_format),
                    date_format
                )
        else:
            current_date = DateUtils.get_current_date_str()
            current_value = DateUtils.get_current_period(current_date, date_format)
            return DateUtils.format_period(current_value, date_format)
    
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
        if config and hasattr(config, "get_needs_stock_grouping"):
            return config.get_needs_stock_grouping()
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
        3. 需要分组时，实体标识字段优先用 context 中 config.result_group_by.by_key，
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
                    primary_keys = model._get_primary_keys_from_schema()
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
            
            # 需要分组：查询每个实体的最新日期；实体标识字段优先用 config.result_group_by.by_key
            try:
                primary_keys = model._get_primary_keys_from_schema()
                group_keys = [k for k in primary_keys if k != date_field]
                if not group_keys:
                    return None
                latest_records = model.load_latest_records(
                    date_field=date_field, group_fields=group_keys
                )
                if not latest_records:
                    return None

                entity_key_field = None
                if context:
                    config = context.get("config")
                    if config and hasattr(config, "get_group_by_key"):
                        entity_key_field = config.get_group_by_key()
                if not entity_key_field:
                    entity_key_field = group_keys[0] if group_keys else "id"

                result = {}
                for record in latest_records:
                    entity_id = record.get(entity_key_field)
                    latest_date = record.get(date_field)
                    if entity_id is not None and latest_date:
                        result[entity_id] = latest_date
                return result if result else None
            except (AttributeError, Exception) as e:
                # 如果 load_latest_records 不存在或失败，降级到简单查询
                logger.debug(f"使用 load_latest_records 失败: {e}，降级到简单查询")
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
