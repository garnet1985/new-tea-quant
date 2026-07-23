"""batch_transfer round-trip."""
from core.modules.data_contract.contracts import ContractScope, DataKey
from core.modules.data_contract.contracts import DataContract
from core.modules.data_contract.contracts import ContractMeta
from core.modules.data_contract.contracts import IssueResult
from core.modules.strategy.engines.simulator.enumerator.calendar_sliced.runtime.batch_transfer import (
    batch_to_transfer,
    estimate_transfer_payload_bytes,
    transfer_to_batch,
)
from core.modules.strategy.services.data.injection.job_contract_batch import (
    StrategyJobContractBatch,
)


def _sample_batch() -> StrategyJobContractBatch:
    batch = StrategyJobContractBatch()
    dk = DataKey.STOCK_KLINE_DAILY
    meta = ContractMeta(data_id=dk, name="klines", scope=ContractScope.PER_ENTITY)
    batch.per_entity_results[dk] = IssueResult(
        data_id=dk,
        scope=ContractScope.PER_ENTITY,
        by_entity={
            "000001.SZ": DataContract(
                meta=meta,
                data=[{"date": "20240101", "close": 10.0}],
            ),
            "000002.SZ": DataContract(
                meta=meta,
                data=[{"date": "20240101", "close": 20.0}],
            ),
        },
    )
    return batch


def test_batch_transfer_round_trip():
    original = _sample_batch()
    transfer = batch_to_transfer(original)
    restored = transfer_to_batch(transfer)
    c1 = restored.contracts_for_entity("000001.SZ")
    assert len(c1[DataKey.STOCK_KLINE_DAILY].data) == 1
    assert c1[DataKey.STOCK_KLINE_DAILY].data[0]["close"] == 10.0


def test_estimate_transfer_payload_bytes():
    transfer = batch_to_transfer(_sample_batch())
    nbytes = estimate_transfer_payload_bytes(transfer)
    assert nbytes > 0
