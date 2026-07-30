# """V2-07 / V2-07b / V2-07c — step reports & stock detail."""

# from flask import request

# from core.bff.APIs.strategy.blueprint import strategy_api_bp
# from core.bff.APIs.strategy.stack import get_stack
# from core.bff.shared.response import error, ok


# @strategy_api_bp.route(
#     "/v1/strategy/<path:strategy_name>/<step>/report/<version_id>",
#     methods=["GET"],
# )
# def get_strategy_step_report(strategy_name, step, version_id):
#     s = get_stack()
#     norm = s.normalize_step(step)
#     if norm is None:
#         return error("step 须为 enum / price / capital", 400)

#     path_vid = str(version_id or "").strip()
#     if not path_vid:
#         return error("缺少路径参数 version_id", 400)

#     sid = s.parse_version_id(path_vid)
#     if sid is None:
#         return error("version_id 无效", 400)
#     msg = s.build_step_report_message(
#         strategy_name=strategy_name,
#         normalized_step=norm,
#         version=sid,
#     )
#     if msg is None:
#         return error("快照不存在", 404)
#     return ok(msg)


# @strategy_api_bp.route(
#     "/v1/strategy/<path:strategy_name>/<step>/report_ref/<version_id>",
#     methods=["GET"],
# )
# def get_strategy_step_report_ref(strategy_name, step, version_id):
#     s = get_stack()
#     norm = s.normalize_step(step)
#     if norm is None:
#         return error("step 须为 enum / price / capital", 400)

#     path_vid = str(version_id or "").strip()
#     if not path_vid:
#         return error("缺少路径参数 version_id", 400)

#     sid = s.parse_version_id(path_vid)
#     if sid is None:
#         return error("version_id 无效", 400)
#     msg = s.build_step_report_ref_message(
#         strategy_name=strategy_name,
#         normalized_step=norm,
#         version=sid,
#     )
#     if msg is None:
#         return error("快照不存在", 404)
#     return ok(msg)


# @strategy_api_bp.route(
#     "/v1/strategy/<path:strategy_name>/<step>/stock/<path:stock_id>",
#     methods=["GET"],
# )
# def get_strategy_step_stock_detail(strategy_name, step, stock_id):
#     s = get_stack()
#     norm = s.normalize_step(step)
#     if norm is None:
#         return error("step 须为 enum / price / capital", 400)

#     path_vid = str(request.args.get("version_id") or "").strip()
#     if not path_vid:
#         return error("缺少 query 参数 version_id", 400)

#     sid = s.parse_version_id(path_vid)
#     if sid is None:
#         return error("version_id 无效", 400)

#     code = str(stock_id or "").strip()
#     if not code:
#         return error("stock_id 无效", 400)

#     msg = s.build_stock_detail_message(
#         strategy_name=strategy_name,
#         normalized_step=norm,
#         version=sid,
#         stock_id=code,
#     )
#     if msg is None:
#         return error("快照不存在", 404)
#     return ok(msg)
