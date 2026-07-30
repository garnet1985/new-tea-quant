



@strategy_api_bp.route(
    "/v1/strategy/<path:strategy_name>/<step>/run",
    methods=["POST"],
)
def post_strategy_step_run(strategy_name, step):
    """POST /strategy/{strategy_name}/{step}/run — 成功时务必携带返回的 ``job_id`` 轮询 progress。"""
    s = get_stack()
    payload = json_payload()
    settings = payload.get("settings")
    if settings is None or not isinstance(settings, dict):
        return error("settings 必须为对象", 400)

    body_name = payload.get("strategy_name")
    if body_name is not None and str(body_name).strip() != str(strategy_name).strip():
        return error("strategy_name 与路径不一致", 400)

    raw_force = payload.get("force_refresh", False)
    force_refresh = raw_force if isinstance(raw_force, bool) else bool(raw_force)

    out = s.submit_workbench_step_via_bff_contract(
        strategy_name=strategy_name,
        step=step,
        api_settings=settings,
        force_refresh=force_refresh,
    )
    if out.get("is_triggered"):
        return ok(
            {
                "is_triggered": True,
                "job_id": out["job_id"],
                "run_id": out.get("run_id") or out["job_id"],
                "steps": out.get("steps") or [],
            }
        )
    return ok({"is_triggered": False, "reason": out.get("reason", "未知错误")})


@strategy_api_bp.route(
    "/v1/strategy/<path:strategy_name>/run/progress",
    methods=["GET"],
)
def get_strategy_run_progress(strategy_name):
    s = get_stack()
    q_job = (request.args.get("job_id") or "").strip()
    if not q_job:
        return error("缺少必填 query 参数 job_id", 400)
    payload = s.get_run_progress(
        strategy_name=str(strategy_name),
        job_id=q_job,
    )
    if payload is None:
        return error("未找到该 job 的编排进度", 404)
    return ok(payload)


@strategy_api_bp.route(
    "/v1/strategy/<path:strategy_name>/<step>/progress",
    methods=["GET"],
)
def get_strategy_step_progress(strategy_name, step):
    """GET /strategy/{strategy_name}/{step}/progress — **必填** query ``job_id``。"""
    s = get_stack()
    norm = s.normalize_step(step)
    if norm is None:
        return error("step 须为 enum / price / capital", 400)
    q_job = (request.args.get("job_id") or "").strip()
    if not q_job:
        return error("缺少必填 query 参数 job_id", 400)
    payload = s.get_step_progress(
        strategy_name=strategy_name,
        normalized_step=norm,
        job_id=q_job,
    )
    if payload is None:
        return error("任务不存在或与路径不匹配", 404)
    return ok(payload)


@strategy_api_bp.route("/v1/strategy/scan/context", methods=["GET"])
def get_strategy_scan_context_route():
    s = get_stack()
    return ok(s.get_scan_page_context())


@strategy_api_bp.route(
    "/v1/strategy/<path:strategy_name>/scan",
    methods=["GET"],
)
def get_strategy_scan_readiness_route(strategy_name: str):
    s = get_stack()
    demo = parse_bool_query(request.args.get("demo"), default=False)
    return ok(s.get_scan_readiness(strategy_name=strategy_name, demo=demo))


@strategy_api_bp.route(
    "/v1/strategy/<path:strategy_name>/scan",
    methods=["POST"],
)
def post_strategy_scan(strategy_name: str):
    s = get_stack()
    demo = parse_bool_query(request.args.get("demo"), default=False)
    force = parse_bool_query(request.args.get("force"), default=False)
    logger.info("[bff.scan] POST scan strategy=%s demo=%s force=%s", strategy_name, demo, force)
    out = s.trigger_strategy_scan_run(strategy_name=strategy_name, demo=demo, force=force)
    if not out.get("is_triggered"):
        reason = str(out.get("reason") or "启动扫描失败")
        status = 409 if "运行中" in reason or "扫描任务" in reason else 400
        logger.warning(
            "[bff.scan] trigger rejected strategy=%s demo=%s force=%s status=%s reason=%s",
            strategy_name,
            demo,
            force,
            status,
            reason,
        )
        return error(reason, status)
    logger.info(
        "[bff.scan] triggered strategy=%s demo=%s force=%s job_id=%s",
        strategy_name,
        demo,
        force,
        out.get("job_id"),
    )
    return ok(
        {
            "is_triggered": True,
            "job_id": out["job_id"],
            "demo": demo,
            "force": force,
            "strategy_name": strategy_name,
        }
    )


@strategy_api_bp.route(
    "/v1/strategy/<path:strategy_name>/scan/progress",
    methods=["GET"],
)
def get_strategy_scan_progress(strategy_name: str):
    s = get_stack()
    q_job = (request.args.get("job_id") or "").strip()
    if not q_job:
        return error("缺少必填 query 参数 job_id", 400)
    payload = s.get_scan_progress(strategy_name=strategy_name, job_id=q_job)
    if payload is None:
        return error("任务不存在或与路径不匹配", 404)
    return ok(payload)

