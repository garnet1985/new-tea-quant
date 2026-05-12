#!/usr/bin/env python3
"""Opportunity enumerator implementation details."""

from __future__ import annotations

from datetime import datetime
import hashlib
import importlib
import inspect
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Union
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
from core.modules.strategy.engines.simulator.enumerator.data_classes.report import (
    EnumeratorReport,
)
from core.modules.strategy.engines.simulator.enumerator.session_enum_stats import (
    materialize_enum_report,
)
from core.modules.strategy.launcher.run_types import (
    StrategyRunFingerprint,
)
from core.modules.strategy.engines.simulator.enumerator.worker import OpportunityEnumeratorWorker
from core.modules.strategy.services.data import StrategyDataInjectionService
from core.modules.strategy.services.data.output import (
    EnumeratorOutputWriterService,
    StrategyOutputVersionService,
)

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from core.modules.strategy.engines.shared.data_classes.discovered_strategy import (
        DiscoveredStrategy,
    )


class WorkbenchEnumeratorProgressCallback:
    """Pickle-safe ProcessWorker on_job_done hook (spawn multiprocessing cannot pickle nested functions)."""

    __slots__ = ("strategy_name", "run_id")

    def __init__(self, strategy_name: str, run_id: str) -> None:
        self.strategy_name = strategy_name
        self.run_id = run_id

    def __call__(self, payload: Dict[str, Any]) -> None:
        from core.modules.strategy.services.progress import ProgressRecorder

        recorder = ProgressRecorder.for_strategy_run_step(
            self.strategy_name, self.run_id, "enum"
        )
        total_jobs = int(payload.get("total_jobs") or 0)
        done_jobs = (
            int(payload.get("completed_jobs") or 0)
            + int(payload.get("failed_jobs") or 0)
            + int(payload.get("cancelled_jobs") or 0)
        )
        progress_pct = int(payload.get("progress_pct") or 0)
        if total_jobs > 0:
            progress_pct = min(100, max(0, progress_pct))
        recorder.record(
            {
                "strategy_name": self.strategy_name,
                "run_id": self.run_id,
                "step_name": "enum",
                "phase": "running",
                "done_jobs": done_jobs,
                "total_jobs": total_jobs,
                "progress_pct": progress_pct,
            }
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
        workbench_strategy_name: Optional[str] = None,
        workbench_run_id: Optional[str] = None,
        force_refresh: bool = False,
    ) -> None:
        self.start_date = start_date
        self.end_date = end_date
        self.stock_list = stock_list
        self.max_workers = max_workers
        self.base_settings = base_settings
        self.workbench_strategy_name = workbench_strategy_name
        self.workbench_run_id = workbench_run_id
        self.force_refresh = bool(force_refresh)
        # 在 ``aggregate_job_results``（postprocess）里单次遍历 ``job_results`` 填满；``save_metadata`` 再写 ``0_stock_ref.json``。
        self._stock_summary_by_id: Dict[str, Dict[str, Any]] = {}
        self._enumeration_bundles_by_id: Dict[str, Dict[str, Any]] = {}

    def resolve_runtime_workers(self) -> int:
        from core.infra.worker import ProcessWorker

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
        output_dir, version_id = StrategyOutputVersionService.create_enumerator_version(
            strategy_name=strategy_name,
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
        settings_payload: Dict[str, Any],
        stock_ids: List[str],
        worker_ref: Dict[str, str],
    ) -> StrategyRunFingerprint:
        worker_anchor = self._build_worker_anchor(worker_ref)
        data_contract_mapping = self._build_data_contract_mapping(settings_payload)
        return StrategyRunFingerprint.from_request(
            strategy_name=strategy_name,
            start_date=self.start_date,
            end_date=self.end_date,
            stock_ids=stock_ids,
            raw_settings=settings_payload,
            worker_module_path=worker_ref.get("worker_module_path", ""),
            worker_class_name=worker_ref.get("worker_class_name", ""),
            worker_code_hash=worker_anchor["worker_code_hash"],
            data_contract_mapping=data_contract_mapping,
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

    def _build_data_contract_mapping(
        self, settings_payload: Dict[str, Any]
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
            "settings_data_block": (settings_payload or {}).get("data") or {},
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
        settings_payload: Dict[str, Any],
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
                "settings": settings_payload,
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
        self, settings_payload: Dict[str, Any], jobs: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        if not jobs:
            return {}
        return StrategyDataInjectionService.preload_global_extras_for_enumeration(
            settings_payload,
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
        from core.modules.strategy.services.progress import ProgressRecorder

        on_job_done: Optional[Callable[[Dict[str, Any]], None]] = None
        if self.workbench_strategy_name and self.workbench_run_id:
            sn, rid = self.workbench_strategy_name, self.workbench_run_id
            recorder = ProgressRecorder.for_strategy_run_step(sn, rid, "enum")
            on_job_done = WorkbenchEnumeratorProgressCallback(sn, rid)
            total_n = len(jobs)
            if total_n > 0:
                recorder.record(
                    {
                        "strategy_name": sn,
                        "run_id": rid,
                        "step_name": "enum",
                        "phase": "running",
                        "done_jobs": 0,
                        "total_jobs": total_n,
                        "progress_pct": 0,
                    }
                )

        # step1: create process executor and scheduler
        executor = ProcessExecutor(
            max_workers=max_workers,
            execution_mode=ProcessExecutionMode.QUEUE,
            job_executor=self._execute_single_job,
            on_job_done=on_job_done,
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
        # step2: run jobs batch-by-batch and collect raw job results
        job_results = self._run_scheduled_batches(
            jobs=jobs,
            global_extra_cache=global_extra_cache,
            scheduler=scheduler,
            executor=executor,
        )
        executor.shutdown()
        return job_results

    def _run_scheduled_batches(
        self,
        *,
        jobs: List[Dict[str, Any]],
        global_extra_cache: Dict[str, List[Dict[str, Any]]],
        scheduler: Any,
        executor: Any,
    ) -> List[Any]:
        total_jobs = len(jobs)
        job_results = []
        finished_jobs = 0
        for batch in scheduler.iter_batches():
            process_jobs = self._build_process_jobs(batch, global_extra_cache)
            batch_results = executor.run_jobs(process_jobs, total_jobs=total_jobs)
            finished_jobs += len(batch)
            scheduler.update_after_batch(
                batch_size=len(batch),
                batch_results=batch_results,
                finished_jobs=finished_jobs,
            )
            job_results.extend(batch_results)
        return job_results

    @staticmethod
    def _build_process_jobs(
        batch: List[Dict[str, Any]],
        global_extra_cache: Dict[str, List[Dict[str, Any]]],
    ) -> List[Dict[str, Any]]:
        return [
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

    def aggregate_job_results(
        self,
        *,
        job_results: List[Any],
        aggregate_profiler: AggregateProfiler,
    ) -> Dict[str, Any]:
        # step1: aggregate result counts and performance metrics
        total_opportunities = 0
        success_count = 0
        failed_count = 0
        success_stock_ids: List[str] = []
        failed_stock_ids: List[str] = []
        trigger_stock_count = 0
        completed_count = 0
        unfinished_count = 0
        stock_summary_by_id: Dict[str, Dict[str, Any]] = {}
        bundles_by_id: Dict[str, Dict[str, Any]] = {}
        for job_result in job_results:
            row = self._aggregate_single_job_result(job_result, aggregate_profiler)
            total_opportunities += row["opportunity_count"]
            completed_count += row["completed_count"]
            unfinished_count += row["unfinished_count"]
            sid = str(row.get("stock_id") or "").strip()
            raw_res = getattr(job_result, "result", None)
            if sid and isinstance(raw_res, dict):
                eb = raw_res.get("enumeration_report_bundle")
                if isinstance(eb, dict):
                    bundles_by_id[sid] = eb
            if sid:
                stock_summary_by_id[sid] = {
                    "stock_name": str(row.get("stock_name") or sid),
                    "opportunities": int(row.get("opportunity_count") or 0),
                    "completion_rate": float(row.get("completion_rate") or 0.0),
                    "avg_opportunity_interval_days": float(row.get("avg_opportunity_interval_days") or 0.0),
                }
            if row["success"]:
                success_count += 1
                success_stock_ids.append(row["stock_id"])
                if row["opportunity_count"] > 0:
                    trigger_stock_count += 1
            else:
                failed_count += 1
                failed_stock_ids.append(row["stock_id"])

        self._stock_summary_by_id = stock_summary_by_id
        self._enumeration_bundles_by_id = bundles_by_id

        # step2: normalize and return aggregate summary
        return {
            "total_opportunities": total_opportunities,
            "success_count": success_count,
            "failed_count": failed_count,
            "trigger_stock_count": trigger_stock_count,
            "completed_count": completed_count,
            "unfinished_count": unfinished_count,
            "success_stock_ids": [s for s in success_stock_ids if s],
            "failed_stock_ids": [s for s in failed_stock_ids if s],
        }

    @staticmethod
    def _aggregate_single_job_result(
        job_result: Any, aggregate_profiler: AggregateProfiler
    ) -> Dict[str, Any]:
        if job_result.status.value != "completed":
            jid = str(getattr(job_result, "job_id", ""))
            return {
                "success": False,
                "stock_id": jid,
                "stock_name": jid,
                "opportunity_count": 0,
                "completed_count": 0,
                "unfinished_count": 0,
                "completion_rate": 0.0,
                "avg_opportunity_interval_days": 0.0,
            }
        result = job_result.result or {}
        stock_id = str(result.get("stock_id", ""))
        if not result.get("success"):
            return {
                "success": False,
                "stock_id": stock_id,
                "stock_name": str(result.get("stock_name") or stock_id),
                "opportunity_count": 0,
                "completed_count": 0,
                "unfinished_count": 0,
                "completion_rate": 0.0,
                "avg_opportunity_interval_days": 0.0,
            }
        perf_data = result.get("performance_metrics")
        if perf_data:
            metrics = PerformanceMetrics.from_dict(perf_data)
            aggregate_profiler.add_stock_metrics(result.get("stock_id"), metrics)
        return {
            "success": True,
            "stock_id": stock_id,
            "stock_name": str(result.get("stock_name") or stock_id),
            "opportunity_count": int(result.get("opportunity_count", 0)),
            "completed_count": int(result.get("completed_count", 0)),
            "unfinished_count": int(result.get("unfinished_count", 0)),
            "completion_rate": float(result.get("completion_rate") or 0.0),
            "avg_opportunity_interval_days": float(result.get("avg_opportunity_interval_days") or 0.0),
        }

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
        EnumeratorOutputWriterService.write_performance_report(
            output_dir=output_dir,
            performance_summary=performance_summary,
        )

    def save_metadata(
        self,
        *,
        strategy_name: str,
        output_dir: Path,
        version_id: int,
        version_dir_name: str,
        settings_snapshot: Dict[str, Any],
        enum_settings: OpportunityEnumeratorSettings,
        fingerprint: StrategyRunFingerprint,
        status: str = "completed",
        stock_summary_by_id: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> Optional[Dict[str, Any]]:
        summary_map = stock_summary_by_id if stock_summary_by_id is not None else self._stock_summary_by_id
        if summary_map:
            EnumeratorOutputWriterService.write_stock_summary_by_stock_id(
                output_dir=output_dir,
                by_stock_id=summary_map,
            )

        metadata, _scope_unused = EnumeratorOutputWriterService.build_metadata(
            strategy_name=str(strategy_name),
            start_date=self.start_date,
            end_date=self.end_date,
            version_id=version_id,
            version_dir_name=version_dir_name,
            settings_snapshot=settings_snapshot,
            is_full_enumeration=not enum_settings.use_sampling,
            fingerprint=fingerprint,
            status=status,
            created_at=datetime.now().isoformat(),
        )
        EnumeratorOutputWriterService.write_metadata(
            output_dir=output_dir, metadata=metadata
        )

        bff_out: Optional[Dict[str, Any]] = None
        try:
            report = materialize_enum_report(
                bundles_by_stock=self._enumeration_bundles_by_id,
                stock_universe=list(self.stock_list),
                output_dir=output_dir,
            )
            bff_out = report.to_bff_payload(include_stock_rows=False)
            report.write_bff_payload(output_dir, include_stock_rows=False)
        except Exception:
            bff_out = None
        return bff_out

    def cleanup_versions(
        self,
        *,
        output_dir: Path,
        strategy_name: str,
        enum_settings: OpportunityEnumeratorSettings,
    ) -> None:
        sub_dir = output_dir.parent
        StrategyOutputVersionService.prune_enumerator_versions(
            sub_dir, enum_settings.max_output_versions
        )

    def build_result_report(
        self,
        *,
        strategy_name: str,
        version_id: int,
        version_dir_name: str,
        total_opportunities: int,
        success_count: int,
        failed_count: int,
        trigger_stock_count: int,
        completed_count: int,
        unfinished_count: int,
        start_time: float,
        output_dir: Optional[Path] = None,
        enum_bff_payload: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        total_stocks = success_count + failed_count
        completion_rate = (
            (completed_count / total_opportunities) if total_opportunities > 0 else 0.0
        )
        summary: Dict[str, Any] = {
            "strategy_name": strategy_name,
            "version_id": version_id,
            "version_dir": version_dir_name,
            # 与 ``version_dir`` 同义；工作台 ``report_ref`` 查找优先使用该字段（枚举产物子目录名）
            "enumerator_output_dir": version_dir_name,
            "opportunities": total_opportunities,
            "totalStocks": total_stocks,
            "triggerStocks": int(trigger_stock_count),
            "completedCount": completed_count,
            "unfinishedCount": unfinished_count,
            "completionRate": completion_rate,
            "elapsed_seconds": time.time() - start_time,
        }
        # ``enumMetrics``：优先使用 ``save_metadata`` 里与落盘同源的内存 ``to_bff_payload``；
        # 再读 ``0_report_enum.json``，最后 ``EnumeratorReport.load`` 目录兜底。
        em: Optional[Dict[str, Any]] = None
        if enum_bff_payload and isinstance(enum_bff_payload, dict):
            cand = enum_bff_payload.get("enumMetrics")
            if isinstance(cand, dict) and cand:
                em = cand
        if em is None and output_dir is not None:
            raw_file = self._read_version_enum_report(output_dir)
            if isinstance(raw_file, dict):
                cand = raw_file.get("enumMetrics")
                if isinstance(cand, dict) and cand:
                    em = cand
            if em is None:
                try:
                    er = EnumeratorReport.load(output_dir)
                    bff = er.to_bff_payload()
                    cand = bff.get("enumMetrics") if isinstance(bff, dict) else None
                    if isinstance(cand, dict) and cand:
                        em = cand
                except Exception:
                    pass
        if isinstance(em, dict) and em:
            summary = {**summary, "enumMetrics": em}
        return [summary]

    @staticmethod
    def _read_version_metadata(version_dir: Path) -> Dict[str, Any]:
        metadata_path = version_dir / "0_metadata.json"
        if not metadata_path.exists():
            return {}
        try:
            with metadata_path.open("r", encoding="utf-8") as f:
                payload = json.load(f) or {}
            if isinstance(payload, dict):
                return payload
        except Exception:
            pass
        return {}

    @staticmethod
    def _read_version_enum_report(version_dir: Path) -> Dict[str, Any]:
        report_path = version_dir / "0_report_enum.json"
        if not report_path.exists():
            return {}
        try:
            with report_path.open("r", encoding="utf-8") as f:
                payload = json.load(f) or {}
            if isinstance(payload, dict):
                return payload
        except Exception:
            pass
        return {}

    @staticmethod
    def _execute_single_job(payload: Dict[str, Any]) -> Dict[str, Any]:
        return OpportunityEnumeratorWorker(payload).run()

__all__ = ["OpportunityEnumeratorFlowImpl"]
