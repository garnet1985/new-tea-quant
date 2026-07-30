"""V2-01 / V2-03 / V2-08 — workbench snapshots & versions."""

from core.bff.APIs.strategy.blueprint import strategy_api_bp
from core.bff.APIs.strategy.helpers.formatting import workbench_snapshot_to_message
from core.bff.APIs.strategy.stack import get_stack
from core.bff.shared.response import error, ok


@strategy_api_bp.route(
    "/v1/strategy/<path:strategy_name>/version/latest",
    methods=["GET"],
)
def get_strategy_version_latest(strategy_name):
    s = get_stack()
    row = s.fetch_latest_workbench_snapshot(strategy_name)
    if row is None:
        return error("策略不存在或无法加载工作台数据", 404)
    msg = workbench_snapshot_to_message(row)
    msg.update(s.workbench_latest_ui_flags(strategy_name, row))
    return ok(msg)


@strategy_api_bp.route(
    "/v1/strategy/<path:strategy_name>/versions",
    methods=["GET"],
)
def get_strategy_versions(strategy_name):
    """GET /strategy/{strategy_name}/versions — 下拉 / 版本对比，至多 10 条。"""
    s = get_stack()
    items = s.fetch_strategy_versions_dropdown(strategy_name)
    return ok({"items": items})


@strategy_api_bp.route(
    "/v1/strategy/<path:strategy_name>/version/<version_id>",
    methods=["GET"],
)
def get_strategy_version_snapshot(strategy_name, version_id):
    """GET /strategy/{strategy_name}/version/{version_id} — 与 latest 同形，按 id 取行（无冷启动）。"""
    s = get_stack()
    sid = s.parse_version_id(version_id)
    if sid is None:
        return error("version_id 无效", 400)
    row = s.fetch_workbench_by_version(strategy_name, sid)
    if row is None:
        return error("快照不存在", 404)
    return ok(workbench_snapshot_to_message(row))
