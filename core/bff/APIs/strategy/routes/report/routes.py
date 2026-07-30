from core.bff.APIs.strategy.api_base import API_BASE_PATH, strategy_api_bp
from core.bff.APIs.strategy.routes.report.implementer import impl
from core.bff.shared.response import error, ok

# ***********************************************
#     Strategy Report
#
# Pattern: /v1/strategy/{target}/report/{step}/{version_id}[/ref|/stock/…]
# 含字面量 ``ref`` / ``stock`` 的路由须注册在泛化 GET 之前。
# ***********************************************


@strategy_api_bp.route(
    f"{API_BASE_PATH}/<path:strategy_key_or_name>/report/<step>/<version_id>/ref",
    methods=["GET"],
)
def get_strategy_step_report_ref(
    strategy_key_or_name: str, step: str, version_id: str
):
    """
    GET /api/v1/strategy/:strategy_key_or_name/report/:step/:version_id/ref

    枚举 / 价格逐股 ref（``entity_list.json``）。
    """
    report = impl.lazy_load()
    try:
        msg = report.build_step_report_ref(
            strategy_key_or_name=strategy_key_or_name,
            step=step,
            version_id=version_id,
        )
    except ValueError as exc:
        return error(str(exc), 400)
    except FileNotFoundError as exc:
        return error(str(exc), 404)
    return ok(msg)


@strategy_api_bp.route(
    f"{API_BASE_PATH}/<path:strategy_key_or_name>/report/<step>/<version_id>/stock/<stock_id>",
    methods=["GET"],
)
def get_strategy_step_stock_detail(
    strategy_key_or_name: str, step: str, version_id: str, stock_id: str
):
    """
    GET /api/v1/strategy/:strategy_key_or_name/report/:step/:version_id/stock/:stock_id

    单股 K 线 + markers。
    """
    report = impl.lazy_load()
    try:
        msg = report.build_stock_detail(
            strategy_key_or_name=strategy_key_or_name,
            step=step,
            version_id=version_id,
            stock_id=stock_id,
        )
    except ValueError as exc:
        return error(str(exc), 400)
    except FileNotFoundError as exc:
        return error(str(exc), 404)
    return ok(msg)


@strategy_api_bp.route(
    f"{API_BASE_PATH}/<path:strategy_key_or_name>/report/<step>/<version_id>",
    methods=["GET"],
)
def get_strategy_step_report(
    strategy_key_or_name: str, step: str, version_id: str
):
    """
    GET /api/v1/strategy/:strategy_key_or_name/report/:step/:version_id

    ``step``: ``WorkbenchStep``（enum | price | portfolio）；
    ``strategy_key_or_name``: meta.key 或 path name。
    """
    report = impl.lazy_load()
    try:
        msg = report.build_step_report(
            strategy_key_or_name=strategy_key_or_name,
            step=step,
            version_id=version_id,
        )
    except ValueError as exc:
        return error(str(exc), 400)
    except FileNotFoundError as exc:
        return error(str(exc), 404)
    return ok(msg)
