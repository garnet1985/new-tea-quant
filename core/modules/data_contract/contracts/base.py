from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, MutableMapping, Optional

from core.modules.data_contract.data_class.contract_meta import ContractMeta
from core.modules.data_contract.loaders.base import BaseLoader


@dataclass
class DataContract:
    """Contract handle: carries meta, loader, and optional loaded data."""

    meta: ContractMeta
    loader: Optional[BaseLoader] = None
    context: Optional[Mapping[str, Any]] = None
    loader_params: MutableMapping[str, Any] = field(default_factory=dict)
    data: Any = None

    def get_meta(self) -> ContractMeta:
        return self.meta

    def load(self, **override_params: Any) -> Any:
        if self.loader is None:
            raise RuntimeError(f"contract={self.meta.data_id.value} 未绑定 loader，无法 load")
        params = dict(self.loader_params)
        params.update(override_params)
        self.data = self.loader.load(params=params, context=self.context)
        return self.data

    def validate_raw(self, raw: Any) -> Any:
        """
        主线优先占位：默认直接透传 raw，不阻塞 issue/load 链路。
        后续由子类补充严格校验。
        """
        return raw

    def clear(self) -> None:
        self.data = None
