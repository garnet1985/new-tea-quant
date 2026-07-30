from core.bff.APIs.strategy.api_base import API_BASE_PATH, strategy_api_bp
from core.bff.APIs.strategy.helpers.formatting import workbench_snapshot_to_message
from core.bff.APIs.strategy.routes.version.implementer import impl as version_impl
from core.bff.shared.response import error, ok

# ***********************************************
#     Strategy Version (snapshots + cache clear)
#
# Pattern: /v1/strategy/{target}/version/…
# Global (no target): DELETE …/version/cache
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

    清空工作台快照 DbCache 表全部行（V2-11，无 target）。
    """
    versions = version_impl.lazy_load()
    return _http_from_cache_result(versions.clear_cache_all(), all_mode=True)


@strategy_api_bp.route(
    f"{API_BASE_PATH}/<path:strategy_key_or_name>/version/latest",
    methods=["GET"],
)
def get_strategy_version_latest(strategy_key_or_name: str):
    """
    GET /api/v1/strategy/:strategy_key_or_name/version/latest

    V2-01：latest 快照（可含冷启动合成行）+ ui_flags。
    须注册在 ``…/version/<version_id>`` 之前，避免 ``latest`` 被当成 version_id。
    """
    versions = version_impl.lazy_load()
    try:
        row, flags = versions.fetch_latest(strategy_key_or_name)
    except ValueError as exc:
        return error(str(exc), 400)
    except FileNotFoundError as exc:
        return error(str(exc), 404)
    if row is None:
        return error("策略不存在或无法加载工作台数据", 404)
    msg = workbench_snapshot_to_message(row)
    msg.update(flags)
    return ok(msg)


@strategy_api_bp.route(
    f"{API_BASE_PATH}/<path:strategy_key_or_name>/versions",
    methods=["GET"],
)
def get_strategy_versions(strategy_key_or_name: str):
    """
    GET /api/v1/strategy/:strategy_key_or_name/versions

    V2-03：下拉 / 版本对比，至多 10 条。
    """
    versions = version_impl.lazy_load()
    try:
        items = versions.list_versions(strategy_key_or_name)
    except ValueError as exc:
        return error(str(exc), 400)
    except FileNotFoundError as exc:
        return error(str(exc), 404)
    return ok({"items": items})


@strategy_api_bp.route(
    f"{API_BASE_PATH}/<path:strategy_key_or_name>/version/<version_id>/cache",
    methods=["DELETE"],
)
def delete_strategy_version_cache_by_version(
    strategy_key_or_name: str, version_id: str
):
    """
    DELETE /api/v1/strategy/:strategy_key_or_name/version/:version_id/cache

    V2-12：删除指定工作台 version 的一条快照行。
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
    f"{API_BASE_PATH}/<path:strategy_key_or_name>/version/<version_id>",
    methods=["GET"],
)
def get_strategy_version_snapshot(strategy_key_or_name: str, version_id: str):
    """
    GET /api/v1/strategy/:strategy_key_or_name/version/:version_id

    V2-08：与 latest 同形，按 id 取行（无冷启动）。
    """
    versions = version_impl.lazy_load()
    try:
        row = versions.fetch_by_version(
            strategy_key_or_name=strategy_key_or_name, version_id=version_id
        )
    except ValueError as exc:
        return error(str(exc), 400)
    except FileNotFoundError as exc:
        return error(str(exc), 404)
    return ok(workbench_snapshot_to_message(row))
