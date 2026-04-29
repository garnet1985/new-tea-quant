#!/usr/bin/env python3
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union
from datetime import datetime
from pathlib import Path
import json
import logging
import time

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
from core.modules.strategy.engines.simulator.enumerator.worker import OpportunityEnumeratorWorker
from core.modules.strategy.engines.simulator.price_factor.helpers import DateTimeEncoder
from core.modules.strategy.services.data import StrategyDataInjectionService
from core.modules.strategy.services.data.output import VersionManager

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from core.modules.strategy.engines.shared.data_classes.discovered_strategy import (
        DiscoveredStrategy,
    )


class OpportunityEnumerator:
    @staticmethod
    def enumerate(
        strategy_name: str,
        start_date: str,
        end_date: str,
        stock_list: List[str],
        max_workers: Union[str, int] = "auto",
        base_settings: Optional[StrategySettingsView] = None,
        strategy_info: Optional["DiscoveredStrategy"] = None,
    ) -> List[Dict[str, Any]]:
        from core.infra.worker.multi_process.process_worker import ProcessWorker

        max_workers = ProcessWorker.resolve_max_workers(max_workers=max_workers, module_name="OpportunityEnumerator")
        start_time = time.time()
        aggregate_profiler = AggregateProfiler()
        if base_settings is None:
            base_settings = load_strategy_settings_view(
                strategy_name, strategy_info=strategy_info
            )
        worker_module_path, worker_class_name = resolve_worker_ref(
            strategy_name, strategy_info=strategy_info
        )
        enum_settings = OpportunityEnumeratorSettings.from_base(base_settings)
        validated_settings = enum_settings.to_dict()
        output_dir, version_id = VersionManager.create_enumerator_version(
            strategy_name=strategy_name, use_sampling=enum_settings.use_sampling
        )
        sub_dir = output_dir.parent
        version_dir_name = output_dir.name
        use_sampling = enum_settings.use_sampling
        from core.utils.date.date_utils import DateUtils

        enum_start_date = DateUtils.DEFAULT_START_DATE
        jobs = [
            {
                "stock_id": stock_id,
                "strategy_name": strategy_name,
                "settings": validated_settings,
                "start_date": enum_start_date,
                "end_date": end_date,
                "output_dir": str(output_dir),
                "worker_module_path": worker_module_path,
                "worker_class_name": worker_class_name,
            }
            for stock_id in stock_list
        ]
        global_extra_cache = (
            StrategyDataInjectionService.preload_global_extras_for_enumeration(
                validated_settings, enum_start_date, end_date
            )
        )
        from core.infra.worker import MemoryAwareScheduler, ProcessExecutionMode, ProcessExecutor

        executor = ProcessExecutor(
            max_workers=max_workers,
            execution_mode=ProcessExecutionMode.QUEUE,
            job_executor=OpportunityEnumerator._execute_single_job,
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
            process_jobs = []
            for job in batch:
                process_jobs.append(
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
                )
            batch_results = executor.run_jobs(process_jobs, total_jobs=total_jobs)
            finished_jobs += len(batch)
            scheduler.update_after_batch(batch_size=len(batch), batch_results=batch_results, finished_jobs=finished_jobs)
            job_results.extend(batch_results)
        executor.shutdown()
        total_opportunities = 0
        success_count = 0
        failed_count = 0
        for job_result in job_results:
            if job_result.status.value == "completed":
                result = job_result.result
                if result.get("success"):
                    success_count += 1
                    total_opportunities += int(result.get("opportunity_count", 0))
                    perf_data = result.get("performance_metrics")
                    if perf_data:
                        metrics = PerformanceMetrics.from_dict(perf_data)
                        aggregate_profiler.add_stock_metrics(result.get("stock_id"), metrics)
                else:
                    failed_count += 1
            else:
                failed_count += 1

        if success_count > 0:
            performance_summary = aggregate_profiler.get_summary()
            with (output_dir / "0_performance_report.json").open("w", encoding="utf-8") as f:
                json.dump(performance_summary, f, indent=2, ensure_ascii=False, cls=DateTimeEncoder)

        is_full_enumeration = not enum_settings.use_sampling
        OpportunityEnumerator._save_results(
            strategy_name=strategy_name,
            start_date=start_date,
            end_date=end_date,
            output_dir=output_dir,
            version_id=version_id,
            version_dir_name=version_dir_name,
            opportunity_count=total_opportunities,
            settings_snapshot=validated_settings,
            is_full_enumeration=is_full_enumeration,
        )
        if use_sampling:
            OpportunityEnumerator._cleanup_old_versions(sub_dir, enum_settings.max_test_versions, strategy_name, mode="test")
        else:
            OpportunityEnumerator._cleanup_old_versions(sub_dir, enum_settings.max_output_versions, strategy_name, mode="output")
        elapsed = time.time() - start_time
        return [
            {
                "strategy_name": strategy_name,
                "version_id": version_id,
                "version_dir": version_dir_name,
                "opportunity_count": total_opportunities,
                "success_stocks": success_count,
                "failed_stocks": failed_count,
                "total_stocks": success_count + failed_count,
                "elapsed_seconds": elapsed,
            }
        ]

    @staticmethod
    def _execute_single_job(payload: Dict[str, Any]) -> Dict[str, Any]:
        return OpportunityEnumeratorWorker(payload).run()

    @staticmethod
    def _save_results(
        strategy_name: str,
        start_date: str,
        end_date: str,
        output_dir: Path,
        version_id: int,
        version_dir_name: str,
        opportunity_count: int,
        settings_snapshot: Dict[str, Any],
        is_full_enumeration: bool = False,
    ):
        metadata = {
            "strategy_name": strategy_name,
            "start_date": start_date,
            "end_date": end_date,
            "opportunity_count": opportunity_count,
            "created_at": datetime.now().isoformat(),
            "version_id": version_id,
            "version_dir": version_dir_name,
            "settings_snapshot": settings_snapshot,
            "is_full_enumeration": is_full_enumeration,
        }
        with (output_dir / "0_metadata.json").open("w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False, cls=DateTimeEncoder)

    @staticmethod
    def _cleanup_old_versions(root_dir: Path, max_keep_versions: int, strategy_name: str, mode: str = "test"):
        if max_keep_versions < 1:
            return
        version_dirs = [item for item in root_dir.iterdir() if item.is_dir() and item.name != "__pycache__" and item.name[0].isdigit()]
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


__all__ = ["OpportunityEnumerator"]
