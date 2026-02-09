"""
JobBuilder - 负责根据实体列表与日期范围构建 ApiJobBundle 列表。

当前实现基本等价于 BaseHandler._build_jobs 的逻辑，仅做轻量封装，
便于后续将 Job 构建职责从 BaseHandler 中进一步解耦。
"""
from typing import Any, Dict, List, Tuple, Optional, Callable

from loguru import logger

from core.modules.data_source.data_class.api_job_bundle import ApiJobBundle
from core.modules.data_source.data_class.config import DataSourceConfig


class JobBuilder:
    """
    Job 构建服务：从实体列表和日期范围构建 ApiJobBundle 列表。

    注意：不负责日期范围计算（由 DateRangeService 处理），也不负责字段映射等。
    """

    def build_jobs(
        self,
        context: Dict[str, Any],
        apis_conf: Dict[str, Any],
        entity_list: List[Any],
        entity_date_ranges: Dict[str, Tuple[str, str]],
        build_single_job: Callable[[Any, Dict[str, Any], Tuple[str, str]], Optional[ApiJobBundle]],
    ) -> List[ApiJobBundle]:
        """
        根据实体列表和 entity_date_ranges 构建 ApiJobBundle 列表。

        Args:
            context: 执行上下文（需包含 config 等）
            apis_conf: DataSourceConfig.get_apis() 返回的 apis 配置
            entity_list: 实体列表（如 stock_list / index_list）
            entity_date_ranges: 实体日期范围映射 {entity_id: (start_date, end_date)}
            build_single_job: 构建单个实体 JobBundle 的回调（通常为 BaseHandler._build_job）

        Returns:
            List[ApiJobBundle]: 构建好的 JobBundle 列表
        """
        config: DataSourceConfig = context.get("config")
        if not config or not isinstance(config, DataSourceConfig):
            logger.warning("JobBuilder.build_jobs: context 中缺少有效的 DataSourceConfig，返回空 jobs")
            return []

        # 单字段分组场景：实体 ID 字段来自 job_execution.key
        entity_key_field = config.get_group_by_key()

        jobs: List[ApiJobBundle] = []

        for entity_info in entity_list or []:
            # 实体 ID 的来源遵循 config.job_execution.key 这一单一约定
            if isinstance(entity_info, dict):
                entity_id = entity_info.get(entity_key_field)
            else:
                # 如果依赖里直接给的是字符串/数字（如 ts_code），则直接当作实体 ID
                entity_id = entity_info

            if not entity_id:
                continue

            entity_key = str(entity_id)
            date_range = entity_date_ranges.get(entity_key)
            if not date_range:
                # 该实体本次无需 renew（可能因为未过 renew_if_over_days 阈值）
                continue

            job_collection = build_single_job(entity_info, apis_conf, date_range)
            if job_collection is not None:
                jobs.append(job_collection)

        return jobs

