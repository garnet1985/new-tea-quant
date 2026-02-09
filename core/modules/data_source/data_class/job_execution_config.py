"""
JobExecutionConfig: job_execution 配置 DataClass。

强类型，构造时校验。key 与 keys 互斥；keys 时 terms 必填。不允许运行时推断。
"""
from dataclasses import dataclass
from typing import List, Optional

from core.modules.data_source.data_class.error import DataSourceConfigError


@dataclass(frozen=True)
class JobExecutionConfig:
    """
    per-entity 模式下的 job 执行配置。

    - list: 实体列表来源（dependencies 中的 key），必填
    - key: 单字段分组（与 keys 互斥）
    - keys: 多字段分组（与 key 互斥），配置 keys 时 terms 必填
    - terms: 多字段时的 term 列表，如 ["daily","weekly","monthly"]
    - merge_by: 跨 API 合并时的 key，如 "id"
    """

    list_name: str
    key: Optional[str]
    keys: Optional[List[str]]
    terms: Optional[List[str]]
    merge_by: Optional[str]

    @classmethod
    def from_dict(
        cls,
        d: dict,
        data_source_key: str,
    ) -> "JobExecutionConfig":
        """
        从字典解析并校验。错误时抛出 DataSourceConfigError。
        不允许运行时推断，terms 等必须显式配置。
        """
        if not isinstance(d, dict):
            raise DataSourceConfigError(
                f"{data_source_key}: job_execution 必须是字典，收到: {type(d).__name__}"
            )

        list_name = d.get("list")
        if not list_name or not str(list_name).strip():
            raise DataSourceConfigError(
                f"{data_source_key}: job_execution 必须配置 list"
            )
        list_name = str(list_name).strip()

        key = d.get("key")
        keys = d.get("keys")
        if key and keys:
            raise DataSourceConfigError(
                f"{data_source_key}: job_execution 不能同时配置 key 和 keys，互斥"
            )
        if not key and not keys:
            raise DataSourceConfigError(
                f"{data_source_key}: job_execution 必须配置 key（单字段）或 keys（多字段）之一"
            )

        if key:
            key = str(key).strip() if key else None
            keys = None
            terms = None
        else:
            if isinstance(keys, str):
                keys = [keys]
            elif isinstance(keys, list):
                keys = [str(k).strip() for k in keys if k is not None]
            else:
                raise DataSourceConfigError(
                    f"{data_source_key}: job_execution.keys 必须是字符串或列表"
                )
            if not keys:
                raise DataSourceConfigError(
                    f"{data_source_key}: job_execution.keys 不能为空"
                )

            terms_raw = d.get("terms")
            if terms_raw is None:
                raise DataSourceConfigError(
                    f"{data_source_key}: job_execution 配置了 keys 时必须配置 terms，不允许运行时推断"
                )
            if isinstance(terms_raw, str):
                terms = [terms_raw.strip()]
            elif isinstance(terms_raw, list):
                terms = [str(t).strip() for t in terms_raw if t is not None]
            else:
                raise DataSourceConfigError(
                    f"{data_source_key}: job_execution.terms 必须是字符串或列表"
                )
            if not terms:
                raise DataSourceConfigError(
                    f"{data_source_key}: job_execution.terms 不能为空"
                )
            key = None

        merge_raw = d.get("merge")
        merge_by = None
        if isinstance(merge_raw, dict) and merge_raw.get("by"):
            merge_by = str(merge_raw["by"]).strip()

        return cls(
            list_name=list_name,
            key=key,
            keys=keys,
            terms=terms,
            merge_by=merge_by,
        )
