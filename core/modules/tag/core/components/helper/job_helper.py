"""
Job Builder - Job 构建器

职责：
1. 构建 jobs（每个 entity 一个 job）
2. 决定多进程 worker 数量
3. 提供 job 相关的辅助方法

所有方法都是静态方法，不需要实例化，类似 helper 职责
"""
from typing import Dict, List, Any, Tuple, Optional
import logging
from core.modules.tag.core.enums import TagUpdateMode
from core.utils.date.date_utils import DateUtils

logger = logging.getLogger(__name__)


class JobHelper:
    """
    Job Builder - Job 构建器
    
    职责：
    1. 构建 jobs（每个 entity 一个 job）
    2. 决定多进程 worker 数量
    3. 提供 job 相关的辅助方法
    
    所有方法都是静态方法，不需要实例化
    """


    @staticmethod
    def _resolve_latest_completed_trading_date() -> str:
        """
        解析最新已完成交易日。
        这里先使用 today 作为无外部依赖的安全默认值，后续可替换为独立日历 contract。
        """
        try:
            return DateUtils.today()
        except Exception as e:
            logger.warning(f"获取最新交易日失败，使用空字符串: {e}")
            return ""

    @staticmethod
    def calculate_start_and_end_date(
        update_mode: TagUpdateMode,
        entity_last_update_date: Optional[str] = None,
        default_start_date: Optional[str] = None,
        default_end_date: Optional[str] = None
    ) -> Tuple[str, str]:
        """
        计算起始日期和结束日期
        
        Args:
            update_mode: 更新模式（TagUpdateMode.REFRESH 或 TagUpdateMode.INCREMENTAL）
            entity_last_update_date: 该 entity 的最后更新日期（INCREMENTAL 模式使用）
            default_start_date: 默认开始日期（REFRESH 模式使用，如果为 None 则从 conf 获取）
            default_end_date: 默认结束日期（如果为 None 则从 DataManager 获取）
            
        Returns:
            Tuple[str, str]: (start_date, end_date)
        """
        from core.infra.project_context import ConfigManager
        
        # 确定 end_date（两种模式都使用最新已完成交易日）
        if default_end_date:
            end_date = default_end_date
        else:
            end_date = JobHelper._resolve_latest_completed_trading_date()
        
        # 确定 start_date（根据 update_mode）
        if update_mode == TagUpdateMode.REFRESH:
            # REFRESH 模式：从默认开始日期开始
            if default_start_date:
                start_date = default_start_date
            else:
                start_date = ConfigManager.get_default_start_date()
        else:
            # INCREMENTAL 模式：从 entity 的最后更新日期继续
            if entity_last_update_date:
                # 当前版本使用“自然日 +1”作为下一交易日的近似策略
                start_date = DateUtils.add_days(entity_last_update_date, 1)
            else:
                # 如果没有历史数据，从默认开始日期开始
                if default_start_date:
                    start_date = default_start_date
                else:
                    start_date = ConfigManager.get_default_start_date()
        
        return start_date, end_date
    
