"""Strategy workbench routes (endpoint definitions)."""

from flask import Blueprint, request

from .service import StrategyWorkbenchService

strategy_workbench_api_bp = Blueprint("strategy_workbench_api", __name__)
_strategy_workbench_service = StrategyWorkbenchService()


@strategy_workbench_api_bp.route('/v1/strategies', methods=['GET'])
def get_strategies():
    return _strategy_workbench_service.get_strategies()


@strategy_workbench_api_bp.route('/v1/strategies/<strategy_name>/settings', methods=['GET'])
def get_strategy_settings(strategy_name):
    return _strategy_workbench_service.get_strategy_settings(strategy_name)


@strategy_workbench_api_bp.route('/v1/strategies/<strategy_name>/settings', methods=['PUT'])
def save_strategy_settings(strategy_name):
    payload = request.get_json(silent=True) or {}
    return _strategy_workbench_service.save_strategy_settings(strategy_name, payload)


@strategy_workbench_api_bp.route('/v1/strategies/<strategy_name>/runs', methods=['POST'])
def start_strategy_run(strategy_name):
    payload = request.get_json(silent=True) or {}
    return _strategy_workbench_service.start_strategy_run(strategy_name, payload)


@strategy_workbench_api_bp.route('/v1/strategies/<strategy_name>/runs/<run_id>', methods=['GET'])
def get_strategy_run_status(strategy_name, run_id):
    return _strategy_workbench_service.get_strategy_run_status(strategy_name, run_id)


@strategy_workbench_api_bp.route('/v1/strategies/<strategy_name>/runs/<run_id>/cancel', methods=['POST'])
def cancel_strategy_run(strategy_name, run_id):
    return _strategy_workbench_service.cancel_strategy_run(strategy_name, run_id)


@strategy_workbench_api_bp.route('/v1/strategies/<strategy_name>/run-results/<run_id>', methods=['GET'])
def get_strategy_run_results(strategy_name, run_id):
    return _strategy_workbench_service.get_strategy_run_results(strategy_name, run_id)


@strategy_workbench_api_bp.route('/v1/strategies/<strategy_name>/compare-options', methods=['GET'])
def get_strategy_compare_options(strategy_name):
    return _strategy_workbench_service.get_strategy_compare_options(strategy_name)


@strategy_workbench_api_bp.route('/v1/strategies/<strategy_name>/reports/<run_id>', methods=['GET'])
def get_strategy_reports(strategy_name, run_id):
    report_types = request.args.get("report_types")
    return _strategy_workbench_service.get_strategy_reports(strategy_name, run_id, report_types)


@strategy_workbench_api_bp.route('/v1/strategies/<strategy_name>/reports/<run_id>/stocks', methods=['GET'])
def get_strategy_report_stocks(strategy_name, run_id):
    report_type = str(request.args.get("report_type") or "").strip()
    limit = request.args.get("limit", type=int) or 10
    search = request.args.get("search", "")
    sort_by = request.args.get("sort_by", "")
    sort_order = request.args.get("sort_order", "desc")
    return _strategy_workbench_service.get_strategy_report_stocks(
        strategy_name,
        run_id,
        report_type=report_type,
        limit=limit,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
    )


@strategy_workbench_api_bp.route('/v1/strategies/<strategy_name>/reports/<run_id>/stocks/<stock_id>/kline', methods=['GET'])
def get_strategy_report_stock_kline(strategy_name, run_id, stock_id):
    return _strategy_workbench_service.get_strategy_report_stock_kline(strategy_name, run_id, stock_id)


@strategy_workbench_api_bp.route('/v1/strategies/<strategy_name>/reports/compare', methods=['GET'])
def get_strategy_report_compare(strategy_name):
    base_run_id = str(request.args.get("base_run_id") or "").strip()
    compare_version = str(request.args.get("compare_version") or "").strip()
    report_type = request.args.get("report_type")
    return _strategy_workbench_service.get_strategy_report_compare(
        strategy_name,
        base_run_id=base_run_id,
        compare_version=compare_version,
        report_type_raw=report_type,
    )


@strategy_workbench_api_bp.route('/v1/strategies/<strategy_name>/versions', methods=['GET'])
def list_strategy_versions(strategy_name):
    return _strategy_workbench_service.list_strategy_versions(strategy_name)


@strategy_workbench_api_bp.route('/v1/strategies/<strategy_name>/versions/<version_id>', methods=['GET'])
def get_strategy_version_detail(strategy_name, version_id):
    return _strategy_workbench_service.get_strategy_version_detail(strategy_name, version_id)


@strategy_workbench_api_bp.route('/v1/strategies/<strategy_name>/versions/<version_id>/restore', methods=['POST'])
def restore_strategy_version(strategy_name, version_id):
    return _strategy_workbench_service.restore_strategy_version(strategy_name, version_id)


@strategy_workbench_api_bp.route('/v1/strategies/<strategy_name>/versions', methods=['POST'])
def create_strategy_version(strategy_name):
    payload = request.get_json(silent=True) or {}
    return _strategy_workbench_service.create_strategy_version(strategy_name, payload)


@strategy_workbench_api_bp.route('/v1/strategies/settings-options/allocation-modes', methods=['GET'])
def get_strategy_settings_options_allocation_modes():
    return _strategy_workbench_service.get_strategy_settings_options_allocation_modes()


@strategy_workbench_api_bp.route('/v1/strategies/settings-options/sampling-strategies', methods=['GET'])
def get_strategy_settings_options_sampling_strategies():
    return _strategy_workbench_service.get_strategy_settings_options_sampling_strategies()
