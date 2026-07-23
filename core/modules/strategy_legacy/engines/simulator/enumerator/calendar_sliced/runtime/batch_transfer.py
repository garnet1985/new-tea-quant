#!/usr/bin/env python3
"""StrategyJobContractBatch 跨进程序列化（仅 data rows，无 loader）。"""

from __future__ import annotations

import pickle
from typing import Any, Dict, List, Mapping

from core.modules.data_contract.contracts import ContractScope, DataKey
from core.modules.data_contract.contracts import DataContract
from core.modules.data_contract.contracts import ContractMeta
from core.modules.data_contract.contracts import IssueResult
from core.modules.strategy.services.data.injection.job_contract_batch import (
    StrategyJobContractBatch,
)


def _contract_to_row(contract: DataContract) -> Dict[str, Any]:
    meta = contract.meta
    return {
        "data_id": meta.data_id.value,
        "name": meta.name,
        "scope": meta.scope.value if hasattr(meta.scope, "value") else str(meta.scope),
        "display_name": meta.display_name,
        "rows": list(contract.data or []),
    }


def _row_to_contract(row: Mapping[str, Any]) -> DataContract:
    scope_raw = str(row.get("scope") or ContractScope.PER_ENTITY.value)
    scope = ContractScope(scope_raw)
    dk = DataKey(str(row["data_id"]))
    meta = ContractMeta(
        data_id=dk,
        name=str(row.get("name") or dk.value),
        scope=scope,
        display_name=str(row.get("display_name") or ""),
    )
    return DataContract(meta=meta, loader=None, data=list(row.get("rows") or []))


def batch_to_transfer(batch: StrategyJobContractBatch) -> Dict[str, Any]:
    global_rows: List[Dict[str, Any]] = []
    for contract in batch.global_contracts.values():
        global_rows.append(_contract_to_row(contract))

    per_entity_rows: List[Dict[str, Any]] = []
    for dk, result in batch.per_entity_results.items():
        entities: Dict[str, List[Dict[str, Any]]] = {}
        if result.by_entity:
            for eid, contract in result.by_entity.items():
                entities[str(eid)] = list(contract.data or [])
        sample = next(iter(result.by_entity.values())) if result.by_entity else None
        meta = sample.meta if sample is not None else ContractMeta(
            data_id=dk,
            name=dk.value,
            scope=ContractScope.PER_ENTITY,
        )
        per_entity_rows.append(
            {
                "data_id": meta.data_id.value,
                "name": meta.name,
                "scope": meta.scope.value,
                "display_name": meta.display_name,
                "entities": entities,
            }
        )

    return {"global": global_rows, "per_entity": per_entity_rows}


def transfer_to_batch(transfer: Dict[str, Any]) -> StrategyJobContractBatch:
    batch = StrategyJobContractBatch()
    for row in transfer.get("global") or []:
        if not isinstance(row, dict):
            continue
        contract = _row_to_contract(row)
        batch.global_contracts[contract.meta.data_id] = contract

    for row in transfer.get("per_entity") or []:
        if not isinstance(row, dict):
            continue
        dk = DataKey(str(row["data_id"]))
        scope = ContractScope(str(row.get("scope") or ContractScope.PER_ENTITY.value))
        by_entity: Dict[str, DataContract] = {}
        entities = row.get("entities") if isinstance(row.get("entities"), dict) else {}
        for eid, rows in entities.items():
            meta = ContractMeta(
                data_id=dk,
                name=str(row.get("name") or dk.value),
                scope=scope,
                display_name=str(row.get("display_name") or ""),
            )
            by_entity[str(eid)] = DataContract(meta=meta, loader=None, data=list(rows or []))
        batch.per_entity_results[dk] = IssueResult(
            data_id=dk,
            scope=scope,
            by_entity=by_entity,
        )
    return batch


def estimate_transfer_payload_bytes(transfer: Dict[str, Any]) -> int:
    """跨进程序列化体积粗估（pickle），用于 preload 内存预算而非 job-tree RSS。"""
    try:
        return max(0, len(pickle.dumps(transfer, protocol=pickle.HIGHEST_PROTOCOL)))
    except Exception:
        return 0


__all__ = ["batch_to_transfer", "estimate_transfer_payload_bytes", "transfer_to_batch"]
