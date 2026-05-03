"""Strategy workbench service orchestration layer."""

import multiprocessing as mp
from datetime import datetime

from core.infra.project_context.config_manager import ConfigManager
from core.infra.project_context.path_manager import PathManager
from core.modules.strategy.services.discovery import StrategyDiscoveryHelper
from core.ui.bff.shared.response import error, ok
from core.ui.bff.shared.file_ops import atomic_write_text, backup_file

from .implementation_helper import (
    StrategyWorkbenchImplementation,
    _strategy_workbench_run_chain_entry as _impl_run_chain_entry,
)
from .request_helper import StrategyWorkbenchRequestHelper


class StrategyWorkbenchService:
    """Route-facing orchestration service for strategy workbench."""

    def __init__(self):
        self._impl = StrategyWorkbenchImplementation()

    @staticmethod
    def normalize_strategy_name(strategy_name: str) -> str:
        return str(strategy_name or "").strip()

    @staticmethod
    def stringify(value: str) -> str:
        return str(value or "").strip()

    @staticmethod
    def to_response_format(discovered: dict) -> list:
        """Map discovery dict to `GET /v1/strategies` response rows (`strategies[]`)."""
        rows = []
        for _name, info in (discovered or {}).items():
            meta = getattr(info.settings, "meta", None)
            rows.append({
                "key": str(info.folder.name),
                "name": str(getattr(meta, "name", info.name)),
                "description": str(getattr(meta, "description", "") or ""),
                "is_enabled": bool(getattr(meta, "is_enabled", False)),
            })
        return rows

    @staticmethod
    def sort_discovered_strategies(rows: list) -> list:
        rows = list(rows or [])
        rows.sort(key=lambda x: x.get("key", ""))
        return rows

    @staticmethod
    def discover_strategies():
        return StrategyDiscoveryHelper.discover_strategies()

    @staticmethod
    def has_settings_snapshot(snapshot: dict) -> bool:
        return isinstance(snapshot, dict) and isinstance(snapshot.get("settings"), dict)

    def load_latest_settings_snapshot(self, strategy_name: str):
        return self._impl._get_snapshot_service().load_latest_settings_snapshot(strategy_name)

    def to_runtime_settings(self, snapshot: dict) -> dict:
        raw_settings = snapshot.get("settings") if isinstance(snapshot, dict) else {}
        return self._impl._canonicalize_api_settings(raw_settings)

    @staticmethod
    def ensure_strategy_settings_files(strategy_name: str):
        strategy_dir = PathManager.strategy(strategy_name)
        settings_file = PathManager.strategy_settings(strategy_name)
        if not strategy_dir.exists() or not strategy_dir.is_dir():
            return None, error(f"策略不存在: {strategy_name}", 404)
        if not settings_file.exists():
            return None, error(f"策略缺少 settings.py: {strategy_name}", 404)
        return settings_file, None

    def load_userspace_api_settings(self, strategy_name: str, settings_file):
        runtime_settings = ConfigManager.load_python(settings_file, var_name="settings")
        if not isinstance(runtime_settings, dict):
            return None, error(f"策略 settings 无效: {strategy_name}", 500)
        return self._impl._runtime_to_api_settings(runtime_settings), None

    @staticmethod
    def build_settings_response(
        strategy_name: str,
        settings: dict,
        settings_source: str,
        workbench_version_id: str,
    ):
        return ok({
            "strategy_name": strategy_name,
            "settings": settings,
            "settings_source": settings_source,
            "workbench_version_id": workbench_version_id or "",
        })

    @staticmethod
    def ensure_payload_object(payload: dict):
        if not isinstance(payload, dict):
            return None, error("请求体必须为对象", 400)
        return payload, None

    @staticmethod
    def extract_settings_from_payload(payload: dict):
        return payload.get("settings")

    def ensure_strategy_exists(self, strategy_name: str):
        if not self._impl._validate_strategy_exists(strategy_name):
            return error(f"策略不存在: {strategy_name}", 404)
        return None

    def to_original_formatted_settings(self, strategy_name: str, ui_formatted_settings):
        normalized, detail = self._impl._normalize_runtime_settings(strategy_name, ui_formatted_settings)
        if normalized is None:
            return None, error(detail or "settings 校验失败", 422)
        return normalized, None

    @staticmethod
    def resolve_userspace_settings_file(strategy_name: str):
        return PathManager.strategy_settings(strategy_name)

    @staticmethod
    def backup_userspace_settings_file(settings_file):
        backup_file(settings_file)

    def build_userspace_settings_file_content(
        self,
        original_formatted_settings: dict,
        *,
        pretty: bool,
    ) -> str:
        return self._impl._build_settings_file_text(original_formatted_settings, pretty=pretty)

    @staticmethod
    def write_userspace_settings_file_content(settings_file, content: str):
        atomic_write_text(settings_file, content)

    def get_strategies(self):
        # Step 1: delegate strategy discovery and formatting.
        return self._impl.get_strategies()

    def get_strategy_settings(self, strategy_name: str):
        # Step 1: delegate settings resolution from snapshot/userspace.
        return self._impl.get_strategy_settings(strategy_name)

    def apply_strategy_settings_to_userspace(self, strategy_name: str, payload: dict):
        # Step 1: delegate validated userspace settings write.
        return self._impl.apply_strategy_settings_to_userspace(strategy_name, payload)

    def start_strategy_run(self, strategy_name: str, payload: dict):
        # Step 1: delegate run status initialization and worker process launch.
        return self._impl.start_strategy_run(strategy_name, payload)

    @staticmethod
    def parse_start_run_request_fields(payload: dict):
        target_step = StrategyWorkbenchRequestHelper.to_stripped_str(payload, "target_step")
        run_settings = StrategyWorkbenchRequestHelper.to_dict_or_none(payload, "settings")
        is_force = StrategyWorkbenchRequestHelper.to_bool(
            payload, "is_force", "force_refresh", default=False
        )
        workbench_version_id = StrategyWorkbenchRequestHelper.to_stripped_str(
            payload, "workbench_version_id", default=""
        )
        return target_step, run_settings, is_force, workbench_version_id

    def validate_target_step(self, target_step: str):
        valid = {
            self._impl.STEP_ENUM,
            self._impl.STEP_PRICE,
            self._impl.STEP_CAPITAL,
        }
        if target_step not in valid:
            return error("target_step 必须是 enum | price | capital", 400)
        return None

    @staticmethod
    def ensure_strategy_files_exist(strategy_name: str):
        strategy_dir = PathManager.strategy(strategy_name)
        settings_file = PathManager.strategy_settings(strategy_name)
        if not strategy_dir.exists() or not strategy_dir.is_dir() or not settings_file.exists():
            return error(f"策略不存在: {strategy_name}", 404)
        return None

    def ensure_no_active_run(self, strategy_name: str):
        current = self._impl._read_status(strategy_name) or {}
        current_state = str(current.get("state") or "")
        if current_state in {self._impl.RUN_STATE_QUEUED, self._impl.RUN_STATE_RUNNING}:
            return None, error("当前策略已有执行任务在运行中", 409)
        return current, None

    def build_step_status(self, current_status: dict) -> dict:
        previous_step_status = (
            current_status.get("step_status")
            if isinstance(current_status.get("step_status"), dict)
            else {}
        )
        return {
            self._impl.STEP_ENUM: previous_step_status.get(
                self._impl.STEP_ENUM, self._impl.STEP_STATUS_IDLE
            ),
            self._impl.STEP_PRICE: previous_step_status.get(
                self._impl.STEP_PRICE, self._impl.STEP_STATUS_IDLE
            ),
            self._impl.STEP_CAPITAL: previous_step_status.get(
                self._impl.STEP_CAPITAL, self._impl.STEP_STATUS_IDLE
            ),
        }

    def resolve_run_chain(self, target_step: str, step_status: dict) -> list:
        return self._impl._resolve_chain(target_step, step_status)

    def mark_running_step_status(self, target_step: str, resolved_chain: list, step_status: dict) -> dict:
        next_step_status = dict(step_status or {})
        if resolved_chain[0] == self._impl.STEP_ENUM:
            next_step_status[self._impl.STEP_ENUM] = self._impl.STEP_STATUS_RUNNING
            if target_step != self._impl.STEP_ENUM:
                next_step_status[self._impl.STEP_PRICE] = self._impl.STEP_STATUS_IDLE
                next_step_status[self._impl.STEP_CAPITAL] = self._impl.STEP_STATUS_IDLE
        elif resolved_chain[0] == self._impl.STEP_PRICE:
            next_step_status[self._impl.STEP_ENUM] = self._impl.STEP_STATUS_DONE
            next_step_status[self._impl.STEP_PRICE] = self._impl.STEP_STATUS_RUNNING
        else:
            next_step_status[self._impl.STEP_CAPITAL] = self._impl.STEP_STATUS_RUNNING
        return next_step_status

    def build_run_settings_snapshot(self, strategy_name: str, run_settings):
        if not isinstance(run_settings, dict):
            return None, None
        normalized_runtime_settings, detail = self._impl._normalize_runtime_settings(
            strategy_name,
            run_settings,
        )
        if normalized_runtime_settings is None:
            return None, error(detail or "settings 校验失败", 422)
        return self._impl._runtime_to_api_settings(normalized_runtime_settings), None

    def resolve_workbench_snapshot_version(self, strategy_name: str, run_api_settings) -> int:
        row = self._impl._get_latest_workbench_snapshot_row(strategy_name)
        workbench_snapshot_version = int(row.get("version") or 0) if row else 0
        if run_api_settings is not None:
            # Run-scoped settings should not reuse persisted snapshot version.
            return 0
        return workbench_snapshot_version

    def build_run_status_payload(
        self,
        *,
        run_id: str,
        strategy_name: str,
        target_step: str,
        resolved_chain: list,
        step_status: dict,
        workbench_snapshot_version: int,
        run_settings_snapshot,
        is_force: bool = False,
        workbench_version_id: str = "",
    ) -> dict:
        return {
            "run_id": run_id,
            "strategy_name": strategy_name,
            "state": self._impl.RUN_STATE_RUNNING,
            "target_step": target_step,
            "resolved_chain": resolved_chain,
            "running_step": resolved_chain[0],
            "progress_pct": 0,
            "step_status": step_status,
            "result_summary": {},
            "workbench_snapshot_version": workbench_snapshot_version,
            "run_settings_snapshot": run_settings_snapshot,
            "is_force": bool(is_force),
            "workbench_version_id": str(workbench_version_id or ""),
            "updated_at": datetime.now().astimezone().isoformat(),
        }

    def write_run_status(self, strategy_name: str, status_payload: dict) -> None:
        self._impl._write_status(strategy_name, status_payload)

    def launch_run_process(self, strategy_name: str, run_id: str, resolved_chain: list) -> None:
        cancel_ev = mp.Event()
        with self._impl._run_lock:
            self._impl._run_cancel_events[run_id] = cancel_ev
            proc = mp.Process(
                target=_strategy_workbench_run_chain_entry,
                args=(strategy_name, run_id, resolved_chain, cancel_ev),
                daemon=False,
                name=f"swb_run_{run_id}",
            )
            proc.start()
            self._impl._run_processes[run_id] = proc

    def build_start_run_response(
        self,
        *,
        run_id: str,
        strategy_name: str,
        target_step: str,
        resolved_chain: list,
    ):
        return ok({
            "run_id": run_id,
            "strategy_name": strategy_name,
            "state": self._impl.RUN_STATE_RUNNING,
            "target_step": target_step,
            "resolved_chain": resolved_chain,
        })

    def generate_run_id(self) -> str:
        return self._impl._build_run_id()

    def build_enumerator_reuse_preview_flow(self, strategy_name: str):
        return self._impl.build_enumerator_reuse_preview_flow(strategy_name)

    def preprocess_enumerator_reuse_preview(self, flow, strategy_name: str, strategy_info):
        return self._impl.preprocess_enumerator_reuse_preview(
            flow, strategy_name, strategy_info
        )

    def assemble_enumerator_reuse_preview_payload(self, strategy_name: str, flow, preprocessed):
        return self._impl.assemble_enumerator_reuse_preview_payload(
            strategy_name, flow, preprocessed
        )

    def require_run_status_for_run(self, strategy_name: str, run_id: str):
        return self._impl._require_status_for_run(strategy_name, run_id)

    def normalize_run_status_step_status(self, status_payload: dict):
        return self._impl.normalize_run_status_step_status(status_payload)

    def build_run_status_response_body(
        self, run_id: str, status_payload: dict, step_status: dict
    ):
        return self._impl.build_run_status_response_body(run_id, status_payload, step_status)

    def merge_enumerator_progress_into_run_status(
        self,
        strategy_name: str,
        run_id: str,
        status_payload: dict,
        out: dict,
    ) -> None:
        self._impl.merge_enumerator_progress_into_run_status(
            strategy_name, run_id, status_payload, out
        )

    def finalize_run_worker_handles_if_terminal(
        self, strategy_name: str, run_id: str, status_payload: dict
    ) -> None:
        self._impl.finalize_run_worker_handles_if_terminal(
            strategy_name, run_id, status_payload
        )

    def normalize_run_result_summary_from_status(self, status_payload: dict) -> dict:
        return self._impl.normalize_run_result_summary_from_status(status_payload)

    def build_strategy_run_results_payload(self, run_id: str, result_summary: dict) -> dict:
        return self._impl.build_strategy_run_results_payload(run_id, result_summary)

    def resolve_workbench_version_history_ids(self, strategy_name: str) -> list:
        return self._impl.resolve_workbench_version_history_ids(strategy_name)

    def parse_report_types_query(self, report_types_raw):
        return self._impl.parse_report_types_query(report_types_raw)

    def resolve_reports_summary_for_strategy_run(self, strategy_name: str, status_payload: dict) -> dict:
        return self._impl.resolve_reports_summary_for_strategy_run(strategy_name, status_payload)

    def assemble_strategy_reports_message(
        self,
        strategy_name: str,
        run_id: str,
        result_summary: dict,
        requested_types: list,
    ) -> dict:
        return self._impl.assemble_strategy_reports_message(
            strategy_name, run_id, result_summary, requested_types
        )

    def get_strategy_report_stocks(
        self,
        strategy_name: str,
        run_id: str,
        report_type: str,
        limit: int = 10,
        search: str = "",
        sort_by: str = "",
        sort_order: str = "desc",
    ):
        # Step 1: delegate stock-row retrieval/filter/sort.
        return self._impl.get_strategy_report_stocks(
            strategy_name,
            run_id,
            report_type=report_type,
            limit=limit,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
        )

    def get_strategy_report_stock_kline(self, strategy_name: str, run_id: str, stock_id: str):
        # Step 1: delegate single-stock kline payload generation.
        return self._impl.get_strategy_report_stock_kline(strategy_name, run_id, stock_id)

    def get_strategy_report_compare(
        self,
        strategy_name: str,
        base_run_id: str,
        compare_version: str,
        report_type_raw=None,
    ):
        # Step 1: delegate compare report resolution.
        return self._impl.get_strategy_report_compare(
            strategy_name,
            base_run_id=base_run_id,
            compare_version=compare_version,
            report_type_raw=report_type_raw,
        )

    def list_strategy_versions(self, strategy_name: str):
        # Step 1: delegate version list query.
        return self._impl.list_strategy_versions(strategy_name)

    def get_strategy_version_detail(self, strategy_name: str, version_id: str):
        # Step 1: delegate version detail loading.
        return self._impl.get_strategy_version_detail(strategy_name, version_id)

    def restore_strategy_version(self, strategy_name: str, version_id: str):
        # Step 1: delegate version restore workflow.
        return self._impl.restore_strategy_version(strategy_name, version_id)

    def create_strategy_version(self, strategy_name: str, payload: dict):
        # Step 1: delegate version creation with validated settings.
        return self._impl.create_strategy_version(strategy_name, payload)

    def get_strategy_settings_options_allocation_modes(self):
        # Step 1: delegate allocation-mode options assembly.
        return self._impl.get_strategy_settings_options_allocation_modes()

    def get_strategy_settings_options_sampling_strategies(self):
        # Step 1: delegate sampling-strategy options assembly.
        return self._impl.get_strategy_settings_options_sampling_strategies()


def _strategy_workbench_run_chain_entry(
    strategy_name: str,
    run_id: str,
    resolved_chain: list,
    cancel_event,
) -> None:
    """Compatibility worker entry for child process chain execution."""
    # Step 1: delegate worker-chain execution to implementation helper.
    return _impl_run_chain_entry(strategy_name, run_id, resolved_chain, cancel_event)
