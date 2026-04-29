#!/usr/bin/env python3
"""Opportunity enumerator implementation details."""

from __future__ import annotations

from datetime import datetime
import hashlib
import importlib
import inspect
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union
import json
import logging
import time

from core.infra.project_context import PathManager
from core.modules.strategy.engines.shared.data_classes.strategy_settings.dict_view_settings import (
    StrategySettingsView,
)
from core.modules.strategy.engines.shared.helpers.strategy_runtime import (
    load_strategy_settings_view,
    resolve_worker_ref,
)
from core.modules.strategy.engines.shared.performance_profiler import (
    AggregateProfiler,
    PerformanceMetrics,
)
from core.modules.strategy.engines.simulator.enumerator.data_classes.settings import (
    OpportunityEnumeratorSettings,
)
from core.modules.strategy.engines.simulator.enumerator.data_classes.fingerprint import (
    EnumeratorFingerprint,
)
from core.modules.strategy.engines.simulator.enumerator.worker import OpportunityEnumeratorWorker
from core.modules.strategy.engines.simulator.price_factor.helpers import DateTimeEncoder
from core.modules.strategy.services.data import StrategyDataInjectionService
from core.modules.strategy.services.data.output import VersionManager

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from core.modules.strategy.engines.shared.data_classes.discovered_strategy import (
        DiscoveredStrategy,
    )


class OpportunityEnumeratorFlowImpl:
    def __init__(
        self,
        *,
        start_date: str,
        end_date: str,
        stock_list: List[str],
        max_workers: Union[str, int],
        base_settings: Optional[StrategySettingsView],
    ) -> None:
        self.start_date = start_date
        self.end_date = end_date
        self.stock_list = stock_list
        self.max_workers = max_workers
        self.base_settings = base_settings

    def resolve_runtime_workers(self) -> int:
        from core.infra.worker.multi_process.process_worker import ProcessWorker

        return ProcessWorker.resolve_max_workers(
            max_workers=self.max_workers, module_name="OpportunityEnumerator"
        )

    def load_settings(
        self,
        *,
        strategy_name: str,
        strategy_info: Optional["DiscoveredStrategy"],
    ) -> StrategySettingsView:
        if self.base_settings is not None:
            return self.base_settings
        return load_strategy_settings_view(strategy_name, strategy_info=strategy_info)

    def resolve_worker_blueprint(
        self,
        *,
        strategy_name: str,
        strategy_info: Optional["DiscoveredStrategy"],
    ) -> Dict[str, str]:
        worker_module_path, worker_class_name = resolve_worker_ref(
            strategy_name, strategy_info=strategy_info
        )
        return {
            "worker_module_path": worker_module_path,
            "worker_class_name": worker_class_name,
        }

    def parse_enum_settings(
        self, base_settings: StrategySettingsView
    ) -> OpportunityEnumeratorSettings:
        return OpportunityEnumeratorSettings.from_base(base_settings)

    def create_output_version(
        self, *, strategy_name: str, enum_settings: OpportunityEnumeratorSettings
    ) -> Dict[str, Any]:
        output_dir, version_id = VersionManager.create_enumerator_version(
            strategy_name=strategy_name, use_sampling=enum_settings.use_sampling
        )
        return {
            "output_dir": output_dir,
            "version_id": version_id,
            "version_dir_name": output_dir.name,
        }

    @staticmethod
    def version_info_from_dir(version_dir: Path) -> Dict[str, Any]:
        version_id = int(version_dir.name) if version_dir.name.isdigit() else 0
        return {
            "output_dir": version_dir,
            "version_id": version_id,
            "version_dir_name": version_dir.name,
        }

    def build_request_fingerprint(
        self,
        *,
        strategy_name: str,
        validated_settings: Dict[str, Any],
        stock_ids: List[str],
        worker_ref: Dict[str, str],
    ) -> EnumeratorFingerprint:
        worker_anchor = self._build_worker_anchor(worker_ref)
        data_contract_signature = self._build_data_contract_signature(validated_settings)
        return EnumeratorFingerprint.from_request(
            strategy_name=strategy_name,
            start_date=self.start_date,
            end_date=self.end_date,
            stock_ids=stock_ids,
            raw_settings=validated_settings,
            worker_module_path=worker_ref.get("worker_module_path", ""),
            worker_class_name=worker_ref.get("worker_class_name", ""),
            worker_code_hash=worker_anchor["worker_code_hash"],
            data_contract_signature=data_contract_signature,
        )

    def plan_reuse(
        self,
        *,
        strategy_name: str,
        enum_settings: OpportunityEnumeratorSettings,
        request_fingerprint: EnumeratorFingerprint,
    ) -> Dict[str, Any]:
        sub_dir = PathManager.strategy_opportunity_enums(
            strategy_name=strategy_name,
            use_sampling=enum_settings.use_sampling,
        )
        if not sub_dir.exists():
            return {
                "action": "REBUILD_ALL",
                "version_dir": None,
                "cached_fingerprint": None,
                "missing_stock_ids": request_fingerprint.stock_ids,
            }
        versions: List[Path] = [
            item
            for item in sub_dir.iterdir()
            if item.is_dir() and item.name and item.name[0].isdigit()
        ]
        versions.sort(key=lambda p: int(p.name), reverse=True)
        for version_dir in versions:
            metadata_path = version_dir / "0_metadata.json"
            if not metadata_path.exists():
                continue
            try:
                with metadata_path.open("r", encoding="utf-8") as f:
                    metadata = json.load(f) or {}
            except Exception:
                continue
            if metadata.get("status") != "completed":
                continue
            fingerprint_payload = metadata.get("fingerprint")
            if not isinstance(fingerprint_payload, dict):
                continue
            try:
                cached_fingerprint = EnumeratorFingerprint.from_dict(fingerprint_payload)
            except Exception:
                continue
            if cached_fingerprint.is_contain(request_fingerprint):
                return {
                    "action": "REUSE_FULL",
                    "version_dir": version_dir,
                    "cached_fingerprint": cached_fingerprint,
                    "missing_stock_ids": [],
                }
            if (
                self._is_reuse_compatible(cached_fingerprint, request_fingerprint)
                and cached_fingerprint.start_date <= request_fingerprint.start_date
                and cached_fingerprint.end_date >= request_fingerprint.end_date
            ):
                missing = cached_fingerprint.diff_stock_ids(request_fingerprint)
                if missing and len(missing) < len(request_fingerprint.stock_ids):
                    return {
                        "action": "RUN_DIFF_STOCKS",
                        "version_dir": version_dir,
                        "cached_fingerprint": cached_fingerprint,
                        "missing_stock_ids": missing,
                    }
        return {
            "action": "REBUILD_ALL",
            "version_dir": None,
            "cached_fingerprint": None,
            "missing_stock_ids": request_fingerprint.stock_ids,
        }

    @staticmethod
    def _is_reuse_compatible(
        cached: EnumeratorFingerprint, request: EnumeratorFingerprint
    ) -> bool:
        return (
            cached.settings_core == request.settings_core
            and cached.worker_module_path == request.worker_module_path
            and cached.worker_class_name == request.worker_class_name
            and cached.worker_code_hash == request.worker_code_hash
            and cached.data_contract_signature == request.data_contract_signature
        )

    def _build_worker_anchor(self, worker_ref: Dict[str, str]) -> Dict[str, str]:
        worker_module_path = str(worker_ref.get("worker_module_path", ""))
        worker_code_hash = ""
        if worker_module_path:
            try:
                module = importlib.import_module(worker_module_path)
                source_file = inspect.getsourcefile(module)
                if source_file:
                    worker_code_hash = self._hash_file(Path(source_file))
            except Exception:
                worker_code_hash = ""
        return {"worker_code_hash": worker_code_hash}

    def _build_data_contract_signature(
        self, validated_settings: Dict[str, Any]
    ) -> str:
        core_mapping_hash = ""
        userspace_mapping_hash = ""
        try:
            dc_mapping_module = importlib.import_module("core.modules.data_contract.mapping")
            dc_mapping_file = inspect.getsourcefile(dc_mapping_module)
            if dc_mapping_file:
                core_mapping_hash = self._hash_file(Path(dc_mapping_file))
        except Exception:
            core_mapping_hash = ""

        userspace_mapping_file = PathManager.data_contract_mapping()
        if userspace_mapping_file.exists():
            userspace_mapping_hash = self._hash_file(userspace_mapping_file)

        payload = {
            "settings_data_block": (validated_settings or {}).get("data") or {},
            "core_mapping_hash": core_mapping_hash,
            "userspace_mapping_hash": userspace_mapping_hash,
        }
        canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    @staticmethod
    def _hash_file(path: Path) -> str:
        if not path.exists() or not path.is_file():
            return ""
        hasher = hashlib.sha256()
        with path.open("rb") as f:
            while True:
                chunk = f.read(8192)
                if not chunk:
                    break
                hasher.update(chunk)
        return hasher.hexdigest()

    def build_jobs(
        self,
        *,
        strategy_name: str,
        validated_settings: Dict[str, Any],
        output_dir: Path,
        worker_ref: Dict[str, str],
        stock_ids: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        from core.utils.date.date_utils import DateUtils

        enum_start_date = DateUtils.DEFAULT_START_DATE
        target_stock_ids = stock_ids if stock_ids is not None else self.stock_list
        jobs = [
            {
                "stock_id": stock_id,
                "strategy_name": strategy_name,
                "settings": validated_settings,
                "start_date": enum_start_date,
                "end_date": self.end_date,
                "output_dir": str(output_dir),
                "worker_module_path": worker_ref["worker_module_path"],
                "worker_class_name": worker_ref["worker_class_name"],
            }
            for stock_id in target_stock_ids
        ]
        return jobs

    def preload_global_cache(
        self, validated_settings: Dict[str, Any], jobs: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        if not jobs:
            return {}
        return StrategyDataInjectionService.preload_global_extras_for_enumeration(
            validated_settings,
            jobs[0]["start_date"],
            self.end_date,
        )

    def create_runtime_context(self) -> Dict[str, Any]:
        return {
            "start_time": time.time(),
            "aggregate_profiler": AggregateProfiler(),
        }

    def run_jobs(
        self,
        *,
        jobs: List[Dict[str, Any]],
        global_extra_cache: Dict[str, List[Dict[str, Any]]],
        max_workers: int,
        enum_settings: OpportunityEnumeratorSettings,
    ) -> List[Any]:
        from core.infra.worker import (
            MemoryAwareScheduler,
            ProcessExecutionMode,
            ProcessExecutor,
        )

        executor = ProcessExecutor(
            max_workers=max_workers,
            execution_mode=ProcessExecutionMode.QUEUE,
            job_executor=self._execute_single_job,
            is_verbose=False,
        )
        scheduler = MemoryAwareScheduler(
            jobs=jobs,
            memory_budget_mb=enum_settings.memory_budget_mb,
            warmup_batch_size=enum_settings.warmup_batch_size,
            min_batch_size=enum_settings.min_batch_size,
            max_batch_size=enum_settings.max_batch_size,
            monitor_interval=enum_settings.monitor_interval,
            log=logger,
        )
        total_jobs = len(jobs)
        job_results = []
        finished_jobs = 0
        for batch in scheduler.iter_batches():
            process_jobs = [
                {
                    "id": job["stock_id"],
                    "data": {
                        "stock_id": job["stock_id"],
                        "strategy_name": job["strategy_name"],
                        "settings": job["settings"],
                        "start_date": job["start_date"],
                        "end_date": job["end_date"],
                        "output_dir": job["output_dir"],
                        "global_extra_cache": global_extra_cache,
                        "worker_module_path": job["worker_module_path"],
                        "worker_class_name": job["worker_class_name"],
                    },
                }
                for job in batch
            ]
            batch_results = executor.run_jobs(process_jobs, total_jobs=total_jobs)
            finished_jobs += len(batch)
            scheduler.update_after_batch(
                batch_size=len(batch),
                batch_results=batch_results,
                finished_jobs=finished_jobs,
            )
            job_results.extend(batch_results)
        executor.shutdown()
        return job_results

    def aggregate_job_results(
        self,
        *,
        job_results: List[Any],
        aggregate_profiler: AggregateProfiler,
    ) -> Dict[str, Any]:
        total_opportunities = 0
        success_count = 0
        failed_count = 0
        success_stock_ids: List[str] = []
        failed_stock_ids: List[str] = []
        for job_result in job_results:
            if job_result.status.value == "completed":
                result = job_result.result
                if result.get("success"):
                    success_count += 1
                    success_stock_ids.append(str(result.get("stock_id", "")))
                    total_opportunities += int(result.get("opportunity_count", 0))
                    perf_data = result.get("performance_metrics")
                    if perf_data:
                        metrics = PerformanceMetrics.from_dict(perf_data)
                        aggregate_profiler.add_stock_metrics(
                            result.get("stock_id"), metrics
                        )
                else:
                    failed_count += 1
                    failed_stock_ids.append(str(result.get("stock_id", "")))
            else:
                failed_count += 1
                failed_stock_ids.append(str(getattr(job_result, "job_id", "")))
        return {
            "total_opportunities": total_opportunities,
            "success_count": success_count,
            "failed_count": failed_count,
            "success_stock_ids": [s for s in success_stock_ids if s],
            "failed_stock_ids": [s for s in failed_stock_ids if s],
        }

    @staticmethod
    def merge_diff_fingerprint(
        *,
        cached_fingerprint: EnumeratorFingerprint,
        newly_successful_stock_ids: List[str],
    ) -> EnumeratorFingerprint:
        merged_stock_ids = sorted(
            set(cached_fingerprint.stock_ids).union(
                {str(s) for s in newly_successful_stock_ids if s}
            )
        )
        return EnumeratorFingerprint.from_request(
            strategy_name=cached_fingerprint.strategy_name,
            start_date=cached_fingerprint.start_date,
            end_date=cached_fingerprint.end_date,
            stock_ids=merged_stock_ids,
            raw_settings={
                "data": cached_fingerprint.settings_core.get("data") or {},
                "goal": cached_fingerprint.settings_core.get("goal") or {},
                "price_simulator": cached_fingerprint.settings_core.get("price_simulator")
                or {},
                "enumerator": cached_fingerprint.settings_core.get("enumerator") or {},
            },
            worker_module_path=cached_fingerprint.worker_module_path,
            worker_class_name=cached_fingerprint.worker_class_name,
            worker_code_hash=cached_fingerprint.worker_code_hash,
            data_contract_signature=cached_fingerprint.data_contract_signature,
        )

    def save_performance_report(
        self,
        *,
        output_dir: Path,
        success_count: int,
        aggregate_profiler: AggregateProfiler,
    ) -> None:
        if success_count <= 0:
            return
        performance_summary = aggregate_profiler.get_summary()
        with (output_dir / "0_performance_report.json").open("w", encoding="utf-8") as f:
            json.dump(
                performance_summary,
                f,
                indent=2,
                ensure_ascii=False,
                cls=DateTimeEncoder,
            )

    def save_metadata(
        self,
        *,
        strategy_name: str,
        output_dir: Path,
        version_id: int,
        version_dir_name: str,
        opportunity_count: int,
        settings_snapshot: Dict[str, Any],
        enum_settings: OpportunityEnumeratorSettings,
        fingerprint: EnumeratorFingerprint,
        status: str = "completed",
    ) -> None:
        metadata = {
            "strategy_name": strategy_name,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "opportunity_count": opportunity_count,
            "created_at": datetime.now().isoformat(),
            "version_id": version_id,
            "version_dir": version_dir_name,
            "settings_snapshot": settings_snapshot,
            "is_full_enumeration": not enum_settings.use_sampling,
            "fingerprint": fingerprint.to_dict(),
            "status": status,
        }
        with (output_dir / "0_metadata.json").open("w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False, cls=DateTimeEncoder)

    def build_reuse_summary(
        self,
        *,
        strategy_name: str,
        version_dir: Path,
        reuse_action: str,
    ) -> List[Dict[str, Any]]:
        version_id = int(version_dir.name) if version_dir.name.isdigit() else 0
        return [
            {
                "strategy_name": strategy_name,
                "version_id": version_id,
                "version_dir": version_dir.name,
                "opportunity_count": None,
                "success_stocks": len(self.stock_list),
                "failed_stocks": 0,
                "total_stocks": len(self.stock_list),
                "elapsed_seconds": 0.0,
                "reuse_action": reuse_action,
            }
        ]

    def cleanup_versions(
        self,
        *,
        output_dir: Path,
        strategy_name: str,
        enum_settings: OpportunityEnumeratorSettings,
    ) -> None:
        sub_dir = output_dir.parent
        if enum_settings.use_sampling:
            self._cleanup_old_versions(
                sub_dir, enum_settings.max_test_versions, strategy_name, mode="test"
            )
        else:
            self._cleanup_old_versions(
                sub_dir, enum_settings.max_output_versions, strategy_name, mode="output"
            )

    def build_result_summary(
        self,
        *,
        strategy_name: str,
        version_id: int,
        version_dir_name: str,
        total_opportunities: int,
        success_count: int,
        failed_count: int,
        start_time: float,
        reuse_action: Optional[str] = None,
        diff_stock_count: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        summary = {
            "strategy_name": strategy_name,
            "version_id": version_id,
            "version_dir": version_dir_name,
            "opportunity_count": total_opportunities,
            "success_stocks": success_count,
            "failed_stocks": failed_count,
            "total_stocks": success_count + failed_count,
            "elapsed_seconds": time.time() - start_time,
        }
        if reuse_action:
            summary["reuse_action"] = reuse_action
        if diff_stock_count is not None:
            summary["diff_stock_count"] = int(diff_stock_count)
        return [summary]

    @staticmethod
    def _execute_single_job(payload: Dict[str, Any]) -> Dict[str, Any]:
        return OpportunityEnumeratorWorker(payload).run()

    @staticmethod
    def _cleanup_old_versions(
        root_dir: Path, max_keep_versions: int, strategy_name: str, mode: str = "test"
    ) -> None:
        if max_keep_versions < 1:
            return
        version_dirs = [
            item
            for item in root_dir.iterdir()
            if item.is_dir() and item.name != "__pycache__" and item.name[0].isdigit()
        ]
        versions = []
        for version_dir in version_dirs:
            metadata_path = version_dir / "0_metadata.json"
            if not metadata_path.exists():
                try:
                    version_id = int(version_dir.name)
                except ValueError:
                    continue
            else:
                try:
                    with metadata_path.open("r", encoding="utf-8") as f:
                        version_id = int((json.load(f) or {}).get("version_id", 0))
                except Exception:
                    continue
            versions.append((version_id, version_dir))
        versions.sort(key=lambda x: x[0], reverse=True)
        for _, vdir in versions[max_keep_versions:]:
            try:
                import shutil

                shutil.rmtree(vdir)
            except Exception as exc:
                logger.warning("cleanup failed for %s: %s", vdir, exc)


__all__ = ["OpportunityEnumeratorFlowImpl"]
