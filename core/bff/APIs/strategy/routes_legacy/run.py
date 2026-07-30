# """V2-05 / V2-06 / V2-06b — workbench step run + progress."""

# from flask import request

# from core.bff.APIs.strategy.blueprint import strategy_api_bp
# from core.bff.APIs.strategy.stack import get_stack
# from core.bff.shared.request import json_payload
# from core.bff.shared.response import error, ok


# @strategy_api_bp.route(
#     "/v1/strategy/<path:strategy_name>/<step>/run",
#     methods=["POST"],
# )
# def post_strategy_step_run(strategy_name, step):
#     """POST /strategy/{strategy_name}/{step}/run — 成功时务必携带返回的 ``job_id`` 轮询 progress。"""
#     s = get_stack()
#     payload = json_payload()
#     settings = payload.get("settings")
#     if settings is None or not isinstance(settings, dict):
#         return error("settings 必须为对象", 400)

#     body_name = payload.get("strategy_name")
#     if body_name is not None and str(body_name).strip() != str(strategy_name).strip():
#         return error("strategy_name 与路径不一致", 400)

#     raw_force = payload.get("force_refresh", False)
#     force_refresh = raw_force if isinstance(raw_force, bool) else bool(raw_force)

#     out = s.submit_workbench_step_via_bff_contract(
#         strategy_name=strategy_name,
#         step=step,
#         api_settings=settings,
#         force_refresh=force_refresh,
#     )
#     if out.get("is_triggered"):
#         return ok(
#             {
#                 "is_triggered": True,
#                 "job_id": out["job_id"],
#                 "run_id": out.get("run_id") or out["job_id"],
#                 "steps": out.get("steps") or [],
#             }
#         )
#     return ok({"is_triggered": False, "reason": out.get("reason", "未知错误")})


# @strategy_api_bp.route(
#     "/v1/strategy/<path:strategy_name>/run/progress",
#     methods=["GET"],
# )
# def get_strategy_run_progress(strategy_name):
#     s = get_stack()
#     q_job = (request.args.get("job_id") or "").strip()
#     if not q_job:
#         return error("缺少必填 query 参数 job_id", 400)
#     payload = s.get_run_progress(
#         strategy_name=str(strategy_name),
#         job_id=q_job,
#     )
#     if payload is None:
#         return error("未找到该 job 的编排进度", 404)
#     return ok(payload)


# @strategy_api_bp.route(
#     "/v1/strategy/<path:strategy_name>/<step>/progress",
#     methods=["GET"],
# )
# def get_strategy_step_progress(strategy_name, step):
#     """GET /strategy/{strategy_name}/{step}/progress — **必填** query ``job_id``。"""
#     s = get_stack()
#     norm = s.normalize_step(step)
#     if norm is None:
#         return error("step 须为 enum / price / capital", 400)
#     q_job = (request.args.get("job_id") or "").strip()
#     if not q_job:
#         return error("缺少必填 query 参数 job_id", 400)
#     payload = s.get_step_progress(
#         strategy_name=strategy_name,
#         normalized_step=norm,
#         job_id=q_job,
#     )
#     if payload is None:
#         return error("任务不存在或与路径不匹配", 404)
#     return ok(payload)
