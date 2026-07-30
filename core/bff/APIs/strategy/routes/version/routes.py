
@strategy_api_bp.route(
    "/v1/strategy/<path:strategy_name>/version/latest",
    methods=["GET"],
)
def get_strategy_version_latest(strategy_name):
    s = get_stack()
    row = s.fetch_latest_workbench_snapshot(strategy_name)
    if row is None:
        return error("策略不存在或无法加载工作台数据", 404)
    msg = workbench_snapshot_to_message(row)
    msg.update(s.workbench_latest_ui_flags(strategy_name, row))
    return ok(msg)


@strategy_api_bp.route(
    "/v1/strategy/<path:strategy_name>/versions",
    methods=["GET"],
)
def get_strategy_versions(strategy_name):
    """GET /strategy/{strategy_name}/versions — 下拉 / 版本对比，至多 10 条。"""
    s = get_stack()
    items = s.fetch_strategy_versions_dropdown(strategy_name)
    return ok({"items": items})


@strategy_api_bp.route(
    "/v1/strategy/<path:strategy_name>/version/<version_id>",
    methods=["GET"],
)
def get_strategy_version_snapshot(strategy_name, version_id):
    """GET /strategy/{strategy_name}/version/{version_id} — 与 latest 同形，按 id 取行（无冷启动）。"""
    s = get_stack()
    sid = s.parse_version_id(version_id)
    if sid is None:
        return error("version_id 无效", 400)
    row = s.fetch_workbench_by_version(strategy_name, sid)
    if row is None:
        return error("快照不存在", 404)
    return ok(workbench_snapshot_to_message(row))




# ********************************
#     Strategy Settings
# ********************************

@strategy_api_bp.route(
    "/v1/strategy/<path:strategy_name>/apply-settings/<version_id>",
    methods=["POST"],
)
def post_apply_settings(strategy_name, version_id):
    s = get_stack()
    sid = s.parse_version_id(version_id)
    if sid is None:
        return error("version_id 无效", 400)

    payload = json_payload()
    raw_pretty = payload.get("pretty", False) if isinstance(payload, dict) else False
    pretty = raw_pretty if isinstance(raw_pretty, bool) else bool(raw_pretty)

    out, err = s.apply_workbench_snapshot_settings_to_userspace(
        strategy_name=strategy_name,
        version=sid,
        pretty=pretty,
    )
    if err:
        if err == "快照不存在":
            return error(err, 404)
        if err == "存储不可用":
            return error(err, 503)
        if err.startswith("写盘失败") or err.startswith("更新快照时间失败"):
            return error(err, 500)
        return error(err, 400)
    return ok(out)



# ********************************
#     Strategy Run Cache
# ********************************

# TODO: url need to update to /strategy/cache/clear/all
@strategy_api_bp.route(
    "/v1/strategy/workbench-snapshot-cache",
    methods=["DELETE"],
)
def delete_workbench_snapshot_cache_all():
    s = get_stack()
    out = s.clear_workbench_simulation_cache_all()
    if not out.get("ok"):
        err = str(out.get("error") or "清理失败")
        if err == "存储不可用":
            return error(err, 503)
        return error(err, 400)
    return ok(
        {
            "cleared": True,
            "deleted_count": int(out.get("deleted_count") or 0),
        }
    )

# TODO: url need to update to /strategy/cache/clear/:version_id
@strategy_api_bp.route(
    "/v1/strategy/<path:strategy_name>/version/<version_id>/workbench-snapshot-cache",
    methods=["DELETE"],
)
def delete_workbench_snapshot_cache_by_version(strategy_name, version_id):
    s = get_stack()
    sid = s.parse_version_id(version_id)
    if sid is None:
        return error("version_id 无效", 400)
    out = s.clear_workbench_simulation_cache_by_version(strategy_name, sid)
    if not out.get("ok"):
        err = str(out.get("error") or "删除失败")
        if err == "存储不可用":
            return error(err, 503)
        if err == "快照不存在":
            return error(err, 404)
        return error(err, 400)
    return ok(
        {
            "deleted": True,
            "strategy_name": out.get("strategy_name"),
            "version_id": out.get("version_id"),
        }
    )
