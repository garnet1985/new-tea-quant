"""Strategy workbench routes (endpoint definitions)."""

from flask import Blueprint, request

from core.ui.bff.shared.response import ok
from .service import StrategyWorkbenchService
from .request_helper import StrategyWorkbenchRequestHelper


strategy_workbench_api_bp = Blueprint("strategy_workbench_api", __name__)
_strategy_workbench_service = StrategyWorkbenchService()


def _json_payload() -> dict:
    """Step helper: normalize request json body."""
    return request.get_json(silent=True) or {}


def query_arg(name: str, default=None):
    """Step helper: fetch query arg."""
    return request.args.get(name, default)


def route_value(value):
    return StrategyWorkbenchRequestHelper.normalize_str_value(value)


def delegate(method_name: str, *args, **kwargs):
    return StrategyWorkbenchRequestHelper.invoke_service_method(
        _strategy_workbench_service,
        method_name,
        *args,
        **kwargs,
    )


@strategy_workbench_api_bp.route('/v1/strategies', methods=['GET'])
def get_strategies():

    discovered = _strategy_workbench_service.discover_strategies()

    strategies = _strategy_workbench_service.to_strategy_list_response_rows(discovered)

    ordered = _strategy_workbench_service.sort_discovered_strategies(strategies)

    return ok({"strategies": ordered})


@strategy_workbench_api_bp.route('/v1/strategies/<strategy_name>/settings', methods=['GET'])
def get_strategy_settings(strategy_name):

    strategy_name = _strategy_workbench_service.stringify(strategy_name)


    settings_file, err = _strategy_workbench_service.ensure_strategy_settings_files(strategy_name)
    if err:
        return err


    settings_snapshot = _strategy_workbench_service.load_latest_settings_snapshot(strategy_name)
    if _strategy_workbench_service.has_settings_snapshot(settings_snapshot):
        runtime_settings = _strategy_workbench_service.to_runtime_settings(settings_snapshot)
        return _strategy_workbench_service.build_settings_response(
            strategy_name=strategy_name,
            settings=runtime_settings,
            settings_source="workbench_snapshot",
            workbench_version_id=settings_snapshot.get("version_id") or "",
        )


    api_settings, err = _strategy_workbench_service.load_userspace_api_settings(
        strategy_name=strategy_name,
        settings_file=settings_file,
    )
    if err:
        return err
    return _strategy_workbench_service.build_settings_response(
        strategy_name=strategy_name,
        settings=api_settings,
        settings_source="userspace",
        workbench_version_id="",
    )


@strategy_workbench_api_bp.route(
    '/v1/strategies/<strategy_name>/settings/apply-to-userspace',
    methods=['POST'],
)
def apply_strategy_settings_to_userspace(strategy_name):
    strategy_key = route_value(strategy_name)
    payload, err = _strategy_workbench_service.ensure_payload_object(_json_payload())
    if err:
        return err
    err = _strategy_workbench_service.ensure_strategy_exists(strategy_key)
    if err:
        return err

    ui_extracted_settings = _strategy_workbench_service.extract_settings_from_payload(payload)
    original_formatted_settings, err = _strategy_workbench_service.to_original_formatted_settings(
        strategy_key,
        ui_extracted_settings,
    )
    if err:
        return err

    settings_file = _strategy_workbench_service.resolve_userspace_settings_file(strategy_key)
    _strategy_workbench_service.backup_userspace_settings_file(settings_file)

    pretty_content = _strategy_workbench_service.build_userspace_settings_file_content(
        original_formatted_settings,
        pretty=True,
    )
    _strategy_workbench_service.write_userspace_settings_file_content(settings_file, pretty_content)
    return ok({
        "strategy_name": strategy_key,
        "applied": True,
    })


@strategy_workbench_api_bp.route('/v1/strategies/<strategy_name>/runs', methods=['POST'])
def start_strategy_run(strategy_name):
    # Step 1: normalize route + payload.
    strategy_key = route_value(strategy_name)
    payload, err = _strategy_workbench_service.ensure_payload_object(_json_payload())
    if err:
        return err

    # Step 2: parse and validate run contract fields.
    target_step, is_force, run_settings = (
        _strategy_workbench_service.parse_start_run_request_fields(payload)
    )
    err = _strategy_workbench_service.validate_target_step(target_step)
    if err:
        return err

    # Step 3: validate strategy files + no active run.
    err = _strategy_workbench_service.ensure_strategy_files_exist(strategy_key)
    if err:
        return err
    current_status, err = _strategy_workbench_service.ensure_no_active_run(strategy_key)
    if err:
        return err

    # Step 4: resolve chain and initial step status.
    step_status = _strategy_workbench_service.build_step_status(current_status)
    resolved_chain = _strategy_workbench_service.resolve_run_chain(target_step, step_status)
    running_step_status = _strategy_workbench_service.mark_running_step_status(
        target_step,
        resolved_chain,
        step_status,
    )

    # Step 5: normalize optional run settings snapshot.
    run_settings_snapshot, err = _strategy_workbench_service.build_run_settings_snapshot(
        strategy_key,
        run_settings,
    )
    if err:
        return err

    # Step 6: create run id and status payload.
    run_id = _strategy_workbench_service.generate_run_id()
    workbench_snapshot_version = _strategy_workbench_service.resolve_workbench_snapshot_version(
        strategy_key,
        run_settings_snapshot,
    )
    status_payload = _strategy_workbench_service.build_run_status_payload(
        run_id=run_id,
        strategy_name=strategy_key,
        target_step=target_step,
        resolved_chain=resolved_chain,
        step_status=running_step_status,
        workbench_snapshot_version=workbench_snapshot_version,
        run_settings_snapshot=run_settings_snapshot,
        is_force=is_force,
    )

    # Step 7: persist status then launch worker process.
    _strategy_workbench_service.write_run_status(strategy_key, status_payload)
    _strategy_workbench_service.launch_run_process(strategy_key, run_id, resolved_chain)

    # Step 8: return run bootstrap response.
    return _strategy_workbench_service.build_start_run_response(
        run_id=run_id,
        strategy_name=strategy_key,
        target_step=target_step,
        resolved_chain=resolved_chain,
        is_force=is_force,
    )


@strategy_workbench_api_bp.route(
    '/v1/strategies/<strategy_name>/enumerator-reuse-preview',
    methods=['GET'],
)
def get_strategy_enumerator_reuse_preview(strategy_name):
    # Step 1: read and normalize route parameter.
    strategy_key = route_value(strategy_name)
    # Step 2: delegate reuse-preview planning workflow.
    response = delegate("get_enumerator_reuse_preview", strategy_key)
    # Step 3: return response envelope.
    return response


@strategy_workbench_api_bp.route('/v1/strategies/<strategy_name>/runs/<run_id>', methods=['GET'])
def get_strategy_run_status(strategy_name, run_id):
    # Step 1: read and normalize route parameters.
    strategy_key = route_value(strategy_name)
    run_key = route_value(run_id)
    # Step 2: delegate run-status query + progress aggregation.
    response = delegate("get_strategy_run_status", strategy_key, run_key)
    # Step 3: return response envelope.
    return response


@strategy_workbench_api_bp.route('/v1/strategies/<strategy_name>/runs/<run_id>/cancel', methods=['POST'])
def cancel_strategy_run(strategy_name, run_id):
    # Step 1: read and normalize route parameters.
    strategy_key = route_value(strategy_name)
    run_key = route_value(run_id)
    # Step 2: delegate cancellation signaling workflow.
    response = delegate("cancel_strategy_run", strategy_key, run_key)
    # Step 3: return response envelope.
    return response


@strategy_workbench_api_bp.route('/v1/strategies/<strategy_name>/run-results/<run_id>', methods=['GET'])
def get_strategy_run_results(strategy_name, run_id):
    # Step 1: read and normalize route parameters.
    strategy_key = route_value(strategy_name)
    run_key = route_value(run_id)
    # Step 2: delegate run-result summary query.
    response = delegate("get_strategy_run_results", strategy_key, run_key)
    # Step 3: return response envelope.
    return response


@strategy_workbench_api_bp.route('/v1/strategies/<strategy_name>/compare-options', methods=['GET'])
def get_strategy_compare_options(strategy_name):
    # Step 1: read and normalize route parameter.
    strategy_key = route_value(strategy_name)
    # Step 2: delegate compare-options query.
    response = delegate("get_strategy_compare_options", strategy_key)
    # Step 3: return response envelope.
    return response


@strategy_workbench_api_bp.route('/v1/strategies/<strategy_name>/reports/<run_id>', methods=['GET'])
def get_strategy_reports(strategy_name, run_id):
    # Step 1: read and normalize route parameters.
    strategy_key = route_value(strategy_name)
    run_key = route_value(run_id)
    # Step 2: read query filters.
    report_types = query_arg("report_types")
    # Step 3: delegate report aggregation workflow.
    response = delegate("get_strategy_reports", strategy_key, run_key, report_types)
    # Step 4: return response envelope.
    return response


@strategy_workbench_api_bp.route('/v1/strategies/<strategy_name>/reports/<run_id>/stocks', methods=['GET'])
def get_strategy_report_stocks(strategy_name, run_id):
    # Step 1: read and normalize route parameters.
    strategy_key = route_value(strategy_name)
    run_key = route_value(run_id)
    # Step 2: normalize query args for filtering/sorting/pagination.
    report_type = route_value(query_arg("report_type"))
    limit = request.args.get("limit", type=int) or 10
    search = query_arg("search", "")
    sort_by = query_arg("sort_by", "")
    sort_order = query_arg("sort_order", "desc")
    # Step 3: delegate stock-list report query.
    response = delegate(
        "get_strategy_report_stocks",
        strategy_key,
        run_key,
        report_type=report_type,
        limit=limit,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    # Step 4: return response envelope.
    return response


@strategy_workbench_api_bp.route('/v1/strategies/<strategy_name>/reports/<run_id>/stocks/<stock_id>/kline', methods=['GET'])
def get_strategy_report_stock_kline(strategy_name, run_id, stock_id):
    # Step 1: read and normalize route parameters.
    strategy_key = route_value(strategy_name)
    run_key = route_value(run_id)
    stock_key = route_value(stock_id)
    # Step 2: delegate single-stock kline query.
    response = delegate("get_strategy_report_stock_kline", strategy_key, run_key, stock_key)
    # Step 3: return response envelope.
    return response


@strategy_workbench_api_bp.route('/v1/strategies/<strategy_name>/reports/compare', methods=['GET'])
def get_strategy_report_compare(strategy_name):
    # Step 1: read and normalize route parameter.
    strategy_key = route_value(strategy_name)
    # Step 2: normalize query args.
    base_run_id = route_value(query_arg("base_run_id"))
    compare_version = route_value(query_arg("compare_version"))
    report_type = query_arg("report_type")
    # Step 3: delegate compare report workflow.
    response = delegate(
        "get_strategy_report_compare",
        strategy_key,
        base_run_id=base_run_id,
        compare_version=compare_version,
        report_type_raw=report_type,
    )
    # Step 4: return response envelope.
    return response


@strategy_workbench_api_bp.route('/v1/strategies/<strategy_name>/versions', methods=['GET'])
def list_strategy_versions(strategy_name):
    # Step 1: read and normalize route parameter.
    strategy_key = route_value(strategy_name)
    # Step 2: delegate version list query.
    response = delegate("list_strategy_versions", strategy_key)
    # Step 3: return response envelope.
    return response


@strategy_workbench_api_bp.route('/v1/strategies/<strategy_name>/versions/<version_id>', methods=['GET'])
def get_strategy_version_detail(strategy_name, version_id):
    # Step 1: read and normalize route parameters.
    strategy_key = route_value(strategy_name)
    version_key = route_value(version_id)
    # Step 2: delegate version detail query.
    response = delegate("get_strategy_version_detail", strategy_key, version_key)
    # Step 3: return response envelope.
    return response


@strategy_workbench_api_bp.route('/v1/strategies/<strategy_name>/versions/<version_id>/restore', methods=['POST'])
def restore_strategy_version(strategy_name, version_id):
    # Step 1: read and normalize route parameters.
    strategy_key = route_value(strategy_name)
    version_key = route_value(version_id)
    # Step 2: delegate version restore workflow.
    response = delegate("restore_strategy_version", strategy_key, version_key)
    # Step 3: return response envelope.
    return response


@strategy_workbench_api_bp.route('/v1/strategies/<strategy_name>/versions', methods=['POST'])
def create_strategy_version(strategy_name):
    # Step 1: read and normalize route parameter.
    strategy_key = route_value(strategy_name)
    # Step 2: normalize request payload.
    payload = _json_payload()
    # Step 3: delegate version creation workflow.
    response = delegate("create_strategy_version", strategy_key, payload)
    # Step 4: return response envelope.
    return response


@strategy_workbench_api_bp.route('/v1/strategies/settings-options/allocation-modes', methods=['GET'])
def get_strategy_settings_options_allocation_modes():
    # Step 1: delegate option catalog query.
    response = delegate("get_strategy_settings_options_allocation_modes")
    # Step 2: return response envelope.
    return response


@strategy_workbench_api_bp.route('/v1/strategies/settings-options/sampling-strategies', methods=['GET'])
def get_strategy_settings_options_sampling_strategies():
    # Step 1: delegate option catalog query.
    response = delegate("get_strategy_settings_options_sampling_strategies")
    # Step 2: return response envelope.
    return response
