from io import BytesIO

from flask import jsonify, request, send_file

from core.bff.APIs.strategy.api_base import API_BASE_PATH, strategy_api_bp
from core.bff.APIs.strategy.helpers.package_upload import read_uploaded_bytes
from core.bff.APIs.strategy.routes.package.implementer import impl
from core.bff.shared.response import error, ok

# ***********************************************
#     Strategy Package import & export
# ***********************************************


@strategy_api_bp.route(
    f"{API_BASE_PATH}/package/export/<path:strategy_key_or_name>",
    methods=["GET"],
)
def get_strategy_package_export(strategy_key_or_name: str):
    """
    GET /api/v1/strategy/package/export/:strategy_key_or_name

    ``strategy_key_or_name``: ``settings.meta.key`` 或 path name（userspace 相对路径）。
    Query ``scope``: ``bundle`` (default) | ``strategy``
    """
    pkg = impl.lazy_load()
    scope = str(request.args.get("scope") or "bundle").strip().lower()
    try:
        data, filename = pkg.export_zip(strategy_key_or_name, scope)
    except FileNotFoundError as exc:
        return error(str(exc), 404)
    except ValueError as exc:
        return error(str(exc), 400)
    except Exception as exc:
        return error(f"导出失败: {exc}", 500)

    return send_file(
        BytesIO(data),
        mimetype="application/zip",
        as_attachment=True,
        download_name=filename,
    )


@strategy_api_bp.route(
    f"{API_BASE_PATH}/package/import/preview",
    methods=["POST"],
)
def post_strategy_package_import_preview():
    """POST /api/v1/strategy/package/import/preview — multipart ``file`` + ``policy``."""
    blob, err = read_uploaded_bytes()
    if err is not None:
        return err

    pkg = impl.lazy_load()
    try:
        policy = pkg.resolve_policy(
            request.args.get("policy") or request.form.get("policy")
        )
    except ValueError as exc:
        return error(str(exc), 400)

    try:
        preview = pkg.preview_import(blob, policy)
    except Exception as exc:
        return error(f"无法解析策略包: {exc}", 400)

    return ok(preview)


@strategy_api_bp.route(
    f"{API_BASE_PATH}/package/import",
    methods=["POST"],
)
def post_strategy_package_import():
    """POST /api/v1/strategy/package/import — multipart ``file`` + ``policy``."""
    blob, err = read_uploaded_bytes()
    if err is not None:
        return err

    pkg = impl.lazy_load()
    try:
        policy = pkg.resolve_policy(
            request.args.get("policy") or request.form.get("policy")
        )
    except ValueError as exc:
        return error(str(exc), 400)

    try:
        preview, result = pkg.import_bundle(blob, policy)
    except Exception as exc:
        return error(f"无法解析策略包: {exc}", 400)

    if result is None:
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

    if not result.ok:
        return error("; ".join(result.errors) or "导入失败", 500)

    return ok(pkg.import_ok_message(preview, result))
