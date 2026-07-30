from core.bff.APIs.strategy.api_base import API_BASE_PATH, strategy_api_bp
from core.bff.APIs.strategy.helpers.formatting import workbench_snapshot_to_message
from core.bff.APIs.strategy.routes.version.implementer import impl as version_impl
from core.bff.APIs.strategy.stack import get_stack
from core.bff.shared.request import json_payload
from core.bff.shared.response import error, ok

# ***********************************************
#     Strategy Version (snapshots + cache clear)
# ***********************************************


def _http_from_cache_result(out: dict, *, all_mode: bool):
    if out.get("ok"):
        if all_mode:
            return ok(
                {
                    "cleared": True,
                    "deleted_count": int(out.get("deleted_count") or 0),
                }
            )
        return ok(
            {
                "deleted": True,
                "strategy_name": out.get("strategy_name"),
                "version_id": out.get("version_id"),
            }
        )
    err = str(out.get("error") or ("清理失败" if all_mode else "删除失败"))
    if err == "存储不可用":
        return error(err, 503)
    if err == "快照不存在":
        return error(err, 404)
    return error(err, 400)


@strategy_api_bp.route(
    f"{API_BASE_PATH}/version/cache",
    methods=["DELETE"],
)
def delete_strategy_version_cache_all():
    """
    DELETE /api/v1/strategy/version/cache

    清空工作台快照 DbCache 表全部行（原 V2-11）。
    """
    versions = version_impl.lazy_load()
    return _http_from_cache_result(versions.clear_cache_all(), all_mode=True)


@strategy_api_bp.route(
    f"{API_BASE_PATH}/version/<version_id>/cache/<path:strategy_key_or_name>",
    methods=["DELETE"],
)
def delete_strategy_version_cache_by_version(
    version_id: str, strategy_key_or_name: str
):
    """
    DELETE /api/v1/strategy/version/:version_id/cache/:strategy_key_or_name

    ``strategy_key_or_name``: ``settings.meta.key`` 或 path name。
    """
    versions = version_impl.lazy_load()
    try:
        out = versions.clear_cache_by_version(
            strategy_key_or_name=strategy_key_or_name, version_id=version_id
        )
    except ValueError as exc:
        return error(str(exc), 400)
    except FileNotFoundError as exc:
        return error(str(exc), 404)
    return _http_from_cache_result(out, all_mode=False)


@strategy_api_bp.route(
    f"{API_BASE_PATH}/<path:strategy_name>/version/latest",
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
    f"{API_BASE_PATH}/<path:strategy_name>/versions",
    methods=["GET"],
)
def get_strategy_versions(strategy_name):
    """GET /strategy/{strategy_name}/versions — 下拉 / 版本对比，至多 10 条。"""
    s = get_stack()
    items = s.fetch_strategy_versions_dropdown(strategy_name)
    return ok({"items": items})


@strategy_api_bp.route(
    f"{API_BASE_PATH}/<path:strategy_name>/version/<version_id>",
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


@strategy_api_bp.route(
    f"{API_BASE_PATH}/<path:strategy_name>/apply-settings/<version_id>",
    methods=["POST"],
)
def post_apply_settings(strategy_name, version_id):
    s = get_stack()
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
