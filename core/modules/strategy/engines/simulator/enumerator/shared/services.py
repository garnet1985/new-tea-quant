#!/usr/bin/env python3
"""枚举器 shared 服务：指纹、聚合、metadata、job 调度（两 flow 共用）。"""

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

from core.infra.project_context import ProjectContext

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
from core.modules.strategy.engines.simulator.enumerator.shared.settings import (
    EnumeratorSettings,
)
from core.modules.strategy.engines.simulator.enumerator.shared.report import (
    EnumeratorReport,
)
from core.modules.strategy.engines.simulator.enumerator.shared.materialize import (
    materialize_enum_report,
)
from core.modules.strategy.launcher.run_types import (
    StrategyRunFingerprint,
)
from core.modules.strategy.engines.simulator.enumerator.stock_based.worker import StockBasedEnumeratorWorker
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
    """Workbench 进度：由 JobPipeline on_result 转成旧版 on_job_done payload。"""

    __slots__ = ("strategy_name", "run_id")

    def __init__(self, strategy_name: str, run_id: str) -> None:
        self.strategy_name = strategy_name
        self.run_id = run_id

    def __call__(self, payload: Dict[str, Any]) -> None:
        from core.modules.strategy.execution_manager.workbench_run_envelope import (
            run_envelope_apply_step_stage,
        )
        from core.modules.strategy.engines.simulator.enumerator.shared.progress_cli import (
            publish_enumeration_execute_progress,
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

        sidecar_extra = {
            k: payload[k]
            for k in (
                "progress_axis",
                "entity_progress_mode",
                "calendar_progress_mode",
                "elapsed_seconds",
            )
            if payload.get(k) not in (None, "")
        }
        published_pct = publish_enumeration_execute_progress(
            strategy_name=self.strategy_name,
            run_id=self.run_id,
            done=done_jobs,
            total=max(1, total_jobs),
            sidecar_extra=sidecar_extra or None,
            update_envelope=False,
        )
        progress_pct = max(progress_pct, published_pct)

        prev_pct = progress_pct
        from core.modules.strategy.services.progress import ProgressRecorder

        recorder = ProgressRecorder.for_strategy_run_step(
            self.strategy_name, self.run_id, "enum"
        )
        prev = recorder.get_progress()
        if isinstance(prev, dict):
            try:
                prev_pct = int(prev.get("progress_pct") or 0)
            except (TypeError, ValueError):
                prev_pct = progress_pct
            progress_pct = max(prev_pct, progress_pct)

        counters = {"done": done_jobs, "total": total_jobs} if total_jobs > 0 else None
        run_envelope_apply_step_stage(
            self.strategy_name,
            self.run_id,
            "enum",
            "execute",
            float(progress_pct) / 100.0,
            counters=counters,
        )
        # 同步更新 ProgressRecorder（_merge_enum_progress_sidecar 的数据源）
        # 写入原始 job 完成百分比，由 _merge_enum_progress_sidecar 统一做加权
        from core.modules.strategy.services.progress import ProgressRecorder

        recorder = ProgressRecorder.for_strategy_run_step(
            self.strategy_name, self.run_id, "enum"
        )
        prev = recorder.get_progress()
        base = dict(prev) if isinstance(prev, dict) else {}
        base["phase"] = "running"
        base["progress_pct"] = int(progress_pct)
        if total_jobs > 0:
            base["done_jobs"] = done_jobs
            base["total_jobs"] = total_jobs
        recorder.record(base)
        # 同步写入 step 级别进度文件（GET /{step}/progress 直接读取的数据源，需要预加权）
        from core.modules.strategy.execution_manager.workbench_disk_progress import (
            disk_workbench_step_progress,
        )
        from core.modules.strategy.execution_manager.workbench_step_progress import (
            compute_step_progress_pct,
        )

        weighted_pct = compute_step_progress_pct("enum", "execute", float(progress_pct) / 100.0)
        disk_workbench_step_progress(
            self.strategy_name,
            self.run_id,
            "enum",
            weighted_pct,
            phase="running",
        )


class EnumeratorSharedServices:
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
        backtest_period: Optional[Dict[str, str]] = None,
    ) -> None:
        self.start_date = start_date
        self.end_date = end_date
        self.stock_list = stock_list
        self.max_workers = max_workers
        self.base_settings = base_settings
        self.workbench_strategy_name = workbench_strategy_name
        self.workbench_run_id = workbench_run_id
        self.force_refresh = bool(force_refresh)
        self._backtest_period_cache: Dict[str, str] = dict(backtest_period or {})
        # 在 ``aggregate_job_results``（postprocess）里单次遍历 ``job_results`` 填满；``save_metadata`` 再写 ``0_stock_ref.json``。
        self._stock_summary_by_id: Dict[str, Dict[str, Any]] = {}
        self._enumeration_bundles_by_id: Dict[str, Dict[str, Any]] = {}

    def resolved_backtest_period(self) -> Dict[str, str]:
        """单次 run 内缓存；构造时已注入则不再查库。"""
        cached = self._backtest_period_cache
        if cached.get("start_date") and cached.get("end_date"):
            return dict(cached)

        from core.modules.data_manager import DataManager
        from core.modules.strategy.engines.shared.helpers.backtest_date_resolve import (
            resolve_backtest_period_payload,
            resolve_latest_completed_trading_date,
        )

        data_mgr = DataManager(is_verbose=False)
        payload = resolve_backtest_period_payload(
            settings_view=self.base_settings,
            stock_ids=self.stock_list,
            data_manager=data_mgr,
            latest_completed_trading_date=resolve_latest_completed_trading_date(data_mgr),
            fallback_start_date=self.start_date,
            fallback_end_date=self.end_date,
        )
        self._backtest_period_cache = dict(payload)
        return payload

    def resolve_runtime_workers(self) -> int:
        from core.infra.job_pipeline.profile.probe import WorkerProbe

        return WorkerProbe.resolve(self.max_workers)

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
        worker_module_path, worker_class_name, worker_file_path = resolve_worker_ref(
            strategy_name, strategy_info=strategy_info
        )
        return {
            "worker_module_path": worker_module_path,
            "worker_class_name": worker_class_name,
            "worker_file_path": worker_file_path,
        }

    def parse_enum_settings(
        self, base_settings: StrategySettingsView
    ) -> EnumeratorSettings:
        return EnumeratorSettings.from_base(base_settings)

    def create_output_version(
        self,
        *,
        strategy_name: str,
        enum_settings: EnumeratorSettings,
        fingerprint: StrategyRunFingerprint,
    ) -> Dict[str, Any]:
        """创建或复用磁盘版本，避免指纹匹配时版本跳变。

        Args:
            strategy_name: 策略名称
            enum_settings: 枚举器设置
            fingerprint: 请求指纹（用于查询数据库中是否已有相同指纹的版本）

        Returns:
            版本信息字典，包含 output_dir, version_id, version_dir_name
        """
        from core.modules.strategy.services.cache.simulator_res_db_cache.snapshot_slot_adapters import (
            lookup_enum_cache,
        )
        from core.modules.strategy.services.data.output.version_manager import (
            StrategyOutputVersionService,
        )

        # 查询数据库中是否已有相同指纹的版本
        cached = lookup_enum_cache(
            strategy_name=strategy_name,
            settings_finger_print_id=fingerprint.settings_fingerprint_id,
            env_fingerprint_id=fingerprint.env_fingerprint_id,
        )

        if cached:
            # 找到缓存，检查磁盘目录是否存在
            _, cached_version_id = cached
            cached_version_dir, _ = StrategyOutputVersionService.resolve_enumerator_version(
                strategy_name=strategy_name,
                version_spec=str(cached_version_id),
            )
            if cached_version_dir.exists() and cached_version_dir.is_dir():
                # 磁盘目录存在，复用该版本
                return {
                    "output_dir": cached_version_dir,
                    "version_id": cached_version_id,
                    "version_dir_name": cached_version_dir.name,
                }

        # 缓存不存在或磁盘目录不存在，创建新版本
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
        disk_settings: Dict[str, Any],
        user_modified_settings: Dict[str, Any],
        stock_ids: List[str],
        worker_ref: Dict[str, str],
    ) -> StrategyRunFingerprint:
        """构建请求指纹（基于差异字段）。"""
        from core.modules.strategy.services.cache.simulator_res_db_cache.finger_print.settings_diff import (
            diff_and_filter,
        )
        from core.modules.strategy.services.cache.simulator_res_db_cache.config import (
            derive_run_mode,
        )
        from core.system import get_version

        # 计算差异字段
        settings_diff = diff_and_filter(disk_settings, user_modified_settings)

        # 获取 run_mode 和 engine_version
        run_mode = derive_run_mode(user_modified_settings)
        engine_version = get_version()

        worker_anchor = self._build_worker_anchor(worker_ref)
        data_contract_mapping = self._build_data_contract_mapping(user_modified_settings)
        return StrategyRunFingerprint.from_request(
            strategy_name=strategy_name,
            start_date=self.start_date,
            end_date=self.end_date,
            stock_ids=stock_ids,
            settings_diff=settings_diff,  # 差异字段
            run_mode=run_mode,
            engine_version=engine_version,
            worker_module_path=worker_ref.get("worker_module_path", ""),
            worker_class_name=worker_ref.get("worker_class_name", ""),
            worker_code_hash=worker_anchor["worker_code_hash"],
            data_contract_mapping=data_contract_mapping,
        )

    def _build_worker_anchor(self, worker_ref: Dict[str, str]) -> Dict[str, str]:
        worker_file_path = str(worker_ref.get("worker_file_path") or "").strip()
        worker_code_hash = ""
        if worker_file_path:
            try:
                worker_code_hash = self._hash_file(Path(worker_file_path))
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

        userspace_mapping_file = ProjectContext.path.get_data_contract_mapping_path()
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
        entities_per_job: int = 1,
    ) -> List[Dict[str, Any]]:
        from core.modules.strategy.engines.simulator.enumerator.stock_based.dispatch_jobs import (
            build_dispatch_jobs,
        )

        target_stock_ids = stock_ids if stock_ids is not None else self.stock_list
        return build_dispatch_jobs(
            strategy_name=strategy_name,
            settings_payload=settings_payload,
            output_dir=str(output_dir),
            worker_ref=worker_ref,
            stock_ids=target_stock_ids,
            start_date=self.start_date,
            end_date=self.end_date,
            entities_per_job=entities_per_job,
        )

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

    def resolve_enum_progress_total(self, jobs: List[Dict[str, Any]]) -> int:
        if jobs:
            if jobs[0].get("enumeration_execution_mode") == "calendar_slice":
                return int(jobs[0].get("calendar_progress_total") or 1)
            entity_total = jobs[0].get("entity_progress_total")
            if entity_total is not None:
                return max(1, int(entity_total))
        from core.modules.strategy.engines.simulator.enumerator.stock_based.dispatch_jobs import (
            count_stocks_in_dispatch_jobs,
        )

        return count_stocks_in_dispatch_jobs(jobs)

    def enumeration_progress_metadata(self, jobs: List[Dict[str, Any]]) -> Dict[str, Any]:
        from core.modules.strategy.engines.simulator.enumerator.shared.progress_axis import (
            enumeration_progress_metadata,
        )

        return enumeration_progress_metadata(jobs)

    def progress_units_from_execute_report(self, report: Any) -> tuple[int, int, int]:
        mode = getattr(self, "_entity_progress_mode", "stock")
        from core.modules.strategy.engines.simulator.enumerator.stock_based.progress import (
            entity_progress_units_from_execute_report,
        )

        return entity_progress_units_from_execute_report(report, progress_mode=mode)

    def run_jobs(
        self,
        *,
        jobs: List[Dict[str, Any]],
        global_extra_cache: Dict[str, List[Dict[str, Any]]],
        max_workers: int,
        enum_settings: EnumeratorSettings,
        duckdb_data_mgr: Any = None,
    ) -> List[Any]:
        from core.modules.strategy.services.execution import (
            run_enumeration_timeline_via_backtest_engine,
        )
        from core.modules.strategy.services.progress import ProgressRecorder

        self._entity_progress_mode = str(
            (jobs[0].get("entity_progress_mode") if jobs else None) or "stock"
        )
        total_stocks = self.resolve_enum_progress_total(jobs)

        on_job_done: Optional[Callable[[Dict[str, Any]], None]] = None
        if self.workbench_strategy_name and self.workbench_run_id:
            sn, rid = self.workbench_strategy_name, self.workbench_run_id
            recorder = ProgressRecorder.for_strategy_run_step(sn, rid, "enum")
            on_job_done = WorkbenchEnumeratorProgressCallback(sn, rid)
            total_n = total_stocks
            if total_n > 0:
                prev = recorder.get_progress()
                seed_pct = 1
                if isinstance(prev, dict):
                    try:
                        seed_pct = max(1, int(prev.get("progress_pct") or 0))
                    except (TypeError, ValueError):
                        seed_pct = 1
                recorder.record(
                    {
                        "strategy_name": sn,
                        "run_id": rid,
                        "step_name": "enum",
                        "phase": "running",
                        "done_jobs": 0,
                        "total_jobs": total_n,
                        "progress_pct": seed_pct,
                        **self.enumeration_progress_metadata(jobs),
                    }
                )
                from core.modules.strategy.execution_manager.workbench_run_envelope import (
                    run_envelope_on_flow_progress,
                )

                run_envelope_on_flow_progress(sn, rid, "enum", float(seed_pct))

        run_name = "enum"
        if self.workbench_strategy_name:
            run_name = f"enum:{self.workbench_strategy_name}"

        if jobs and jobs[0].get("enumeration_execution_mode") != "calendar_slice":
            return run_enumeration_timeline_via_backtest_engine(
                entity_jobs=jobs,
                global_extra_cache=global_extra_cache,
                total_jobs=total_stocks,
                run_name=run_name,
                on_job_progress=on_job_done,
                duckdb_data_mgr=duckdb_data_mgr,
                progress_units_from_report=self.progress_units_from_execute_report,
            )

        from core.modules.strategy.services.execution.enum_job_pipeline import (
            calendar_progress_units_from_execute_report,
            run_enumeration_sliced_via_backtest_engine,
        )

        poll_stop = None
        poll_thread = None
        if jobs:
            import threading

            poll_stop = threading.Event()
            poll_thread = threading.Thread(
                target=self._poll_calendar_enumeration_progress,
                args=(jobs[0], poll_stop),
                daemon=True,
            )
            poll_thread.start()

        try:
            return run_enumeration_sliced_via_backtest_engine(
                dispatch_jobs=jobs,
                global_extra_cache=global_extra_cache,
                total_jobs=total_stocks,
                run_name=run_name,
                on_job_progress=on_job_done,
                duckdb_data_mgr=duckdb_data_mgr,
                progress_units_from_report=calendar_progress_units_from_execute_report,
            )
        finally:
            if poll_stop is not None:
                poll_stop.set()
            if poll_thread is not None:
                poll_thread.join(timeout=2.0)

    @staticmethod
    def _poll_calendar_enumeration_progress(
        job: Dict[str, Any],
        stop_event: Any,
    ) -> None:
        """主进程轮询侧车：CLI 终端输出 + 信封同步（子进程写入侧车）。"""
        import time

        from core.modules.strategy.engines.simulator.enumerator.shared.progress_cli import (
            print_enumeration_progress_line,
            publish_enumeration_execute_progress,
        )
        from core.modules.strategy.services.progress import ProgressRecorder

        sn = str(job.get("workbench_strategy_name") or "").strip()
        rid = str(job.get("workbench_run_id") or "").strip()
        if not sn or not rid:
            return

        rec = ProgressRecorder.for_strategy_run_step(sn, rid, "enum")
        last_print_pct = -1
        last_plan_sig = ""
        poll_started_at = time.time()

        def _emit_from_sidecar() -> None:
            nonlocal last_print_pct, last_plan_sig
            sidecar = rec.get_progress()
            if not isinstance(sidecar, dict):
                return
            plan = sidecar.get("calendar_slice_runtime_plan")
            if isinstance(plan, dict):
                import json

                sig = json.dumps(plan, sort_keys=True, default=str)
                if sig != last_plan_sig:
                    from core.modules.strategy.engines.simulator.enumerator.shared.progress_cli import (
                        print_calendar_slice_plan_line,
                    )

                    print_calendar_slice_plan_line(plan)
                    last_plan_sig = sig
            try:
                done = int(sidecar.get("done_jobs") or 0)
                total = int(sidecar.get("total_jobs") or 0)
                pct = int(sidecar.get("progress_pct") or 0)
                elapsed_raw = sidecar.get("elapsed_seconds")
                elapsed = (
                    float(elapsed_raw)
                    if elapsed_raw is not None
                    else max(0.0, time.time() - poll_started_at)
                )
            except (TypeError, ValueError):
                return
            if total <= 0:
                return
            publish_enumeration_execute_progress(
                strategy_name=sn,
                run_id=rid,
                done=done,
                total=total,
                sidecar_extra={
                    k: sidecar[k]
                    for k in (
                        "progress_axis",
                        "calendar_progress_mode",
                        "elapsed_seconds",
                        "calendar_as_of_date",
                        "calendar_slice_id",
                        "calendar_slice_runtime_plan",
                    )
                    if sidecar.get(k) not in (None, "")
                },
            )
            if pct - last_print_pct >= 5 or last_print_pct < 0 or (pct >= 100 and last_print_pct < 100):
                last_print_pct = print_enumeration_progress_line(
                    progress_pct=pct,
                    done=done,
                    total=total,
                    last_printed_pct=last_print_pct,
                    elapsed_seconds=elapsed,
                )

        while not stop_event.wait(1.5):
            _emit_from_sidecar()
        if last_print_pct < 100:
            _emit_from_sidecar()

    def _run_scheduled_batches(
        self,
        *,
        jobs: List[Dict[str, Any]],
        global_extra_cache: Dict[str, List[Dict[str, Any]]],
        scheduler: Any,
        max_workers: int,
        total_stocks: int,
        run_name: str,
        on_job_progress: Optional[Callable[[Dict[str, Any]], None]],
        run_fn: Any,
        duckdb_data_mgr: Any = None,
    ) -> List[Any]:
        from core.modules.strategy.services.execution.enum_job_pipeline import (
            count_progress_units_from_job_result,
        )

        job_results: List[Any] = []
        finished_stocks = 0
        cumulative_ok = 0
        cumulative_fail = 0
        for batch in scheduler.iter_batches():
            batch_results = run_fn(
                stock_jobs=batch,
                global_extra_cache=global_extra_cache,
                max_workers=max_workers,
                total_jobs=total_stocks,
                finished_offset=finished_stocks,
                completed_offset=cumulative_ok,
                failed_offset=cumulative_fail,
                run_name=run_name,
                on_job_progress=on_job_progress,
                duckdb_data_mgr=duckdb_data_mgr,
                progress_units_from_report=self.progress_units_from_execute_report,
            )
            batch_finished = 0
            for jr in batch_results:
                ok_n, fail_n = count_progress_units_from_job_result(jr)
                cumulative_ok += ok_n
                cumulative_fail += fail_n
                batch_finished += ok_n + fail_n
            finished_stocks += batch_finished
            scheduler.update_after_batch(
                batch_size=len(batch),
                batch_results=batch_results,
                finished_jobs=finished_stocks,
            )
            job_results.extend(batch_results)
        return job_results

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
        from core.modules.strategy.services.execution.enum_job_pipeline import (
            expand_bulk_job_results,
        )

        # 预处理：提取 bulk job 的 performance_metrics（calendar_sliced 等模式）
        for jr in job_results:
            raw_result = getattr(jr, "result", None) or {}
            if isinstance(raw_result, dict) and raw_result.get("bulk"):
                perf_data = raw_result.get("performance_metrics")
                if perf_data and isinstance(perf_data, dict):
                    # calendar_sliced 模式：整个 job 的 performance_metrics
                    # 使用一个虚拟 stock_id 存储整体指标
                    try:
                        metrics = PerformanceMetrics.from_dict(perf_data)
                        aggregate_profiler.add_stock_metrics("__bulk__", metrics)
                    except Exception:
                        pass

        for job_result in expand_bulk_job_results(job_results):
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
        self._calendar_slice_runtime_plan = None
        for jr in job_results:
            raw = getattr(jr, "result", None)
            if (
                getattr(jr, "status", None)
                and jr.status.value == "completed"
                and isinstance(raw, dict)
                and raw.get("bulk")
            ):
                perf = raw.get("performance_metrics") or {}
                plan = perf.get("calendar_slice_runtime_plan")
                if isinstance(plan, dict):
                    self._calendar_slice_runtime_plan = plan
                    # 注入到 AggregateProfiler，使其出现在最终 report 中
                    aggregate_profiler.set_extra_data(calendar_slice_runtime_plan=plan)
                    break

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
        aggregate_profiler.print_report()

    def save_metadata(
        self,
        *,
        strategy_name: str,
        output_dir: Path,
        version_id: int,
        version_dir_name: str,
        settings_snapshot: Dict[str, Any],
        enum_settings: EnumeratorSettings,
        fingerprint: StrategyRunFingerprint,
        status: str = "completed",
        stock_summary_by_id: Optional[Dict[str, Dict[str, Any]]] = None,
        simulation_settings: Any = None,
    ) -> Optional[Dict[str, Any]]:
        summary_map = stock_summary_by_id if stock_summary_by_id is not None else self._stock_summary_by_id
        if summary_map:
            EnumeratorOutputWriterService.write_stock_summary_by_stock_id(
                output_dir=output_dir,
                by_stock_id=summary_map,
            )

        sim_effective = None
        if simulation_settings is not None:
            from core.modules.strategy.engines.shared.helpers.simulation_flow import (
                simulation_effective_snapshot,
            )

            sim_effective = simulation_effective_snapshot(simulation_settings)
        backtest_period = self.resolved_backtest_period()
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
            simulation_effective=sim_effective,
            backtest_period=backtest_period,
        )
        runtime_plan = getattr(self, "_calendar_slice_runtime_plan", None)
        if isinstance(runtime_plan, dict):
            metadata["calendar_slice_runtime_plan"] = runtime_plan
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
            if isinstance(bff_out, dict):
                bff_out["backtest_period"] = backtest_period
                if isinstance(runtime_plan, dict):
                    bff_out["calendar_slice_runtime_plan"] = runtime_plan
                with (output_dir / "0_report_enum.json").open("w", encoding="utf-8") as f:
                    json.dump(bff_out, f, indent=2, ensure_ascii=False)
        except Exception:
            bff_out = None
        return bff_out

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
            "output_version_id": version_id,
            "enumerator_output_dir": version_dir_name,
            "opportunities": total_opportunities,
            "totalStocks": total_stocks,
            "triggerStocks": int(trigger_stock_count),
            "completedCount": completed_count,
            "unfinishedCount": unfinished_count,
            "completionRate": completion_rate,
            "elapsed_seconds": time.time() - start_time,
        }
        bp = None
        if enum_bff_payload and isinstance(enum_bff_payload, dict):
            cand_bp = enum_bff_payload.get("backtest_period")
            if isinstance(cand_bp, dict) and cand_bp.get("start_date") and cand_bp.get("end_date"):
                bp = cand_bp
        if bp is None:
            bp = dict(self._backtest_period_cache)
        if isinstance(bp, dict) and bp.get("start_date") and bp.get("end_date"):
            summary["backtest_period"] = bp
        plan = getattr(self, "_calendar_slice_runtime_plan", None)
        if isinstance(plan, dict):
            summary["calendar_slice_runtime_plan"] = plan
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
        """单测 / 同步路径；并行枚举走 ``execute_enumeration_job``。"""
        return StockBasedEnumeratorWorker(payload).run()


__all__ = ["EnumeratorSharedServices"]
