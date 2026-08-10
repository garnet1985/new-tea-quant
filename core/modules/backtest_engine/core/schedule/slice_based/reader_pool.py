"""Slice reader pool (SOT: R readers + queue depth N).

- R == 0: sync load in the calling (compute) process.
- R  > 0: ProcessPoolExecutor readers; ready queue capped at N; concurrent
  loads capped at R. Compute process only takes ready / waits — never issues
  DuckDB loads on the main connection while the pool is live.
"""
from __future__ import annotations

import logging
import time
from collections import OrderedDict
from concurrent.futures import Future, ProcessPoolExecutor
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

LoadPerEntityWindowFn = Callable[..., Dict[str, Any]]


@dataclass(frozen=True)
class SliceWindowKey:
    start: str
    end: str

    def as_id(self) -> str:
        return f"{self.start}:{self.end}"


@dataclass
class SliceWindowResult:
    key: SliceWindowKey
    entity_contracts: Dict[str, Any]
    load_sec: float
    error: Optional[str] = None


class SliceReaderPool:
    """BE-owned per-slice loader with optional multiprocess prefetch."""

    def __init__(
        self,
        *,
        reader_workers: int,
        queue_depth: int,
        load_per_entity_window: Optional[LoadPerEntityWindowFn] = None,
    ) -> None:
        self.reader_workers = max(0, int(reader_workers))
        self.queue_depth = max(0, int(queue_depth))
        self._load_per_entity_window = load_per_entity_window
        self._executor: Optional[ProcessPoolExecutor] = None
        self._loading: Dict[str, Future] = {}
        self._ready: "OrderedDict[str, SliceWindowResult]" = OrderedDict()
        self._started = False
        self._shutdown = False

    @classmethod
    def from_plan(
        cls,
        plan: Any,
        *,
        load_per_entity_window: Optional[LoadPerEntityWindowFn] = None,
    ) -> "SliceReaderPool":
        return cls(
            reader_workers=int(getattr(plan, "reader_workers", 0) or 0),
            queue_depth=int(
                getattr(plan, "preload_depth", None)
                or getattr(plan, "queue_capacity", 0)
                or 0
            ),
            load_per_entity_window=load_per_entity_window,
        )

    def _require_loader(self) -> LoadPerEntityWindowFn:
        if self._load_per_entity_window is None:
            raise RuntimeError(
                "SliceReaderPool 未注入 load_per_entity_window "
                "(via RunCallbacks.load_per_entity_window)"
            )
        return self._load_per_entity_window

    @property
    def uses_process_pool(self) -> bool:
        return self.reader_workers > 0

    def set_queue_depth(self, depth: int) -> None:
        """Runtime N adjust (SOT §5). Width / R stay fixed."""
        self.queue_depth = max(0, int(depth))
        while self.queue_depth > 0 and len(self._ready) > self.queue_depth:
            self._ready.popitem(last=False)
        if self.queue_depth <= 0:
            self._ready.clear()
        logger.info(
            "SliceReaderPool queue_depth → %s (ready=%s loading=%s)",
            self.queue_depth,
            len(self._ready),
            len(self._loading),
        )

    @classmethod
    def refine_queue_from_samples(
        cls,
        pool: "SliceReaderPool",
        samples: List[Dict[str, Any]],
        *,
        budget_mb: float,
        mb_per_slice: Optional[float] = None,
    ) -> int:
        """Apply SOT §5 N from head/formal slice timings onto a live pool."""
        from core.modules.backtest_engine.core.schedule.slice_based.slice_width import (
            SliceMemoryPlanner,
        )

        if not samples:
            return pool.queue_depth
        loads = [float(s.get("load_sec") or 0.0) for s in samples]
        computes = [float(s.get("compute_sec") or 0.0) for s in samples]
        t_load = sum(loads) / max(len(loads), 1)
        t_compute = sum(computes) / max(len(computes), 1)
        payloads = [
            float(s.get("payload_mb") or 0.0)
            for s in samples
            if float(s.get("payload_mb") or 0.0) > 0.0
        ]
        per = (
            float(mb_per_slice)
            if mb_per_slice is not None
            else (sum(payloads) / len(payloads) if payloads else 1.0)
        )
        new_n = SliceMemoryPlanner.refine_queue_depth(
            budget_mb=budget_mb,
            mb_per_slice=max(per, 1e-6),
            reader_workers=pool.reader_workers,
            current_queue=pool.queue_depth,
            t_load_sec=t_load,
            t_compute_sec=t_compute,
        )
        pool.set_queue_depth(new_n)
        return new_n

    def start(self) -> None:
        if self._started or self._shutdown:
            return
        self._started = True
        if self.reader_workers <= 0:
            return
        self._executor = ProcessPoolExecutor(max_workers=self.reader_workers)
        logger.info(
            "SliceReaderPool started: readers=%s queue_depth=%s",
            self.reader_workers,
            self.queue_depth,
        )

    def shutdown(self) -> None:
        if self._shutdown:
            return
        self._shutdown = True
        for fut in list(self._loading.values()):
            fut.cancel()
        self._loading.clear()
        self._ready.clear()
        if self._executor is not None:
            self._executor.shutdown(wait=True, cancel_futures=True)
            self._executor = None
        logger.info("SliceReaderPool shutdown")

    @classmethod
    def payload_for_reader(cls, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Strip non-picklable / irrelevant fields before crossing to readers."""
        return {
            "entity_specified": list(payload.get("entity_specified") or []),
            "entity_ids": list(payload.get("entity_ids") or []),
            "entity_shared": dict(payload.get("entity_shared") or {}),
        }

    @staticmethod
    def window_key(start: str, end: str) -> SliceWindowKey:
        start_s = str(start or "").strip()
        end_s = str(end or "").strip()
        if start_s > end_s:
            start_s, end_s = end_s, start_s
        return SliceWindowKey(start=start_s, end=end_s)

    def load_window(
        self,
        payload: Dict[str, Any],
        *,
        start: str,
        end: str,
        perf: Any = None,
    ) -> Dict[str, Any]:
        """Blocking take of one window's ``entity_contracts``."""
        self.start()
        key = self.window_key(start, end)
        self._harvest()

        ready = self._ready.pop(key.as_id(), None)
        if ready is not None:
            if ready.error:
                raise RuntimeError(ready.error)
            if perf is not None and ready.load_sec > 0:
                # Approximate: attribute prefetched IO to this consume call.
                pass
            return ready.entity_contracts

        fut = self._loading.get(key.as_id())
        if fut is not None:
            result = self._await_future(key, fut)
            return result.entity_contracts

        if self._executor is None:
            return self._load_sync(payload, start=key.start, end=key.end, perf=perf)

        fut = self._submit(payload, key)
        result = self._await_future(key, fut)
        return result.entity_contracts

    def prefetch(
        self,
        payload: Dict[str, Any],
        *,
        start: str,
        end: str,
    ) -> bool:
        """Submit a window load if capacity allows. Returns True if submitted/queued."""
        if self.reader_workers <= 0 or self.queue_depth <= 0:
            return False
        self.start()
        if self._executor is None:
            return False

        self._harvest()
        key = self.window_key(start, end)
        kid = key.as_id()
        if kid in self._ready or kid in self._loading:
            return True
        if len(self._ready) >= self.queue_depth:
            return False
        if len(self._loading) >= self.reader_workers:
            return False

        self._submit(payload, key)
        return True

    def ready_count(self) -> int:
        self._harvest()
        return len(self._ready)

    def loading_count(self) -> int:
        """Number of reader tasks still loading (not yet in queue)."""
        self._harvest()
        return len(self._loading)

    def _submit(self, payload: Dict[str, Any], key: SliceWindowKey) -> Future:
        assert self._executor is not None
        reader_payload = self.payload_for_reader(payload)
        load_fn = self._require_loader()
        fut = self._executor.submit(
            SliceReaderPool._worker_load,
            reader_payload,
            key.start,
            key.end,
            load_fn,
        )
        self._loading[key.as_id()] = fut
        return fut

    def _await_future(self, key: SliceWindowKey, fut: Future) -> SliceWindowResult:
        try:
            raw = fut.result()
            result = self._result_from_raw(key, raw)
        except Exception as exc:
            result = SliceWindowResult(
                key=key,
                entity_contracts={},
                load_sec=0.0,
                error=f"slice reader failed for {key.as_id()}: {exc}",
            )
        self._loading.pop(key.as_id(), None)
        if result.error:
            raise RuntimeError(result.error)
        return result

    def _harvest(self) -> None:
        if self.queue_depth <= 0:
            return
        done_ids = [kid for kid, fut in self._loading.items() if fut.done()]
        for kid in done_ids:
            fut = self._loading.pop(kid)
            try:
                raw = fut.result()
                start, end = kid.split(":", 1)
                key = SliceWindowKey(start=start, end=end)
                result = self._result_from_raw(key, raw)
            except Exception as exc:
                start, end = kid.split(":", 1)
                result = SliceWindowResult(
                    key=SliceWindowKey(start=start, end=end),
                    entity_contracts={},
                    load_sec=0.0,
                    error=str(exc),
                )
            while len(self._ready) >= self.queue_depth:
                self._ready.popitem(last=False)
            self._ready[kid] = result

    @staticmethod
    def _result_from_raw(key: SliceWindowKey, raw: Any) -> SliceWindowResult:
        if not isinstance(raw, dict):
            return SliceWindowResult(
                key=key,
                entity_contracts={},
                load_sec=0.0,
                error=f"reader returned non-dict: {type(raw)!r}",
            )
        err = raw.get("error")
        if err:
            return SliceWindowResult(
                key=key,
                entity_contracts={},
                load_sec=float(raw.get("load_sec") or 0.0),
                error=str(err),
            )
        # Prefer pickle-safe wire format from workers.
        wire = raw.get("entity_contracts_wire")
        if isinstance(wire, dict):
            try:
                contracts = SliceReaderPool._contracts_from_wire(wire)
            except Exception as exc:
                return SliceWindowResult(
                    key=key,
                    entity_contracts={},
                    load_sec=float(raw.get("load_sec") or 0.0),
                    error=f"hydrate contracts failed: {exc}",
                )
        else:
            # Sync / legacy path may still pass live contract objects.
            contracts = raw.get("entity_contracts") or {}
            if not isinstance(contracts, dict):
                contracts = {}
        return SliceWindowResult(
            key=key,
            entity_contracts=contracts,
            load_sec=float(raw.get("load_sec") or 0.0),
            error=None,
        )

    @classmethod
    def _runtime_to_dict(cls, runtime: Any) -> Dict[str, Any]:
        if runtime is None:
            return {}
        from dataclasses import asdict, fields, is_dataclass

        if is_dataclass(runtime):
            try:
                return dict(asdict(runtime))
            except Exception:
                return {
                    f.name: getattr(runtime, f.name, None) for f in fields(runtime)
                }
        if isinstance(runtime, dict):
            return dict(runtime)
        return {}

    @classmethod
    def _contracts_to_wire(cls, contracts: Dict[str, Any]) -> Dict[str, Any]:
        """Strip Contract objects to pickle-safe {data, runtime} blobs."""
        wire: Dict[str, Any] = {}
        for data_key, contract in (contracts or {}).items():
            key = str(data_key)
            runtime = cls._runtime_to_dict(getattr(contract, "runtime", None))
            wire[key] = {
                "data": getattr(contract, "data", None),
                "runtime": runtime,
            }
        return wire

    @classmethod
    def _contracts_from_wire(cls, wire: Dict[str, Any]) -> Dict[str, Any]:
        """Rebuild Contract instances on the compute process from wire blobs."""
        from core.modules.data_contract import ContractIssuer

        out: Dict[str, Any] = {}
        for data_key, item in (wire or {}).items():
            if not isinstance(item, dict):
                continue
            runtime = dict(item.get("runtime") or {})
            entity_ids = runtime.pop("entity_ids", None)
            if entity_ids is None and "entity_ids" in (item.get("runtime") or {}):
                entity_ids = item["runtime"].get("entity_ids")
            contract = ContractIssuer.issue(
                str(data_key),
                entity_ids=entity_ids,
                runtime=runtime,
                fill_in_data=False,
            )
            contract.data = item.get("data")
            contract.is_loaded = contract.data is not None
            out[str(data_key)] = contract
        return out

    def _load_sync(
        self,
        payload: Dict[str, Any],
        *,
        start: str,
        end: str,
        perf: Any = None,
    ) -> Dict[str, Any]:
        return self._require_loader()(
            payload,
            start=start,
            end=end,
            perf=perf,
        )

    @staticmethod
    def _worker_load(
        payload: Dict[str, Any],
        start: str,
        end: str,
        load_per_entity_window: LoadPerEntityWindowFn,
    ) -> Dict[str, Any]:
        """Process-pool entry: bootstrap RO DataManager → load window → wire blob."""
        from core.modules.backtest_engine.core.shared.worker_data_runtime import (
            bootstrap_worker_data_manager,
        )

        bootstrap_worker_data_manager()
        t0 = time.perf_counter()
        try:
            contracts = load_per_entity_window(
                payload,
                start=start,
                end=end,
                perf=None,
            )
            return {
                # Never return live Contract objects — DynamicContractRuntime
                # is not picklable across processes.
                "entity_contracts_wire": SliceReaderPool._contracts_to_wire(contracts),
                "load_sec": max(0.0, time.perf_counter() - t0),
                "start": start,
                "end": end,
            }
        except Exception as exc:
            return {
                "entity_contracts_wire": {},
                "load_sec": max(0.0, time.perf_counter() - t0),
                "start": start,
                "end": end,
                "error": str(exc),
            }


__all__ = [
    "SliceReaderPool",
    "SliceWindowKey",
    "SliceWindowResult",
]
