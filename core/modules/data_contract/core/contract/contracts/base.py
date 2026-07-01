from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Mapping, MutableMapping, Optional

from core.modules.data_contract.core.contract.data_class.contract_meta import ContractMeta
from core.modules.data_contract.core.load.loaders.base import BaseLoader


@dataclass
class DataContract:
    """Contract handle: carries meta, loader, and optional loaded data."""

    meta: ContractMeta
    loader: Optional[BaseLoader] = None
    context: Optional[Mapping[str, Any]] = None
    loader_params: MutableMapping[str, Any] = field(default_factory=dict)
    data: Any = None
    _view_cursor: Any = field(default=None, init=False, repr=False, compare=False)

    @property
    def needs_load(self) -> bool:
        """
        ``True``：还没有数据，需要 ``load``（或等 DCM 写入 ``data``）。
        ``False``：已有结果；可能是正常数据，也可能是空列表 ``[]``（表示加载过但无行）。
        """
        return self.data is None

    def get_meta(self) -> ContractMeta:
        return self.meta

    def load(self, **override_params: Any) -> Any:
        if self.loader is None:
            raise RuntimeError(f"contract={self.meta.data_id.value} 未绑定 loader，无法 load")
        params = dict(self.loader_params)
        params.update(override_params)
        self.data = self.loader.load(params=params, context=self.context)
        self._view_cursor = None
        return self.data

    def until(self, as_of: str, *, time_field: Optional[str] = None) -> List[dict[str, Any]]:
        """
        返回截至 ``as_of``（含）的累计前缀行；时序源按时间轴单调推进，非时序源返回全量。

        委托 ``modules.data_cursor.DataCursor``；须先物化 ``data``。
        """
        if self.data is None:
            raise ValueError(
                f"contract={self.meta.data_id.value} 的 data 未加载，无法 until(as_of={as_of!r})"
            )
        cursor = self._ensure_view_cursor(time_field=time_field)
        key = self.meta.data_id
        return list(cursor.until(as_of)[key])

    def reset_view(self) -> None:
        """重置本 contract 的 as-of 游标（下次 ``until`` 从首行重新累计）。"""
        if self._view_cursor is not None:
            self._view_cursor.reset()

    def _ensure_view_cursor(self, *, time_field: Optional[str] = None) -> Any:
        from core.modules.data_cursor import DataCursor

        key = self.meta.data_id
        overrides = {key: time_field} if time_field is not None else None
        if self._view_cursor is None:
            self._view_cursor = DataCursor(
                contracts={key: self},
                time_field_overrides=overrides,
            )
        return self._view_cursor

    def validate_raw(self, raw: Any) -> Any:
        """
        主线优先占位：默认直接透传 raw，不阻塞 issue/load 链路。
        后续由子类补充严格校验。
        """
        return raw

    def clear(self) -> None:
        self.data = None
        self._view_cursor = None
