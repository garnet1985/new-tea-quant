"""
Job Builder - Job 构建器

职责：
1. 构建 jobs（每个 entity 一个 job）
2. 决定多进程 worker 数量
3. 提供 job 相关的辅助方法

所有方法都是静态方法，不需要实例化，类似 helper 职责
"""
from typing import Dict, List, Any, Tuple
import os
import logging
from app.enums import UpdateMode
from app.tag.core.models.scenario_model import ScenarioModel
from app.tag.core.models.tag_model import TagModel

logger = logging.getLogger(__name__)


class JobBuilder:
    """
    Job Builder - Job 构建器
    
    职责：
    1. 构建 jobs（每个 entity 一个 job）
    2. 决定多进程 worker 数量
    3. 提供 job 相关的辅助方法
    
    所有方法都是静态方法，不需要实例化
    """

    @staticmethod
    def build_jobs(
        scenario_model: ScenarioModel, 
        entity_list: List[str], 
        tag_value_last_update_info: Dict[str, Any],
        update_mode: UpdateMode) -> List[Dict[str, Any]]:
        """
        构建 jobs（每个 entity 一个 job）
        
        Args:
            scenario_model: ScenarioModel 实例（已 ensure_metadata）
            entity_list: 实体ID列表
            tag_value_last_update_info: 上次计算的 tag 值更新信息
            update_mode: 更新模式
        
        Returns:
            List[Dict[str, Any]]: Job列表，每个 job 包含：
                - "id": str - job ID
                - "payload": Dict[str, Any] - job payload（伪代码，待完善）
        """
        jobs = []
        for entity_id in entity_list:
            last_update_info = tag_value_last_update_info[entity_id]
            start_date, end_date = JobBuilder.calculate_start_and_end_date(last_update_info, update_mode)

            job = {
                "id": JobBuilder._generate_job_id(entity_id, scenario_model.get_name()),
                "payload": {
                    # TODO: 伪代码，待完善
                    # - entity_id: 实体ID
                    # - entity_type: 实体类型（从 scenario_model 获取）
                    # - scenario_name: Scenario 名称
                    # - scenario_version: Scenario 版本
                    # - tag_definitions: Tag Definition 列表（从 scenario_model.get_tag_models() 获取并转换为字典）
                    # - start_date: 起始日期
                    # - end_date: 结束日期
                    # - worker_class: Worker 类（需要从 scenario_cache 或 settings 获取）
                    # - settings: Settings 字典（从 scenario_model.get_settings() 获取）
                }
            }
            jobs.append(job)
        return jobs

    @staticmethod
    def calculate_start_and_end_date(last_update_info: Dict[str, Any], update_mode: UpdateMode) -> Tuple[str, str]:
        """
        计算起始日期和结束日期
        """
        pass
        # if update_mode == UpdateMode.INCREMENTAL:
        #     return last_update_info["start_date"], last_update_info["end_date"]
        # else:
        #     return default_data_start_date, latest_completed_trading_date
    


    
    # @staticmethod
    # def build_jobs(
    #     scenario_setting: Dict[str, Any],
    #     tag_defs: List[Dict[str, Any]],
    #     start_date: str,
    #     end_date: str,
    #     entity_list: List[str]
    # ) -> List[Dict[str, Any]]:
    #     """
    #     构建 jobs（每个 entity 一个 job）
        
    #     职责：
    #     1. 为每个 entity 创建一个 job
    #     2. 组装 job payload（包含所有必要信息）
        
    #     Args:
    #         scenario_setting: Scenario settings 字典，包含：
    #             - "scenario_name": str
    #             - "worker_class": Type[BaseTagWorker]
    #             - "settings": Dict[str, Any]
    #         tag_defs: Tag Definition 列表
    #         start_date: 起始日期（YYYYMMDD 格式）
    #         end_date: 结束日期（YYYYMMDD 格式）
    #         entity_list: 实体ID列表
        
    #     Returns:
    #         List[Dict[str, Any]]: Job列表，每个 job 包含：
    #             - "id": str - job ID（格式：{entity_id}_{scenario_name}）
    #             - "payload": Dict[str, Any] - job payload，包含：
    #                 - entity_id: 实体ID
    #                 - entity_type: 实体类型（当前固定为 "stock"）
    #                 - scenario_name: Scenario 名称
    #                 - scenario_version: Scenario 版本
    #                 - tag_definitions: Tag Definition 列表
    #                 - start_date: 起始日期
    #                 - end_date: 结束日期
    #                 - worker_class: Worker 类（用于子进程中实例化）
    #                 - settings: Settings 字典（完整的 settings 配置）
    #     """
    #     jobs = []
    #     scenario_name = scenario_setting["scenario_name"]
        
    #     if not entity_list:
    #         logger.warning(f"没有实体需要计算: scenario={scenario_name}")
    #         return jobs
        
    #     # 为每个 entity 创建 job
    #     # 注意：直接传递完整的 settings 字典，避免在子进程中重复加载
    #     # 这样如果 settings 结构变化，只需要改 BaseTagWorker 一处即可
    #     for entity_id in entity_list:
    #         job = {
    #             "id": JobBuilder._generate_job_id(entity_id, scenario_name),
    #             "payload": {
    #                 # 实体信息
    #                 "entity_id": entity_id,
    #                 "entity_type": "stock",  # TODO: 未来支持 macro, corporate_finance 等
                    
    #                 # Scenario 信息
    #                 "scenario_name": scenario_name,
    #                 "scenario_version": scenario_setting["settings"]["scenario"]["version"],
                    
    #                 # Tag 信息（必需，因为需要 tag_definition_id）
    #                 # 转换为字典以便序列化到子进程
    #                 "tag_definitions": [tag_def.to_dict() for tag_def in tag_defs],
                    
    #                 # 日期范围（必需）
    #                 "start_date": start_date,
    #                 "end_date": end_date,
                    
    #                 # Worker 实例化所需（子进程中需要）
    #                 "worker_class": scenario_setting["worker_class"],
    #                 "settings": scenario_setting["settings"],  # 直接传完整的 settings 字典
    #             }
    #         }
    #         jobs.append(job)
        
    #     logger.info(
    #         f"构建 jobs 完成: scenario={scenario_name}, "
    #         f"entities={len(entity_list)}, jobs={len(jobs)}"
    #     )
        
    #     return jobs
    
    @staticmethod
    def decide_worker_amount(jobs: List[Dict[str, Any]], max_workers: int = None) -> int:
        """
        根据 job 数量决定进程数（最多 max_workers 个）
        
        策略：
        - 100个job及以下：1个worker
        - 500个job及以下，100个以上：2个worker
        - 1000个job及以下，500个以上：4个worker
        - 2000个job及以下，1000个以上：8个worker
        - 2000个job以上：最大worker（max_workers，默认 CPU 核心数）
        
        Args:
            jobs: Job 列表
            max_workers: 最大 worker 数量（可选，默认使用 CPU 核心数）
        
        Returns:
            int: 建议的 worker 数量
        """
        if max_workers is None:
            max_workers = os.cpu_count() or 10  # 默认最多 10 个
        
        job_count = len(jobs)
        
        if job_count <= 100:
            worker_amount = 1
        elif job_count <= 500:
            worker_amount = 2
        elif job_count <= 1000:
            worker_amount = 4
        elif job_count <= 2000:
            worker_amount = 8
        else:
            worker_amount = max_workers
        
        return min(worker_amount, max_workers)
    
    @staticmethod
    def _generate_job_id(entity_id: str, scenario_name: str) -> str:
        """
        生成 job ID
        
        Args:
            entity_id: 实体ID
            scenario_name: Scenario 名称
        
        Returns:
            str: Job ID（格式：{entity_id}_{scenario_name}）
        """
        return f"{entity_id}_{scenario_name}"
    
    @staticmethod
    def validate_jobs(jobs: List[Dict[str, Any]]) -> bool:
        """
        验证 jobs 的有效性
        
        Args:
            jobs: Job 列表
        
        Returns:
            bool: 如果所有 jobs 都有效则返回 True，否则返回 False
        """
        if not jobs:
            return True
        
        required_payload_keys = [
            "entity_id",
            "entity_type",
            "scenario_name",
            "scenario_version",
            "tag_definitions",
            "start_date",
            "end_date",
            "worker_class",
            "settings"
        ]
        
        for i, job in enumerate(jobs):
            if "id" not in job:
                logger.error(f"Job {i} 缺少 'id' 字段")
                return False
            
            if "payload" not in job:
                logger.error(f"Job {i} (id={job.get('id')}) 缺少 'payload' 字段")
                return False
            
            payload = job["payload"]
            missing_keys = [key for key in required_payload_keys if key not in payload]
            if missing_keys:
                logger.error(
                    f"Job {i} (id={job.get('id')}) payload 缺少必需字段: {missing_keys}"
                )
                return False
        
        return True
    
    @staticmethod
    def get_job_statistics(jobs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        获取 jobs 的统计信息
        
        Args:
            jobs: Job 列表
        
        Returns:
            Dict[str, Any]: 统计信息，包含：
                - total_jobs: 总 job 数量
                - entity_types: 实体类型统计
                - scenario_names: Scenario 名称统计
        """
        stats = {
            "total_jobs": len(jobs),
            "entity_types": {},
            "scenario_names": {}
        }
        
        for job in jobs:
            payload = job.get("payload", {})
            
            # 统计实体类型
            entity_type = payload.get("entity_type", "unknown")
            stats["entity_types"][entity_type] = stats["entity_types"].get(entity_type, 0) + 1
            
            # 统计 scenario 名称
            scenario_name = payload.get("scenario_name", "unknown")
            stats["scenario_names"][scenario_name] = stats["scenario_names"].get(scenario_name, 0) + 1
        
        return stats
