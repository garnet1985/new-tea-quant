# """Scan context / readiness / trigger / progress."""

# import logging

# from flask import request

# from core.bff.APIs.strategy.blueprint import strategy_api_bp
# from core.bff.APIs.strategy.helpers.query import parse_bool_query
# from core.bff.APIs.strategy.stack import get_stack
# from core.bff.shared.response import error, ok

# logger = logging.getLogger(__name__)


# @strategy_api_bp.route("/v1/strategy/scan/context", methods=["GET"])
# def get_strategy_scan_context_route():
#     s = get_stack()
#     return ok(s.get_scan_page_context())


# @strategy_api_bp.route(
#     "/v1/strategy/<path:strategy_name>/scan",
#     methods=["GET"],
# )
# def get_strategy_scan_readiness_route(strategy_name: str):
#     s = get_stack()
#     demo = parse_bool_query(request.args.get("demo"), default=False)
#     return ok(s.get_scan_readiness(strategy_name=strategy_name, demo=demo))


# @strategy_api_bp.route(
#     "/v1/strategy/<path:strategy_name>/scan",
#     methods=["POST"],
# )
# def post_strategy_scan(strategy_name: str):
#     s = get_stack()
#     demo = parse_bool_query(request.args.get("demo"), default=False)
#     force = parse_bool_query(request.args.get("force"), default=False)
#     logger.info("[bff.scan] POST scan strategy=%s demo=%s force=%s", strategy_name, demo, force)
#     out = s.trigger_strategy_scan_run(strategy_name=strategy_name, demo=demo, force=force)
#     if not out.get("is_triggered"):
#         reason = str(out.get("reason") or "启动扫描失败")
#         status = 409 if "运行中" in reason or "扫描任务" in reason else 400
#         logger.warning(
#             "[bff.scan] trigger rejected strategy=%s demo=%s force=%s status=%s reason=%s",
#             strategy_name,
#             demo,
#             force,
#             status,
#             reason,
#         )
#         return error(reason, status)
#     logger.info(
#         "[bff.scan] triggered strategy=%s demo=%s force=%s job_id=%s",
#         strategy_name,
#         demo,
#         force,
#         out.get("job_id"),
#     )
#     return ok(
#         {
#             "is_triggered": True,
#             "job_id": out["job_id"],
#             "demo": demo,
#             "force": force,
#             "strategy_name": strategy_name,
#         }
#     )


# @strategy_api_bp.route(
#     "/v1/strategy/<path:strategy_name>/scan/progress",
#     methods=["GET"],
# )
# def get_strategy_scan_progress(strategy_name: str):
#     s = get_stack()
#     q_job = (request.args.get("job_id") or "").strip()
#     if not q_job:
#         return error("缺少必填 query 参数 job_id", 400)
#     payload = s.get_scan_progress(strategy_name=strategy_name, job_id=q_job)
#     if payload is None:
#         return error("任务不存在或与路径不匹配", 404)
#     return ok(payload)
