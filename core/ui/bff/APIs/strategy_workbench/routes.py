"""Strategy workbench routes — V2 contract.

契约路径见 ``core/ui/fed/src/pages/strategyWorkbenchPage/API.md``；
编排说明见 ``ROUTES_ORCHESTRATION.md``。
应用挂载前缀：``/api``（见 ``core/ui/bff/app.py``）。

路由内直接编排后端调用；若有复杂分支或复用需求再抽到 ``service`` 层。
"""

from flask import Blueprint, request

from core.modules.strategy.services.launcher import fetch_latest_workbench_snapshot
from core.modules.strategy.services.launcher.workbench import (
    apply_workbench_snapshot_settings_to_userspace,
    build_step_report_message,
    fetch_workbench_snapshot_by_snapshot_id,
    parse_snapshot_id,
)
from core.modules.strategy.services.launcher.workbench_catalog import (
    fetch_discovered_strategies_page,
    fetch_strategy_versions_dropdown,
    items_capital_allocation_strategies,
    items_sampling_strategies,
)
from core.modules.strategy.services.launcher.workbench_step_run import (
    get_step_progress,
    normalize_step,
    trigger_workbench_step_run,
)
from core.ui.bff.shared.response import error, ok

from .formatting import workbench_snapshot_to_message
from .helpers import json_payload, pagination_params

strategy_workbench_api_bp = Blueprint("strategy_workbench_api", __name__)


# --- V2-01 ---
@strategy_workbench_api_bp.route(
    "/v1/strategy/<strategy_name>/version/latest",
    methods=["GET"],
)
def get_strategy_version_latest(strategy_name):
    row = fetch_latest_workbench_snapshot(strategy_name)
    if row is None:
        return error("策略不存在或无法加载工作台数据", 404)
    return ok(workbench_snapshot_to_message(row))


# --- V2-02 ---
@strategy_workbench_api_bp.route("/v1/strategies/list", methods=["GET"])
def get_strategies_list():
    page, limit = pagination_params()
    items, total = fetch_discovered_strategies_page(page, limit)
    return ok({"items": items, "total": total, "page": page, "limit": limit})


# --- V2-03 ---
@strategy_workbench_api_bp.route(
    "/v1/strategy/<strategy_name>/versions",
    methods=["GET"],
)
def get_strategy_versions(strategy_name):
    """GET /strategy/{strategy_name}/versions — 下拉 / 版本对比，至多 10 条。"""
    items = fetch_strategy_versions_dropdown(strategy_name)
    return ok({"items": items})


# --- V2-04（选项类：固定子路径，见 API.md） ---
@strategy_workbench_api_bp.route(
    "/v1/strategy/settings/capital-allocation-strategies",
    methods=["GET"],
)
def get_settings_capital_allocation_strategies():
    """GET /strategy/settings/capital-allocation-strategies"""
    return ok({"items": items_capital_allocation_strategies()})


@strategy_workbench_api_bp.route(
    "/v1/strategy/settings/sampling-strategies",
    methods=["GET"],
)
def get_settings_sampling_strategies():
    """GET /strategy/settings/sampling-strategies"""
    return ok({"items": items_sampling_strategies()})


# --- V2-05 ---
@strategy_workbench_api_bp.route(
    "/v1/strategy/<strategy_name>/<step>/run",
    methods=["POST"],
)
def post_strategy_step_run(strategy_name, step):
    """POST /strategy/{strategy_name}/{step}/run — 成功时务必携带返回的 ``job_id`` 轮询 progress。"""
    payload = json_payload()
    settings = payload.get("settings")
    if settings is None or not isinstance(settings, dict):
        return error("settings 必须为对象", 400)

    body_name = payload.get("strategy_name")
    if body_name is not None and str(body_name).strip() != str(strategy_name).strip():
        return error("strategy_name 与路径不一致", 400)

    raw_force = payload.get("is_force", False)
    is_force = raw_force if isinstance(raw_force, bool) else bool(raw_force)

    out = trigger_workbench_step_run(
        strategy_name=strategy_name,
        step=step,
        api_settings=settings,
        is_force=is_force,
    )
    if out.get("is_triggered"):
        return ok({"is_triggered": True, "job_id": out["job_id"]})
    return ok({"is_triggered": False, "reason": out.get("reason", "未知错误")})


# --- V2-06 ---
@strategy_workbench_api_bp.route(
    "/v1/strategy/<strategy_name>/<step>/progress",
    methods=["GET"],
)
def get_strategy_step_progress(strategy_name, step):
    """GET /strategy/{strategy_name}/{step}/progress — **必填** query ``job_id``（与 V2-05 返回一致）。"""
    norm = normalize_step(step)
    if norm is None:
        return error("step 须为 enum / price / capital", 400)
    q_job = (request.args.get("job_id") or "").strip()
    if not q_job:
        return error("缺少必填 query 参数 job_id", 400)
    payload = get_step_progress(
        strategy_name=strategy_name,
        normalized_step=norm,
        job_id=q_job,
    )
    if payload is None:
        return error("任务不存在或与路径不匹配", 404)
    return ok(payload)


# --- V2-07（report：必填 ``version_id``；典型来源为 V2-06 completed 响应） ---
@strategy_workbench_api_bp.route(
    "/v1/strategy/<strategy_name>/<step>/report",
    methods=["GET"],
)
def get_strategy_step_report(strategy_name, step):
    """
    GET …/report?version_id=

    **必填** query ``version_id``（``v3`` / ``3``）。本轮 run 在 **V2-06** 达 **completed**
    且 ``snapshot_id>0`` 时已下发 ``version_id``，前端用同一值拉取该步明细；历史/对比亦为同一参数。
    """
    norm = normalize_step(step)
    if norm is None:
        return error("step 须为 enum / price / capital", 400)

    q_vid = (request.args.get("version_id") or "").strip()
    if not q_vid:
        return error("缺少必填 query 参数 version_id", 400)

    sid = parse_snapshot_id(q_vid)
    if sid is None:
        return error("version_id 无效", 400)
    msg = build_step_report_message(
        strategy_name=strategy_name,
        normalized_step=norm,
        snapshot_id=sid,
    )
    if msg is None:
        return error("快照不存在", 404)
    return ok(msg)


# --- V2-08 ---
@strategy_workbench_api_bp.route(
    "/v1/strategy/<strategy_name>/version/<version_id>",
    methods=["GET"],
)
def get_strategy_version_snapshot(strategy_name, version_id):
    """GET /strategy/{strategy_name}/version/{version_id} — 与 latest 同形，按 id 取行（无冷启动）。"""
    sid = parse_snapshot_id(version_id)
    if sid is None:
        return error("version_id 无效", 400)
    row = fetch_workbench_snapshot_by_snapshot_id(strategy_name, sid)
    if row is None:
        return error("快照不存在", 404)
    return ok(workbench_snapshot_to_message(row))


# --- V2-09 ---
@strategy_workbench_api_bp.route(
    "/v1/strategy/<strategy_name>/apply-settings/<version_id>",
    methods=["POST"],
)
def post_apply_settings(strategy_name, version_id):
    """POST /strategy/{strategy_name}/apply-settings/{version_id} — 快照 settings → userspace ``settings.py``。"""
    sid = parse_snapshot_id(version_id)
    if sid is None:
        return error("version_id 无效", 400)

    payload = json_payload()
    raw_pretty = payload.get("pretty", False) if isinstance(payload, dict) else False
    pretty = raw_pretty if isinstance(raw_pretty, bool) else bool(raw_pretty)

    out, err = apply_workbench_snapshot_settings_to_userspace(
        strategy_name=strategy_name,
        snapshot_id=sid,
        pretty=pretty,
    )
    if err:
        if err == "快照不存在":
            return error(err, 404)
        if err == "存储不可用":
            return error(err, 503)
        if err.startswith("写盘失败") or err.startswith("更新快照时间失败"):
            return error(err, 500)
        return error(err, 400)
    return ok(out)
