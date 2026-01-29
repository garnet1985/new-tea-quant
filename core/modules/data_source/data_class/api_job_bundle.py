from dataclasses import dataclass
from typing import List, Optional

from core.modules.data_source.data_class.api_job import ApiJob


@dataclass
class ApiJobBundle:
    """
    ApiJobBatch: 一批需要一起执行的 ApiJobs

    设计意图：
    - 表达"这一批 ApiJobs 组成了一次完整的数据抓取计划"；
    - 用于在 Handler 侧描述执行计划；
    - 具体如何执行（拓扑排序、限流、并发策略）仍由执行器负责。
    """

    bundle_id: str  # 批次 ID（通常建议使用 data_source_name_batch 等语义化命名）
    apis: List[ApiJob]  # 本批次需要执行的 ApiJobs
    tuple_order_map: Optional[str] = None  # 批次描述（可选）
    start_date: Optional[str] = None  # 本批次统一的开始日期（可选）
    end_date: Optional[str] = None  # 本批次统一的结束日期（可选）

    @staticmethod
    def to_id(data_source_name: str) -> str:
        """
        根据 data_source_name 生成标准化的 batch_id。

        约定：
        - 统一使用 "{data_source_name}_batch" 的格式；
        - 如果 data_source_name 为空，则退化为 "data_source_batch"。
        """
        name = data_source_name or "data_source"
        return f"{name}_batch"

    def sort_by_map():
        pass


    def execute():
        pass