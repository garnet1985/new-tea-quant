# """V2-09 — apply snapshot settings to userspace settings.py."""

# from core.bff.APIs.strategy.blueprint import strategy_api_bp
# from core.bff.APIs.strategy.stack import get_stack
# from core.bff.shared.request import json_payload
# from core.bff.shared.response import error, ok


# @strategy_api_bp.route(
#     "/v1/strategy/<path:strategy_name>/apply-settings/<version_id>",
#     methods=["POST"],
# )
# def post_apply_settings(strategy_name, version_id):
#     s = get_stack()
#     sid = s.parse_version_id(version_id)
#     if sid is None:
#         return error("version_id 无效", 400)

#     payload = json_payload()
#     raw_pretty = payload.get("pretty", False) if isinstance(payload, dict) else False
#     pretty = raw_pretty if isinstance(raw_pretty, bool) else bool(raw_pretty)

#     out, err = s.apply_workbench_snapshot_settings_to_userspace(
#         strategy_name=strategy_name,
#         version=sid,
#         pretty=pretty,
#     )
#     if err:
#         if err == "快照不存在":
#             return error(err, 404)
#         if err == "存储不可用":
#             return error(err, 503)
#         if err.startswith("写盘失败") or err.startswith("更新快照时间失败"):
#             return error(err, 500)
#         return error(err, 400)
#     return ok(out)
