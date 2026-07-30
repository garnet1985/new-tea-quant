# """V2-13 … V2-15 — strategy package export / import."""

# from io import BytesIO

# from flask import jsonify, request, send_file

# from core.bff.APIs.strategy.blueprint import strategy_api_bp
# from core.bff.APIs.strategy.helpers.package_upload import (
#     parse_conflict_policy,
#     read_uploaded_bytes,
# )
# from core.bff.APIs.strategy.stack import get_stack
# from core.bff.shared.response import error, ok


# @strategy_api_bp.route(
#     "/v1/strategy/<path:strategy_name>/package/export",
#     methods=["GET"],
# )
# def get_strategy_package_export(strategy_name):
#     """
#     Query ``scope``:
#     - ``bundle`` (default): strategy + resolved tag/adapter dependencies
#     - ``strategy``: strategy directory only
#     """
#     s = get_stack()
#     scope = str(request.args.get("scope") or "bundle").strip().lower()
#     name = str(strategy_name or "").strip()
#     if not name:
#         return error("strategy_name 不能为空", 400)

#     try:
#         if scope == "bundle":
#             _manifest, payload = s.export_strategy_bundle(name)
#             filename = s.bundle_filename(name)
#         elif scope == "strategy":
#             _manifest, payload = s.export_single_entity("strategy", name)
#             filename = s.single_entity_filename("strategy", name)
#         else:
#             return error(f"无效 scope={scope!r}；可选 bundle | strategy", 400)
#     except FileNotFoundError as exc:
#         return error(str(exc), 404)
#     except ValueError as exc:
#         return error(str(exc), 400)
#     except Exception as exc:
#         return error(f"导出失败: {exc}", 500)

#     if isinstance(payload, (bytes, bytearray)):
#         data = bytes(payload)
#     else:
#         data = payload.read_bytes()

#     return send_file(
#         BytesIO(data),
#         mimetype="application/zip",
#         as_attachment=True,
#         download_name=filename,
#     )


# @strategy_api_bp.route(
#     "/v1/strategy/package/import/preview",
#     methods=["POST"],
# )
# def post_strategy_package_import_preview():
#     blob, err = read_uploaded_bytes()
#     if err is not None:
#         return err

#     policy, err = parse_conflict_policy()
#     if err is not None:
#         return err

#     s = get_stack()
#     try:
#         preview = s.preview_strategy_bundle_import(blob, policy=policy)
#     except Exception as exc:
#         return error(f"无法解析策略包: {exc}", 400)

#     return ok(preview)


# @strategy_api_bp.route(
#     "/v1/strategy/package/import",
#     methods=["POST"],
# )
# def post_strategy_package_import():
#     blob, err = read_uploaded_bytes()
#     if err is not None:
#         return err

#     policy, err = parse_conflict_policy()
#     if err is not None:
#         return err

#     s = get_stack()
#     try:
#         preview = s.preview_strategy_bundle_import(blob, policy=policy)
#     except Exception as exc:
#         return error(f"无法解析策略包: {exc}", 400)

#     if not preview.get("ok"):
#         return (
#             jsonify(
#                 {
#                     "status": "error",
#                     "message": {
#                         "detail": "导入冲突：目标路径已存在",
#                         "code": "package_conflict",
#                         "preview": preview,
#                     },
#                 }
#             ),
#             409,
#         )

#     try:
#         result = s.import_strategy_bundle(blob, policy)
#     except Exception as exc:
#         return error(f"导入失败: {exc}", 500)

#     if not result.ok:
#         return error("; ".join(result.errors) or "导入失败", 500)

#     return ok(
#         {
#             "strategy_name": preview.get("strategy_name") or preview.get("entity_name"),
#             "bundle_type": preview.get("bundle_type"),
#             "policy": preview.get("policy"),
#             "installed": [
#                 {"kind": e.kind, "name": e.name, "target_relative": e.target_relative}
#                 for e in result.installed
#             ],
#             "skipped": [
#                 {"kind": e.kind, "name": e.name, "target_relative": e.target_relative}
#                 for e in result.skipped
#             ],
#         }
#     )
