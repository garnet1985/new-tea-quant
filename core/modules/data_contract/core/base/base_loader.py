"""DataKey Loader 抽象基类。"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, List, Mapping, Optional, Sequence

from core.utils.date.date_utils import DateUtils


class BaseDataContractLoader(ABC):
    """所有业务 Loader 的抽象基类。

    API 设计：
    - global scope：load(params) + load_batch(entity_ids, params)（返回相同数据）
    - per_entity scope：load_single(entity_id, params) + load_batch(entity_ids, params)
    """

    @abstractmethod
    def load(self, params: Mapping[str, Any]) -> Any:
        """
        加载单个数据源 - 必须实现。

        对于 GLOBAL scope 的数据源，返回全局数据（如股票列表、交易日历）。
        对于 PER_ENTITY scope 的数据源，返回单个实体的数据（params 包含 entity_id）。

        Args:
            params: 加载参数（包含 start/end 等，以及 entity_id（仅 per_entity））

        Returns:
            加载的数据
        """
        raise NotImplementedError

    @abstractmethod
    def load_batch(
        self,
        entity_ids: Sequence[str],
        params: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        """
        批量加载多个实体数据 - **必须实现**（强制要求）。

        **重要**：此方法必须使用真正的批量查询（如 SQL WHERE IN），
        禁止在内部循环调用 ``self.load()`` 以避免性能问题。

        Args:
            entity_ids: 实体 ID 列表（如股票代码）
            params: 加载参数（包含 start/end 等，不包含 entity_id）

        Returns:
            Dict[entity_id, data]: 每个实体对应的数据

        Raises:
            NotImplementedError: 如果子类未实现真正的批量查询逻辑
        """
        raise NotImplementedError("子类必须实现 load_batch() 以支持批量查询")

    @staticmethod
    def build_batch_load_params(
        entity_id: str,
        params: Mapping[str, Any],
    ) -> dict[str, Any]:
        """
        构建单个 entity 的加载参数（用于批量加载时循环调用）。

        用途：在 load_batch 默认实现中，对每个 entity_id 构建 params。
        
        Args:
            entity_id: 实体 ID（如股票代码）
            params: 批量加载参数（不包含 entity_id）

        Returns:
            单个 entity 的加载参数（包含 entity_id）
        
        示例：
            批量加载时，默认实现：
            ```python
            def load_batch(entity_ids, params):
                result = {}
                for entity_id in entity_ids:
                    single_params = self.build_batch_load_params(entity_id, params)
                    data = self.load(single_params)
                    result[entity_id] = data
                return result
            ```
        """
        return {**params, "entity_id": entity_id}

    @staticmethod
    def drop_boundary_rows(
        rows: List[Mapping[str, Any]],
        *,
        start: Optional[str],
        end: Optional[str],
        include_boundary: bool,
        time_field: str = "date",
    ) -> List[Mapping[str, Any]]:
        """
        根据 include_boundary 参数过滤边界行。

        Args:
            rows: 原始数据行列表
            start: 起始日期（可选）
            end: 结束日期（可选）
            include_boundary: 是否包含边界
            time_field: 时间字段名（默认 "date"）

        Returns:
            过滤后的数据行列表
        """
        if include_boundary:
            return rows

        out: List[Mapping[str, Any]] = []
        for row in rows:
            raw_d = row.get(time_field)
            row_date = DateUtils.normalize_str(raw_d) if raw_d is not None else None
            if row_date is None:
                out.append(row)
                continue
            if start is not None and row_date == start:
                continue
            if end is not None and row_date == end:
                continue
            out.append(row)
        return out


__all__ = ['BaseDataContractLoader']