from core.bff.APIs.strategy.api_base import API_BASE_PATH, strategy_api_bp
from core.bff.APIs.strategy.routes.folder.implementer import impl as folder_impl
from core.bff.shared.response import error, ok


@strategy_api_bp.route(
    f"{API_BASE_PATH}/<path:strategy_key_or_name>/folder/reveal",
    methods=["POST"],
)
def post_strategy_folder_reveal(strategy_key_or_name: str):
    """
    POST /api/v1/strategy/:strategy_key_or_name/folder/reveal

    在运行 BFF 的机器上打开策略目录（Finder / Explorer / 文件管理器）。
    仅允许 ``userspace/strategies/`` 下的已解析目录。
    """
    folders = folder_impl.lazy_load()
    try:
        out = folders.reveal(strategy_key_or_name)
    except ValueError as exc:
        return error(str(exc), 400)
    except FileNotFoundError as exc:
        return error(str(exc), 404)
    except Exception as exc:
        return error(f"无法打开文件夹: {exc}", 500)
    return ok(out)
