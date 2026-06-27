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
from core.modules.tag.enums import TagUpdateMode
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
        try:
            from core.modules.data_manager import DataManager

            dm = DataManager.get_instance()
            if dm is None:
                dm = DataManager(is_verbose=False)
            if dm and getattr(dm, "service", None):
                return str(
                    dm.service.calendar.get_latest_completed_trading_date() or ""
                ).strip()
        except Exception as exc:
            logger.warning("获取 latest completed trading date 失败: %s", exc)
        return ""

    @staticmethod
    def _cap_end_date_to_latest(end_date: str, latest_completed: str) -> str:
        configured = str(end_date or "").strip()
        latest = str(latest_completed or "").strip()
        if not configured:
            return latest
        if latest and configured > latest:
            return latest
        return configured

    @staticmethod
    def calculate_start_and_end_date(
        update_mode: TagUpdateMode,
        entity_last_update_date: Optional[str] = None,
        default_start_date: Optional[str] = None,
        default_end_date: Optional[str] = None,
        *,
        latest_completed_trading_date: Optional[str] = None,
    ) -> Tuple[str, str]:
        """
        计算起始日期和结束日期
        
        Args:
            update_mode: 更新模式（TagUpdateMode.REFRESH 或 TagUpdateMode.INCREMENTAL）
            entity_last_update_date: 该 entity 的最后更新日期（INCREMENTAL 模式使用）
            default_start_date: 默认开始日期（REFRESH 模式使用，如果为 None 则从 conf 获取）
            default_end_date: 场景配置的结束日期；若晚于 latest completed 则截断到后者
            latest_completed_trading_date: 可选；传入则不再逐 entity 查 CalendarService
            
        Returns:
            Tuple[str, str]: (start_date, end_date)
        """
        from core.infra.project_context import ProjectContext

        latest_completed = (
            str(latest_completed_trading_date or "").strip()
            or JobHelper._resolve_latest_completed_trading_date()
        )
        if default_end_date:
            end_date = JobHelper._cap_end_date_to_latest(default_end_date, latest_completed)
        else:
            end_date = latest_completed
        
        # 确定 start_date（根据 update_mode）
        if update_mode == TagUpdateMode.REFRESH:
            # REFRESH 模式：从默认开始日期开始
            if default_start_date:
                start_date = default_start_date
            else:
                start_date = ProjectContext.path.get_default_start_date()
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
                    start_date = ProjectContext.path.get_default_start_date()
        
        return start_date, end_date
    
