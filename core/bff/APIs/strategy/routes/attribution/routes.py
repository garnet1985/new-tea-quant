from flask import request

from core.bff.APIs.strategy.api_base import API_BASE_PATH, strategy_api_bp
from core.bff.APIs.strategy.routes.attribution.implementer import impl as attr_impl
from core.bff.shared.request import json_payload
from core.bff.shared.response import error, ok

# ***********************************************
#     Strategy Attribution (campaign sea/spa/soa)
#
# A1-00 status · A1-01 run · A1-02 progress · A1-04 report
# ***********************************************


@strategy_api_bp.route(
    f"{API_BASE_PATH}/<path:strategy_key_or_name>/attribute/run/progress",
    methods=["GET"],
)
def get_strategy_attribute_run_progress(strategy_key_or_name: str):
    """
    GET /api/v1/strategy/:strategy_key_or_name/attribute/run/progress?job_id=

    A1-02：归因编排进度（对标 V2-06b）。
    """
    attr = attr_impl.lazy_load()
    q_job = (request.args.get("job_id") or "").strip()
    if not q_job:
        return error("缺少必填 query 参数 job_id", 400)
    try:
        payload = attr.get_run_progress(
            strategy_key_or_name=strategy_key_or_name, job_id=q_job
        )
    except ValueError as exc:
        return error(str(exc), 400)
    except FileNotFoundError as exc:
        return error(str(exc), 404)
    if payload is None:
        return error("未找到该 job 的归因进度", 404)
    return ok(payload)


@strategy_api_bp.route(
    f"{API_BASE_PATH}/<path:strategy_key_or_name>/<step>/attribute/status",
    methods=["GET"],
)
def get_strategy_attribute_status(strategy_key_or_name: str, step: str):
    """
    GET /api/v1/strategy/:strategy_key_or_name/:step/attribute/status

    A1-00：按钮显隐 / enable。
    """
    attr = attr_impl.lazy_load()
    try:
        return ok(
            attr.status(strategy_key_or_name=strategy_key_or_name, step=step)
        )
    except ValueError as exc:
        return error(str(exc), 400)
    except FileNotFoundError as exc:
        return error(str(exc), 404)


@strategy_api_bp.route(
    f"{API_BASE_PATH}/<path:strategy_key_or_name>/<step>/attribute/run",
    methods=["POST"],
)
def post_strategy_attribute_run(strategy_key_or_name: str, step: str):
    """
    POST /api/v1/strategy/:strategy_key_or_name/:step/attribute/run

    A1-01：启动本层归因战役。
    """
    attr = attr_impl.lazy_load()
    payload = json_payload()
    raw_force = payload.get("force_refresh", payload.get("is_force", False))
    force_refresh = raw_force if isinstance(raw_force, bool) else bool(raw_force)
    try:
        out = attr.submit_run(
            strategy_key_or_name=strategy_key_or_name,
            step=step,
            force_refresh=force_refresh,
        )
    except ValueError as exc:
        return error(str(exc), 400)
    except FileNotFoundError as exc:
        return error(str(exc), 404)

    if out.get("is_triggered"):
        return ok(
            {
                "is_triggered": True,
                "job_id": out["job_id"],
                "run_id": out.get("run_id") or out["job_id"],
                "pipeline_id": out.get("pipeline_id") or out["job_id"],
                "pipeline_name": out.get("pipeline_name"),
                "pipeline_kind": out.get("pipeline_kind") or "attribute",
                "pipeline_description": out.get("pipeline_description"),
            }
        )
    reason = str(out.get("reason") or "启动归因失败")
    status = 409 if "运行中" in reason or "系统任务" in reason else 400
    return error(reason, status)


@strategy_api_bp.route(
    f"{API_BASE_PATH}/<path:strategy_key_or_name>/attribute/report/<step>/<group_id>",
    methods=["GET"],
)
def get_strategy_attribute_report(
    strategy_key_or_name: str, step: str, group_id: str
):
    """
    GET /api/v1/strategy/:strategy_key_or_name/attribute/report/:step/:group_id

    A1-04：读取已落盘战役报告。
    """
    attr = attr_impl.lazy_load()
    try:
        return ok(
            attr.build_report(
                strategy_key_or_name=strategy_key_or_name,
                step=step,
                group_id=group_id,
            )
        )
    except ValueError as exc:
        return error(str(exc), 400)
    except FileNotFoundError as exc:
        return error(str(exc), 404)
