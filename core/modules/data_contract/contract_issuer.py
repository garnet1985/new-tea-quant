from __future__ import annotations

from typing import Any, Mapping, Optional

from core.modules.data_contract.contract_const import ContractScope, ContractType, DataKey
from core.modules.data_contract.contracts import DataContract, NonTimeSeriesContract, TimeSeriesContract
from core.modules.data_contract.data_class.contract_meta import ContractMeta
from core.modules.data_contract.loaders import BaseLoader
from core.modules.data_contract.mapping import DataSpecMap


class ContractIssuer:
    """Issue contract handles from mapping specs."""

    def __init__(self, resolved_map: DataSpecMap):
        self.resolved_map = resolved_map

    def issue(
        self,
        data_id: DataKey,
        context: Optional[Mapping[str, Any]] = None,
        **override_params: Any,
    ) -> DataContract:
        if not self._is_key_exists(data_id):
            raise ValueError(f"未找到 data_id：{data_id.value}")

        contract = self._select_contract(data_id)
        contract = self._add_meta_info(contract, data_id)
        contract = self._inject_context(contract, context)
        contract = self._attach_loader(contract, data_id, override_params=override_params)
        return contract

    def _is_key_exists(self, data_id: DataKey) -> bool:
        return data_id in self.resolved_map

    def _select_contract(self, data_id: DataKey) -> DataContract:
        spec = self.resolved_map[data_id]
        contract_type = spec.get("type")
        scope = spec.get("scope")
        if scope is None:
            raise ValueError(f"data_id={data_id.value} 缺少 scope 配置")
        if not isinstance(scope, ContractScope):
            raise TypeError(f"data_id={data_id.value} 的 scope 类型错误：{type(scope)!r}")

        if contract_type == ContractType.TIME_SERIES:
            return TimeSeriesContract(
                meta=ContractMeta(data_id=data_id, name=data_id.value, scope=scope),
                time_axis_field=spec.get("time_axis_field", "date"),
                time_axis_format=spec.get("time_axis_format", "YYYYMMDD"),
                unique_keys=tuple(spec.get("unique_keys", [])),
            )
        if contract_type == ContractType.NON_TIME_SERIES:
            return NonTimeSeriesContract(
                meta=ContractMeta(data_id=data_id, name=data_id.value, scope=scope),
                unique_keys=tuple(spec.get("unique_keys", [])),
            )
        raise ValueError(f"data_id={data_id.value} 的 contract type 不支持：{contract_type!r}")

    def _add_meta_info(self, contract: DataContract, data_id: DataKey) -> DataContract:
        spec = self.resolved_map[data_id]
        meta_attrs: dict[str, Any] = {}
        for k in ("type", "unique_keys", "time_axis_field", "time_axis_format", "loader"):
            if k in spec:
                meta_attrs[k] = spec[k]

        contract.meta = ContractMeta(
            data_id=contract.meta.data_id,
            name=contract.meta.name,
            scope=contract.meta.scope,
            display_name=str(spec.get("display_name", contract.meta.display_name)),
            attrs=meta_attrs,
        )
        return contract

    def _inject_context(self, contract: DataContract, context: Optional[Mapping[str, Any]]) -> DataContract:
        base_context = dict(contract.context or {})
        if context:
            base_context.update(dict(context))
        contract.context = base_context or None
        return contract

    def _attach_loader(
        self,
        contract: DataContract,
        data_id: DataKey,
        override_params: Mapping[str, Any],
    ) -> DataContract:
        spec = self.resolved_map[data_id]
        loader_cls = spec.get("loader")
        if loader_cls is None:
            raise ValueError(f"data_id={data_id.value} 未配置 loader，无法完成签发")

        if not isinstance(loader_cls, type):
            raise TypeError(
                f"data_id={data_id.value} 的 loader 配置错误："
                f"期望 BaseLoader 子类，当前为 {type(loader_cls)!r}"
            )
        if not issubclass(loader_cls, BaseLoader):
            raise TypeError(f"data_id={data_id.value} 的 loader 必须继承 BaseLoader")

        try:
            loader_obj = loader_cls()
        except Exception as e:
            raise TypeError(f"data_id={data_id.value} 的 loader 无法实例化：{e}") from e

        if not isinstance(loader_obj, BaseLoader):
            raise TypeError(f"data_id={data_id.value} 的 loader 实例类型异常，必须为 BaseLoader")

        contract.loader = loader_obj
        defaults = dict(spec.get("defaults", {}))
        defaults.update(dict(override_params))
        contract.loader_params = defaults
        return contract
