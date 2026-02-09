"""
Fetched Data Helper

负责在执行层与标准化层之间，对执行结果 `fetched_data` 做分组与重组：

- `build_grouped_fetched_data`：按 API + entity 分桶，供 per-entity 标准化使用；
- `build_unified_fetched_data`：不分实体，简单按 API 聚合到 `_unified`；
- `has_group_by_config`：根据 config / apis 判断是否应走 per-entity 分组流程。

该模块的实现从 `DataSourceHandlerHelper` 中抽取而来，作为独立 helper 提供给
`BundleExecutionService` / `BaseHandler` 等调用方使用。
"""

from typing import Any, Dict, List

from loguru import logger

from core.modules.data_source.data_class.api_job import ApiJob
from core.modules.data_source.data_class.config import DataSourceConfig


def build_grouped_fetched_data(
    context: Dict[str, Any],
    fetched_data: Dict[str, Any],
    apis: List[ApiJob],
) -> Dict[str, Dict[str, Any]]:
    """
    根据配置中的 params_mapping，将执行层返回的 {job_id: result} 统一整理为标准的
    fetched_data 结构，供 normalize 阶段使用。

    统一规范：

    fetched_data = {
        api_name: {
            "_unified": raw_result,     # 全局数据（无 job_execution 时）
            entity_id1: raw_result_1,   # 按实体分组的数据
            entity_id2: raw_result_2,
            ...
        }
    }

    规则：从 apis[api_name].params_mapping 的 key 取 entity_id；无 params_mapping 时放入 "_unified"。

    注意：
    - 该方法仅负责“按 API + entity 分组”，不负责字段映射和 schema 处理；
    - 子类如需更复杂的重组逻辑（例如跨 API 合并），可以在 on_after_fetch 中自行调用
      本方法作为基础，或完全自定义实现。
    """
    config = context.get("config")
    if not isinstance(config, DataSourceConfig):
        return {}
    apis_conf = config.get_apis()

    grouped: Dict[str, Dict[str, Any]] = {}

    for api_job in apis or []:
        api_name = getattr(api_job, "api_name", None)
        job_id = getattr(api_job, "job_id", None) or api_name
        if not api_name or not job_id:
            continue

        raw_result = fetched_data.get(job_id)
        if raw_result is None:
            continue

        api_conf = apis_conf.get(api_name)
        params_mapping = api_conf.params_mapping if api_conf else {}

        bucket = grouped.setdefault(api_name, {})
        params = getattr(api_job, "params", {}) or {}

        # per-entity 且有 params_mapping：从 params 取 entity_id
        if params_mapping and config.has_result_group_by():
            if len(params_mapping) == 1:
                param_key = next(iter(params_mapping.keys()))
                entity_id = params.get(param_key)
                if entity_id is not None:
                    bucket[str(entity_id)] = raw_result
                else:
                    if "_unified" in bucket:
                        logger.warning(
                            f"[DataSource:{context.get('data_source_key', 'unknown')}][API:{api_name}] "
                            "存在多个未能识别实体 ID 的结果，写入同一 '_unified' 分组，后写将覆盖前写。"
                        )
                    bucket["_unified"] = raw_result
            else:
                # 多字段：用 "::" 拼接 params 值
                entity_id = "::".join(str(params.get(k, "")) for k in params_mapping.keys())
                if entity_id:
                    bucket[str(entity_id)] = raw_result
                else:
                    if "_unified" in bucket:
                        logger.warning(
                            f"[DataSource:{context.get('data_source_key', 'unknown')}][API:{api_name}] "
                            "存在多个未能识别实体 ID 的结果，写入同一 '_unified' 分组，后写将覆盖前写。"
                        )
                    bucket["_unified"] = raw_result
        else:
            if "_unified" in bucket:
                logger.warning(
                    f"[DataSource:{context.get('data_source_key', 'unknown')}][API:{api_name}] "
                    "未配置 params_mapping 且产生了多个结果，将按顺序覆盖 '_unified'。"
                )
            bucket["_unified"] = raw_result

    return grouped


def build_unified_fetched_data(
    context: Dict[str, Any],
    fetched_data: Dict[str, Any],
    apis: List[ApiJob],
) -> Dict[str, Dict[str, Any]]:
    """
    不考虑 group_by，简单按 api_name 聚合结果到 \"_unified\"。

    适用于：
    - 所有 API 都是全局数据（无实体维度）；
    - 或者暂时不希望在 BaseHandler 层做实体分组，只要一个统一的数据块。
    """
    unified: Dict[str, Dict[str, Any]] = {}

    for api_job in apis or []:
        api_name = getattr(api_job, "api_name", None)
        job_id = getattr(api_job, "job_id", None) or api_name
        if not api_name or not job_id:
            continue

        raw_result = fetched_data.get(job_id)
        if raw_result is None:
            continue

        bucket = unified.setdefault(api_name, {})
        if "_unified" in bucket:
            logger.warning(
                f"[DataSource:{context.get('data_source_key', 'unknown')}][API:{api_name}] "
                "未使用 group_by 但产生了多个结果，将按顺序覆盖 '_unified'。"
            )
        bucket["_unified"] = raw_result

    return unified


def has_group_by_config(context: Dict[str, Any], apis: List[ApiJob]) -> bool:
    """
    检查是否应按 per-entity 分组整理 fetched_data。

    返回 True：config 有 job_execution（per-entity 模式）且至少有一个 API 配置了 params_mapping。
    """
    config = context.get("config")
    if not isinstance(config, DataSourceConfig) or not config.has_result_group_by():
        return False

    apis_conf = config.get_apis()
    for api_job in apis or []:
        api_name = getattr(api_job, "api_name", None)
        if not api_name:
            continue
        api_conf = apis_conf.get(api_name)
        if api_conf and api_conf.params_mapping:
            return True
    return False

