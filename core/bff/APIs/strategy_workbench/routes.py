"""Strategy workbench routes — V2 contract.

契约路径见 ``core/ui/fed/src/pages/strategyWorkbenchPage/API.md``；
编排说明见 ``ROUTES_ORCHESTRATION.md``。
应用挂载前缀：``/api``（见 ``core/bff/app.py``）。

工作台实现栈在 ``strategy_stack`` 中首次请求时再 import，避免 BFF 启动即拉 DataManager 等。
"""

from io import BytesIO

from flask import Blueprint, jsonify, request, send_file

from core.bff.shared.response import error, ok

from .formatting import workbench_snapshot_to_message
from .helpers import json_payload, pagination_params
from .package_helpers import parse_conflict_policy, read_uploaded_bytes
from .package_stack import get_strategy_package_stack
from .strategy_stack import get_strategy_workbench_stack

strategy_workbench_api_bp = Blueprint("strategy_workbench_api", __name__)


# --- V2-01 ---
@strategy_workbench_api_bp.route(
    "/v1/strategy/<path:strategy_name>/version/latest",
    methods=["GET"],
)
def get_strategy_version_latest(strategy_name):
    s = get_strategy_workbench_stack()
    row = s.fetch_latest_workbench_snapshot(strategy_name)
    if row is None:
        return error("策略不存在或无法加载工作台数据", 404)
    msg = workbench_snapshot_to_message(row)
    msg.update(s.workbench_latest_ui_flags(strategy_name, row))
    return ok(msg)


# --- V2-02 ---
@strategy_workbench_api_bp.route("/v1/strategies/list", methods=["GET"])
def get_strategies_list():
    s = get_strategy_workbench_stack()
    page, limit = pagination_params()
    items, total = s.fetch_discovered_strategies_page(page, limit)
    return ok({"items": items, "total": total, "page": page, "limit": limit})


# --- V2-03 ---
@strategy_workbench_api_bp.route(
    "/v1/strategy/<path:strategy_name>/versions",
    methods=["GET"],
)
def get_strategy_versions(strategy_name):
    """GET /strategy/{strategy_name}/versions — 下拉 / 版本对比，至多 10 条。"""
    s = get_strategy_workbench_stack()
    items = s.fetch_strategy_versions_dropdown(strategy_name)
    return ok({"items": items})


# --- V2-04（选项类：固定子路径，见 API.md） ---
@strategy_workbench_api_bp.route(
    "/v1/strategy/settings/capital-allocation-strategies",
    methods=["GET"],
)
def get_settings_capital_allocation_strategies():
    """GET /strategy/settings/capital-allocation-strategies"""
    s = get_strategy_workbench_stack()
    return ok({"items": s.items_capital_allocation_strategies()})


@strategy_workbench_api_bp.route(
    "/v1/strategy/settings/sampling-strategies",
    methods=["GET"],
)
def get_settings_sampling_strategies():
    """GET /strategy/settings/sampling-strategies"""
    s = get_strategy_workbench_stack()
    return ok({"items": s.items_sampling_strategies()})


@strategy_workbench_api_bp.route(
    "/v1/strategy/settings/simulation-templates",
    methods=["GET"],
)
def get_settings_simulation_templates():
    """GET /strategy/settings/simulation-templates"""
    s = get_strategy_workbench_stack()
    return ok({"items": s.items_simulation_templates()})


@strategy_workbench_api_bp.route(
    "/v1/strategy/settings/skip-investment-when",
    methods=["GET"],
)
def get_settings_skip_investment_when():
    """GET /strategy/settings/skip-investment-when

    URL 兼容旧路径；语义为 ``simulation.risk_control.skip_enter_when``。
    """
    s = get_strategy_workbench_stack()
    return ok({"items": s.items_skip_investment_when()})


@strategy_workbench_api_bp.route(
    "/v1/strategy/settings/market-profiles",
    methods=["GET"],
)
def get_settings_market_profiles():
    """GET /strategy/settings/market-profiles"""
    s = get_strategy_workbench_stack()
    return ok({"items": s.items_market_profiles()})


# --- V2-05 ---
@strategy_workbench_api_bp.route(
    "/v1/strategy/<path:strategy_name>/<step>/run",
    methods=["POST"],
)
def post_strategy_step_run(strategy_name, step):
    """POST /strategy/{strategy_name}/{step}/run — 成功时务必携带返回的 ``job_id`` 轮询 progress。"""
    s = get_strategy_workbench_stack()
    payload = json_payload()
    settings = payload.get("settings")
    if settings is None or not isinstance(settings, dict):
        return error("settings 必须为对象", 400)

    body_name = payload.get("strategy_name")
    if body_name is not None and str(body_name).strip() != str(strategy_name).strip():
        return error("strategy_name 与路径不一致", 400)

    raw_force = payload.get("force_refresh", False)
    force_refresh = raw_force if isinstance(raw_force, bool) else bool(raw_force)

    out = s.submit_workbench_step_via_bff_contract(
        strategy_name=strategy_name,
        step=step,
        api_settings=settings,
        force_refresh=force_refresh,
    )
    if out.get("is_triggered"):
        return ok(
            {
                "is_triggered": True,
                "job_id": out["job_id"],
                "run_id": out.get("run_id") or out["job_id"],
                "steps": out.get("steps") or [],
            }
        )
    return ok({"is_triggered": False, "reason": out.get("reason", "未知错误")})


# --- V2-06b：整次 run 编排进度（``steps[]``，不依赖路径 ``step``） ---
@strategy_workbench_api_bp.route(
    "/v1/strategy/<path:strategy_name>/run/progress",
    methods=["GET"],
)
def get_strategy_run_progress(strategy_name):
    s = get_strategy_workbench_stack()
    q_job = (request.args.get("job_id") or "").strip()
    if not q_job:
        return error("缺少必填 query 参数 job_id", 400)
    payload = s.get_run_progress(
        strategy_name=str(strategy_name),
        job_id=q_job,
    )
    if payload is None:
        return error("未找到该 job 的编排进度", 404)
    return ok(payload)


# --- V2-06 ---
@strategy_workbench_api_bp.route(
    "/v1/strategy/<path:strategy_name>/<step>/progress",
    methods=["GET"],
)
def get_strategy_step_progress(strategy_name, step):
    """GET /strategy/{strategy_name}/{step}/progress — **必填** query ``job_id``（与 V2-05 返回一致）。"""
    s = get_strategy_workbench_stack()
    norm = s.normalize_step(step)
    if norm is None:
        return error("step 须为 enum / price / capital", 400)
    q_job = (request.args.get("job_id") or "").strip()
    if not q_job:
        return error("缺少必填 query 参数 job_id", 400)
    payload = s.get_step_progress(
        strategy_name=strategy_name,
        normalized_step=norm,
        job_id=q_job,
    )
    if payload is None:
        return error("任务不存在或与路径不匹配", 404)
    return ok(payload)


# --- V2-07（report：路径 ``version_id``；典型来源为 V2-06 completed 响应） ---
@strategy_workbench_api_bp.route(
    "/v1/strategy/<path:strategy_name>/<step>/report/<version_id>",
    methods=["GET"],
)
def get_strategy_step_report(strategy_name, step, version_id):
    """
    GET …/report/<version_id>

    **路径** ``version_id``（``v3`` / ``3``）。本轮 run 在 **V2-06** 达 **completed**
    且工作台 ``version>0`` 时已下发 ``version_id``，前端用同一值拉取该步明细；历史/对比亦为同一参数。
    """
    s = get_strategy_workbench_stack()
    norm = s.normalize_step(step)
    if norm is None:
        return error("step 须为 enum / price / capital", 400)

    path_vid = str(version_id or "").strip()
    if not path_vid:
        return error("缺少路径参数 version_id", 400)

    sid = s.parse_version_id(path_vid)
    if sid is None:
        return error("version_id 无效", 400)
    msg = s.build_step_report_message(
        strategy_name=strategy_name,
        normalized_step=norm,
        version=sid,
    )
    if msg is None:
        return error("快照不存在", 404)
    return ok(msg)


# --- V2-07b：枚举 / 价格逐股 ref（``entity_list.json``） ---
@strategy_workbench_api_bp.route(
    "/v1/strategy/<path:strategy_name>/<step>/report_ref/<version_id>",
    methods=["GET"],
)
def get_strategy_step_report_ref(strategy_name, step, version_id):
    """GET …/report_ref/<version_id> — ``enum`` / ``price`` 逐股 ref（NEW ``entity_list.json``）；``stock_ref`` 可空（见 ``stock_ref_available``）。"""
    s = get_strategy_workbench_stack()
    norm = s.normalize_step(step)
    if norm is None:
        return error("step 须为 enum / price / capital", 400)

    path_vid = str(version_id or "").strip()
    if not path_vid:
        return error("缺少路径参数 version_id", 400)

    sid = s.parse_version_id(path_vid)
    if sid is None:
        return error("version_id 无效", 400)
    msg = s.build_step_report_ref_message(
        strategy_name=strategy_name,
        normalized_step=norm,
        version=sid,
    )
    if msg is None:
        return error("快照不存在", 404)
    return ok(msg)


# --- V2-07c：单股 K 线 + 步骤 markers（enum MVP） ---
@strategy_workbench_api_bp.route(
    "/v1/strategy/<path:strategy_name>/<step>/stock/<path:stock_id>",
    methods=["GET"],
)
def get_strategy_step_stock_detail(strategy_name, step, stock_id):
    """GET …/stock/{stock_id}?version_id= — 单股 K 线与标注；query ``version_id`` 必填。"""
    s = get_strategy_workbench_stack()
    norm = s.normalize_step(step)
    if norm is None:
        return error("step 须为 enum / price / capital", 400)

    path_vid = str(request.args.get("version_id") or "").strip()
    if not path_vid:
        return error("缺少 query 参数 version_id", 400)

    sid = s.parse_version_id(path_vid)
    if sid is None:
        return error("version_id 无效", 400)

    code = str(stock_id or "").strip()
    if not code:
        return error("stock_id 无效", 400)

    msg = s.build_stock_detail_message(
        strategy_name=strategy_name,
        normalized_step=norm,
        version=sid,
        stock_id=code,
    )
    if msg is None:
        return error("快照不存在", 404)
    return ok(msg)


# --- V2-08 ---
@strategy_workbench_api_bp.route(
    "/v1/strategy/<path:strategy_name>/version/<version_id>",
    methods=["GET"],
)
def get_strategy_version_snapshot(strategy_name, version_id):
    """GET /strategy/{strategy_name}/version/{version_id} — 与 latest 同形，按 id 取行（无冷启动）。"""
    s = get_strategy_workbench_stack()
    sid = s.parse_version_id(version_id)
    if sid is None:
        return error("version_id 无效", 400)
    row = s.fetch_workbench_by_version(strategy_name, sid)
    if row is None:
        return error("快照不存在", 404)
    return ok(workbench_snapshot_to_message(row))


# --- V2-09 ---
@strategy_workbench_api_bp.route(
    "/v1/strategy/<path:strategy_name>/apply-settings/<version_id>",
    methods=["POST"],
)
def post_apply_settings(strategy_name, version_id):
    """POST /strategy/{strategy_name}/apply-settings/{version_id} — 快照 settings → userspace ``settings.py``。"""
    s = get_strategy_workbench_stack()
    sid = s.parse_version_id(version_id)
    if sid is None:
        return error("version_id 无效", 400)

    payload = json_payload()
    raw_pretty = payload.get("pretty", False) if isinstance(payload, dict) else False
    pretty = raw_pretty if isinstance(raw_pretty, bool) else bool(raw_pretty)

    out, err = s.apply_workbench_snapshot_settings_to_userspace(
        strategy_name=strategy_name,
        version=sid,
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


# --- V2-11：清空模拟结果 DbCache 全表 ---
@strategy_workbench_api_bp.route(
    "/v1/strategy/workbench-snapshot-cache",
    methods=["DELETE"],
)
def delete_workbench_snapshot_cache_all():
    """DELETE /strategy/workbench-snapshot-cache — 清空 ``sys_strategy_workbench_snapshot``。"""
    s = get_strategy_workbench_stack()
    out = s.clear_workbench_simulation_cache_all()
    if not out.get("ok"):
        err = str(out.get("error") or "清理失败")
        if err == "存储不可用":
            return error(err, 503)
        return error(err, 400)
    return ok(
        {
            "cleared": True,
            "deleted_count": int(out.get("deleted_count") or 0),
        }
    )


# --- V2-12：按 version 删除单条模拟结果缓存 ---
@strategy_workbench_api_bp.route(
    "/v1/strategy/<path:strategy_name>/version/<version_id>/workbench-snapshot-cache",
    methods=["DELETE"],
)
def delete_workbench_snapshot_cache_by_version(strategy_name, version_id):
    """DELETE …/version/{version_id}/workbench-snapshot-cache — 删指定快照行。"""
    s = get_strategy_workbench_stack()
    sid = s.parse_version_id(version_id)
    if sid is None:
        return error("version_id 无效", 400)
    out = s.clear_workbench_simulation_cache_by_version(strategy_name, sid)
    if not out.get("ok"):
        err = str(out.get("error") or "删除失败")
        if err == "存储不可用":
            return error(err, 503)
        if err == "快照不存在":
            return error(err, 404)
        return error(err, 400)
    return ok(
        {
            "deleted": True,
            "strategy_name": out.get("strategy_name"),
            "version_id": out.get("version_id"),
        }
    )


# --- V2-13：策略包导出（二进制 zip） ---
@strategy_workbench_api_bp.route(
    "/v1/strategy/<path:strategy_name>/package/export",
    methods=["GET"],
)
def get_strategy_package_export(strategy_name):
    """
    GET /strategy/{strategy_name}/package/export

    Query ``scope``:
    - ``bundle`` (default): strategy + resolved tag/adapter dependencies
    - ``strategy``: strategy directory only
    """
    p = get_strategy_package_stack()
    scope = str(request.args.get("scope") or "bundle").strip().lower()
    name = str(strategy_name or "").strip()
    if not name:
        return error("strategy_name 不能为空", 400)

    try:
        if scope == "bundle":
            _manifest, payload = p.export_strategy_bundle(name)
            filename = p.bundle_filename(name)
        elif scope == "strategy":
            _manifest, payload = p.export_single_entity("strategy", name)
            filename = p.single_entity_filename("strategy", name)
        else:
            return error(f"无效 scope={scope!r}；可选 bundle | strategy", 400)
    except FileNotFoundError as exc:
        return error(str(exc), 404)
    except ValueError as exc:
        return error(str(exc), 400)
    except Exception as exc:
        return error(f"导出失败: {exc}", 500)

    if isinstance(payload, (bytes, bytearray)):
        data = bytes(payload)
    else:
        data = payload.read_bytes()

    return send_file(
        BytesIO(data),
        mimetype="application/zip",
        as_attachment=True,
        download_name=filename,
    )


# --- V2-14：策略包导入预览 ---
@strategy_workbench_api_bp.route(
    "/v1/strategy/package/import/preview",
    methods=["POST"],
)
def post_strategy_package_import_preview():
    """POST multipart ``file`` + ``policy`` (reject | skip_existing | overwrite)."""
    blob, err = read_uploaded_bytes()
    if err is not None:
        return err

    policy, err = parse_conflict_policy()
    if err is not None:
        return err

    p = get_strategy_package_stack()
    try:
        preview = p.preview_strategy_bundle_import(blob, policy=policy)
    except Exception as exc:
        return error(f"无法解析策略包: {exc}", 400)

    return ok(preview)


# --- V2-15：策略包导入 ---
@strategy_workbench_api_bp.route(
    "/v1/strategy/package/import",
    methods=["POST"],
)
def post_strategy_package_import():
    """POST multipart ``file`` + ``policy``; 409 when reject policy hits conflicts."""
    blob, err = read_uploaded_bytes()
    if err is not None:
        return err

    policy, err = parse_conflict_policy()
    if err is not None:
        return err

    p = get_strategy_package_stack()
    try:
        preview = p.preview_strategy_bundle_import(blob, policy=policy)
    except Exception as exc:
        return error(f"无法解析策略包: {exc}", 400)

    if not preview.get("ok"):
        return (
            jsonify(
                {
                    "status": "error",
                    "message": {
                        "detail": "导入冲突：目标路径已存在",
                        "code": "package_conflict",
                        "preview": preview,
                    },
                }
            ),
            409,
        )

    try:
        result = p.import_strategy_bundle(blob, policy)
    except Exception as exc:
        return error(f"导入失败: {exc}", 500)

    if not result.ok:
        return error("; ".join(result.errors) or "导入失败", 500)

    return ok(
        {
            "strategy_name": preview.get("strategy_name") or preview.get("entity_name"),
            "bundle_type": preview.get("bundle_type"),
            "policy": preview.get("policy"),
            "installed": [
                {"kind": e.kind, "name": e.name, "target_relative": e.target_relative}
                for e in result.installed
            ],
            "skipped": [
                {"kind": e.kind, "name": e.name, "target_relative": e.target_relative}
                for e in result.skipped
            ],
        }
    )
