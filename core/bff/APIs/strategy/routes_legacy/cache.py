# """V2-11 / V2-12 — workbench simulation cache clear."""

# from core.bff.APIs.strategy.blueprint import strategy_api_bp
# from core.bff.APIs.strategy.stack import get_stack
# from core.bff.shared.response import error, ok


# @strategy_api_bp.route(
#     "/v1/strategy/workbench-snapshot-cache",
#     methods=["DELETE"],
# )
# def delete_workbench_snapshot_cache_all():
#     s = get_stack()
#     out = s.clear_workbench_simulation_cache_all()
#     if not out.get("ok"):
#         err = str(out.get("error") or "清理失败")
#         if err == "存储不可用":
#             return error(err, 503)
#         return error(err, 400)
#     return ok(
#         {
#             "cleared": True,
#             "deleted_count": int(out.get("deleted_count") or 0),
#         }
#     )


# @strategy_api_bp.route(
#     "/v1/strategy/<path:strategy_name>/version/<version_id>/workbench-snapshot-cache",
#     methods=["DELETE"],
# )
# def delete_workbench_snapshot_cache_by_version(strategy_name, version_id):
#     s = get_stack()
#     sid = s.parse_version_id(version_id)
#     if sid is None:
#         return error("version_id 无效", 400)
#     out = s.clear_workbench_simulation_cache_by_version(strategy_name, sid)
#     if not out.get("ok"):
#         err = str(out.get("error") or "删除失败")
#         if err == "存储不可用":
#             return error(err, 503)
#         if err == "快照不存在":
#             return error(err, 404)
#         return error(err, 400)
#     return ok(
#         {
#             "deleted": True,
#             "strategy_name": out.get("strategy_name"),
#             "version_id": out.get("version_id"),
#         }
#     )
