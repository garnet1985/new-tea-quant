"""
Job Builder - Job 构建器

职责：
1. 构建 jobs（每个 entity 一个 job）
2. 决定多进程 worker 数量
3. 提供 job 相关的辅助方法

所有方法都是静态方法，不需要实例化，类似 helper 职责
"""
from typing import Dict, List, Any, Tuple, Optional
import os
import logging
from app.core.modules.tag.core.enums import TagUpdateMode

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
        from app.core.conf.conf import data_default_start_date
        
        # 确定 end_date（两种模式都使用最新已完成交易日）
        if default_end_date:
            end_date = default_end_date
        else:
            # 从 DataManager 获取最新已完成交易日
            try:
                from app.core.modules.data_manager import DataManager
                data_mgr = DataManager(is_verbose=False)
                end_date = data_mgr.service.calendar.get_latest_completed_trading_date()
            except Exception as e:
                logger.warning(f"获取最新交易日失败，使用空字符串: {e}")
                end_date = ""
        
        # 确定 start_date（根据 update_mode）
        if update_mode == TagUpdateMode.REFRESH:
            # REFRESH 模式：从默认开始日期开始
            if default_start_date:
                start_date = default_start_date
            else:
                start_date = data_default_start_date
        else:
            # INCREMENTAL 模式：从 entity 的最后更新日期继续
            if entity_last_update_date:
                # 获取下一个交易日
                try:
                    from app.core.modules.data_manager import DataManager
                    data_mgr = DataManager(is_verbose=False)
                    tag_service = data_mgr.stock.tags
                    if tag_service:
                        start_date = tag_service.get_next_trading_date(entity_last_update_date)
                    else:
                        # 如果无法获取下一个交易日，使用最后更新日期的下一天（简单处理）
                        logger.warning(f"无法获取 TagDataService，使用简单日期计算")
                        from app.core.utils.date.date_utils import DateUtils
                        start_date = DateUtils.get_next_date(entity_last_update_date)
                except Exception as e:
                    logger.warning(f"获取下一个交易日失败，使用最后更新日期: {e}")
                    start_date = entity_last_update_date
            else:
                # 如果没有历史数据，从默认开始日期开始
                if default_start_date:
                    start_date = default_start_date
                else:
                    start_date = data_default_start_date
        
        return start_date, end_date
    


    @staticmethod
    def decide_worker_amount(estimated_job_count: int, max_workers: Any = None) -> int:
        """
        根据 job 数量决定进程数（最多 max_workers 个）
        
        策略：
        - 100个job及以下：1个worker
        - 500个job及以下，100个以上：2个worker
        - 1000个job及以下，500个以上：4个worker
        - 2000个job及以下，1000个以上：8个worker
        - 2000个job以上：最大worker（max_workers，默认 CPU 核心数）
        
        Args:
            estimated_job_count: 预估的 job 数量
            max_workers: 最大 worker 数量（可选，可以是 "auto"、int 或 None，默认使用 CPU 核心数）
        
        Returns:
            int: 建议的 worker 数量
        """
        if max_workers == "auto" or max_workers is None:
            max_workers = os.cpu_count() or 10
        
        worker_amount = 1
        if estimated_job_count <= 100:
            worker_amount = 1
        elif estimated_job_count <= 500:
            worker_amount = 2
        elif estimated_job_count <= 1000:
            worker_amount = 4
        elif estimated_job_count <= 2000:
            worker_amount = 8
        else:
            worker_amount = max_workers
            
        return min(worker_amount, max_workers)
    
