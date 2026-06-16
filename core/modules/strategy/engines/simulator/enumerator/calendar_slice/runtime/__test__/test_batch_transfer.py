"""batch_transfer round-trip."""
from core.modules.data_contract.contract_const import ContractScope, DataKey
from core.modules.data_contract.contracts import DataContract
from core.modules.data_contract.data_class.contract_meta import ContractMeta
from core.modules.data_contract.data_class.issue_result import IssueResult
from core.modules.strategy.engines.simulator.enumerator.calendar_slice.runtime.batch_transfer import (
    batch_to_transfer,
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


def test_calendar_slice_runtime_settings_defaults():
    from core.modules.strategy.engines.simulator.enumerator.calendar_slice.runtime.settings import (
        CalendarSliceRuntimeSettings,
    )

    rt = CalendarSliceRuntimeSettings.from_job_payload({"settings": {"enumerator": {}}})
    assert rt.prefetch_enabled is True
    assert rt.reader_workers == 8  # auto default upper bound placeholder


def test_calendar_slice_runtime_settings_explicit():
    from core.modules.strategy.engines.simulator.enumerator.calendar_slice.runtime.settings import (
        CalendarSliceRuntimeSettings,
    )

    rt = CalendarSliceRuntimeSettings.from_job_payload(
        {
            "settings": {
                "enumerator": {
                    "calendar_slice": {"reader_workers": 2, "queue_depth": 2},
                }
            }
        }
    )
    assert rt.reader_workers == 2
    assert rt.queue_depth == 2


def test_calendar_slice_runtime_settings_prefetch_off_forces_single_reader():
    from core.modules.strategy.engines.simulator.enumerator.calendar_slice.runtime.settings import (
        CalendarSliceRuntimeSettings,
    )

    rt = CalendarSliceRuntimeSettings.from_job_payload(
        {
            "settings": {
                "enumerator": {
                    "calendar_slice": {
                        "queue_depth": 2,
                        "prefetch_enabled": False,
                        "reader_workers": 4,
                    },
                }
            }
        }
    )
    assert rt.prefetch_enabled is False
    assert rt.queue_depth == 1
    assert rt.reader_workers == 1
