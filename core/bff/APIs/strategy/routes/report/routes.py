from core.bff.APIs.strategy.api_base import API_BASE_PATH, strategy_api_bp
from core.bff.APIs.strategy.routes.report.implementer import impl
from core.bff.shared.response import error, ok

# ***********************************************
#     Strategy Report
# ***********************************************
#
# ``strategy_key_or_name`` 一律放路径末尾（``<path:>``），与 package/export 一致。
# 含字面量 ``ref`` / ``stock`` 的路由须注册在泛化 GET 之前。


@strategy_api_bp.route(
    f"{API_BASE_PATH}/report/<step>/<version_id>/ref/<path:strategy_key_or_name>",
    methods=["GET"],
)
def get_strategy_step_report_ref(
    step: str, version_id: str, strategy_key_or_name: str
):
    """
    GET /api/v1/strategy/report/:step/:version_id/ref/:strategy_key_or_name

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
    f"{API_BASE_PATH}/report/<step>/<version_id>/stock/<stock_id>/<path:strategy_key_or_name>",
    methods=["GET"],
)
def get_strategy_step_stock_detail(
    step: str, version_id: str, stock_id: str, strategy_key_or_name: str
):
    """
    GET /api/v1/strategy/report/:step/:version_id/stock/:stock_id/:strategy_key_or_name

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
    f"{API_BASE_PATH}/report/<step>/<version_id>/<path:strategy_key_or_name>",
    methods=["GET"],
)
def get_strategy_step_report(step: str, version_id: str, strategy_key_or_name: str):
    """
    GET /api/v1/strategy/report/:step/:version_id/:strategy_key_or_name

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
