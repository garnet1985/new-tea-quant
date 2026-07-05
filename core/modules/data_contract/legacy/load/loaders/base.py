from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Mapping, Optional, Sequence


class BaseLoader(ABC):
    """所有业务 loader 的抽象基类。"""

    @abstractmethod
    def load(self, params: Mapping[str, Any], context: Optional[Mapping[str, Any]] = None) -> Any:
        """
        单实体加载 - 必须实现。

        根据参数与上下文加载单个实体的数据。
        对于 PER_ENTITY scope 的数据源，此方法会被 ``load_batch`` 调用。
        """
        raise NotImplementedError

    @abstractmethod
    def load_batch(
        self,
        entity_ids: Sequence[str],
        params: Mapping[str, Any],
        context: Optional[Mapping[str, Any]] = None,
    ) -> Mapping[str, Any]:
        """
        批量加载多个实体数据 - **必须实现**（强制要求）。

        **重要**：此方法必须使用真正的批量查询（如 SQL WHERE IN），
        禁止在内部循环调用 ``self.load()`` 以避免性能问题。

        Args:
            entity_ids: 实体 ID 列表（如股票代码）
            params: 加载参数（包含 start/end 等）
            context: 可选上下文信息

        Returns:
            Dict[entity_id, data]: 每个实体对应的数据

        Raises:
            NotImplementedError: 如果子类未实现真正的批量查询逻辑
        """
        raise NotImplementedError("子类必须实现 load_batch() 以支持批量查询")

