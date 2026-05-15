"""
升级「应用阶段」流水线。

**为何放在 ``userspace/updater``（发版源树见仓库根 ``setup/updater/``）：**

- **不能放在 ``core/``**：镜像时会覆盖 ``core/``，进程自身正在加载其中的模块，易导致文件占用。
- **不能放在 ``setup/``**：``setup/`` 也可能纳入 ``managed_scope``，覆盖时同样会换掉正在执行的脚本。
- **应放在 ``userspace/updater``**：通常不在发行 zip 的替换范围内；随 **init userspace** 解压到用户目录后长期存在。

版本探测（仅 GET 远端 ``system.json``）可由旧版 launcher/BFF 调用；**写盘升级**须在本模块所在路径执行（或单独子进程）。

约定摘要（详见 ``userspace/updater/README.md``）：
- 以新版 zip + ``managed_scope`` 对管辖路径做递归镜像；管辖外不动。
- **数据库迁移用的旧版期望 schema** 须在 ``_update_managed_scope`` **之前** 固化（见 ``_snapshot_core_table_schemas_before_managed_scope``）；收尾顺序：安装依赖 → 数据库迁移。
"""
from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import helper

# 供外部或测试引用时与 helper 一致（可选从 helper 再导出）
REMOTE_REPO = helper.REMOTE_REPO
VERSION_FILE = helper.VERSION_FILE
UPDATE_PLAN_FILE = helper.UPDATE_PLAN_FILE
REQUEST_TIMEOUT_SEC = helper.REQUEST_TIMEOUT_SEC
ZIP_DOWNLOAD_TIMEOUT_SEC = helper.ZIP_DOWNLOAD_TIMEOUT_SEC
PIPELINE_STEP_TOTAL = helper.PIPELINE_STEP_TOTAL

# CLI / 后续 UI 可调用的依赖安装接口（实现均在 ``helper``）
reinstall_runtime_dependencies_cli = helper.reinstall_runtime_dependencies_cli
python_for_repo_commands = helper.python_for_repo_commands
repo_venv_python = helper.repo_venv_python


@dataclass
class UpgradeContext:
    """单次升级所需上下文（字段随实现扩展）。"""

    repo_root: Path
    staging_dir: Optional[Path] = None
    zip_path: Optional[Path] = None
    update_plan: Optional[Dict[str, Any]] = None
    lift_out_backup_dir: Optional[Path] = None
    pre_mirror_schema_snapshot_path: Optional[Path] = None
    database_migration: Optional[helper.DatabaseMigrationResult] = None
    post_upgrade: Optional[helper.PostUpgradeResult] = None
    cleanup: Optional[helper.UpgradeCleanupResult] = None


def check_remote_has_newer_version(repo_root: Path) -> Optional[str]:
    """
    探测远端是否有比本地更新的版本。

    1. 按 ``REMOTE_REPO`` 顺序用 ``VERSION_FILE`` 拼 raw URL（先 Gitee，后 GitHub）。
    2. 先请求 Gitee，超时或失败再请求 GitHub。
    3. 全部失败或无法解析 ``version`` 时 **静默** 返回 ``None``；若有远端版本且 **严格大于** 本地，返回远端版本字符串。

    分支名由环境变量 ``NTQ_REMOTE_REF`` 指定，未设置时默认 ``helper.DEFAULT_REMOTE_REF``。
    单次 HTTP 超时由 ``NTQ_UPDATE_CHECK_TIMEOUT``（秒）控制，见 ``helper.REQUEST_TIMEOUT_SEC``。

    开发/测试绕过 HTTP：``NTQ_UPDATE_FORCE_NEWER_VERSION``、``NTQ_UPDATE_FORCE_RUN``（见 ``helper.dev_force_newer_version``）。
    """
    local_ver = helper.read_local_version(repo_root)
    if local_ver is None:
        return None

    dev_newer = helper.dev_force_newer_version(local_ver)
    if dev_newer is not None:
        return dev_newer

    ref = helper.default_remote_ref()
    for base in helper.REMOTE_REPO:
        url = helper.raw_system_json_url(base, ref, helper.VERSION_FILE)
        if not url:
            continue
        remote = helper.http_get_json(url, helper.REQUEST_TIMEOUT_SEC)
        if remote is None:
            continue
        remote_ver = helper.extract_version_string(remote)
        if remote_ver is None:
            continue
        if helper.semver_gt(remote_ver, local_ver):
            return remote_ver
        return None

    return None


def run_upgrade_pipeline(ctx: UpgradeContext) -> None:
    """
    应用升级：自洽的一条龙编排（须在 **停掉主应用** 后调用）。

    大步骤顺序见本仓库 ``userspace/updater/README.md`` §8。
    """
    helper.pipeline_step_begin(1, "正在获取更新包")
    _download_latest_version_package(ctx)
    helper.pipeline_step_done(1, f"更新包已就绪（{ctx.zip_path}）")

    helper.pipeline_step_begin(2, "正在解压更新包到临时目录")
    _extract_zip_to_staging(ctx)
    helper.pipeline_step_done(2, f"已解压到 {ctx.staging_dir}")

    helper.pipeline_step_begin(3, "正在读取升级计划（managed_scope）")
    _load_update_plan(ctx)
    managed_count = len(ctx.update_plan.get("managed_scope", [])) if ctx.update_plan else 0
    helper.pipeline_step_done(3, f"共 {managed_count} 项待更新")

    helper.pipeline_step_begin(4, "正在停止运行中的应用")
    _kill_running_app(ctx)
    helper.pipeline_step_done(4, "已尝试停止主进程（未配置停服钩子时跳过）")

    helper.pipeline_step_begin(5, "正在备份需保留的用户数据（lift-out）")
    _backup_exceptions(ctx)
    if ctx.lift_out_backup_dir is not None:
        helper.pipeline_step_done(5, f"已备份至 {ctx.lift_out_backup_dir}")
    else:
        helper.pipeline_step_done(5, "无需备份的路径")

    helper.pipeline_step_begin(6, "正在快照数据库表结构（供迁移对照）")
    _snapshot_core_table_schemas_before_managed_scope(ctx)
    if ctx.pre_mirror_schema_snapshot_path is not None:
        helper.pipeline_step_done(6, f"快照已保存（{ctx.pre_mirror_schema_snapshot_path}）")
    else:
        helper.pipeline_step_done(6, "已跳过 schema 快照")

    helper.pipeline_step_begin(7, "正在将新版本文件写入仓库（镜像 managed_scope）")
    _update_managed_scope(ctx)
    helper.pipeline_step_done(7, "核心文件已更新")

    helper.pipeline_step_begin(8, "正在还原 lift-out 备份")
    _restore_exceptions(ctx)
    if ctx.lift_out_backup_dir is not None:
        helper.pipeline_step_done(8, "用户数据已还原")
    else:
        helper.pipeline_step_done(8, "无备份需还原")

    helper.pipeline_step_begin(9, "正在重装运行依赖（pip / UI）")
    if helper._env_truthy("NTQ_UPDATE_SKIP_RUNTIME_REINSTALL"):
        helper.pipeline_step_done(9, "已跳过（NTQ_UPDATE_SKIP_RUNTIME_REINSTALL）")
    else:
        _reinstall_dependencies(ctx)
        helper.pipeline_step_done(9, "运行依赖已重装")

    helper.pipeline_step_begin(10, "正在执行数据库迁移")
    _run_database_migrations(ctx)
    mig = ctx.database_migration
    if mig is not None and mig.skipped:
        reason = mig.skipped_reason or "已跳过"
        helper.pipeline_step_done(10, reason)
    elif mig is not None and mig.log_path is not None:
        helper.pipeline_step_done(10, f"迁移完成，日志 {mig.log_path}")
    else:
        helper.pipeline_step_done(10, "迁移完成")

    helper.pipeline_step_begin(11, "正在执行升级后收尾动作")
    _trigger_core_extra_actions(ctx)
    pu = ctx.post_upgrade
    if pu is not None and pu.skipped:
        reason = pu.skipped_reason or "无注册动作，已跳过"
        helper.pipeline_step_done(11, reason)
    elif pu is not None and pu.executed_count:
        helper.pipeline_step_done(11, f"已执行 {pu.executed_count} 项收尾动作")
    else:
        helper.pipeline_step_done(11, "收尾完成")

    helper.pipeline_step_begin(12, "正在清理临时文件")
    _cleanup_staging(ctx)
    cleanup = ctx.cleanup
    if cleanup is not None and cleanup.skipped:
        helper.pipeline_step_done(12, cleanup.skipped_reason or "已跳过清理")
    elif cleanup is not None and cleanup.removed_paths:
        helper.pipeline_step_done(12, f"已清理 {len(cleanup.removed_paths)} 处临时文件")
    else:
        helper.pipeline_step_done(12, "无需清理的临时文件")


def _trigger_core_extra_actions(ctx: UpgradeContext) -> None:
    """
    主流程结束后，子进程执行新版 ``core/infra/update/post_upgrade`` 已注册的收尾动作。

    用于 updater 在主镜像阶段无法安全完成的「反向」写盘（如同步 ``userspace/updater``）。
    注册表为空则跳过；结果写入 ``ctx.post_upgrade``。
    跳过整步：``NTQ_UPDATE_SKIP_POST_UPGRADE=1``。
    """
    ctx.post_upgrade = helper.spawn_post_upgrade_actions_cli(ctx.repo_root)


def _download_latest_version_package(ctx: UpgradeContext) -> None:
    """
    从 ``REMOTE_REPO`` 按顺序下载 **与 ``NTQ_REMOTE_REF`` 一致的分支** 的源码 zip（Gitee → GitHub），
    写入 ``userspace/.ntq/update/inbox/ntq-src-<ref>.zip``，并设置 ``ctx.zip_path``。

    若调用方已设置 ``ctx.zip_path`` 且文件存在，则跳过下载。
    开发/测试：``NTQ_UPDATE_LOCAL_ZIP`` 使用本地 zip（见 ``helper.dev_local_zip_path``）。
    全部远端失败时抛出 ``RuntimeError``。
    """
    if ctx.zip_path is not None and ctx.zip_path.is_file():
        helper.pipeline_step_note(f"使用已有更新包：{ctx.zip_path}")
        return

    local_zip = helper.dev_local_zip_path()
    if local_zip is not None:
        helper.pipeline_step_note(f"使用本地 zip：{local_zip}")
        ctx.zip_path = local_zip
        return

    ref = helper.default_remote_ref()
    inbox = helper.update_bundle_dir(ctx.repo_root) / "inbox"
    inbox.mkdir(parents=True, exist_ok=True)
    dest = inbox / f"ntq-src-{ref}.zip"

    for base in helper.REMOTE_REPO:
        label = helper.remote_repo_label(base)
        helper.pipeline_step_note(f"正在从 {label} 获取更新包（分支 {ref}）…")
        ok, reason = helper.download_branch_archive_zip(
            base,
            ref,
            dest,
            timeout_sec=helper.ZIP_DOWNLOAD_TIMEOUT_SEC,
        )
        if ok:
            ctx.zip_path = dest
            return
        helper.pipeline_step_note(f"{label} 失败：{reason}；尝试下一镜像…")

    raise RuntimeError(
        "NTQ updater: 无法从任何镜像获取分支 zip。"
        "Gitee 不支持 GitHub 风格 /archive/{branch}.zip；可设置 NTQ_GITEE_ACCESS_TOKEN，"
        "或使用 NTQ_UPDATE_LOCAL_ZIP / git 回退。"
    )


def _extract_zip_to_staging(ctx: UpgradeContext) -> None:
    """
    将 ``ctx.zip_path`` 解压到 ``userspace/.ntq/update/staging/current``，
    并把 ``ctx.staging_dir`` 设为 zip 内仓库根（单层 ``repo-ref/`` 时进入该子目录）。
    """
    z = ctx.zip_path
    if z is None or not z.is_file():
        raise RuntimeError("NTQ updater: zip_path is missing or not a file")

    root = helper.update_bundle_dir(ctx.repo_root)
    extract_parent = root / "staging" / "current"
    if extract_parent.exists():
        shutil.rmtree(extract_parent)
    extract_parent.mkdir(parents=True, exist_ok=True)

    try:
        helper.safe_extract_zip(z.resolve(), extract_parent)
        ctx.staging_dir = helper.resolve_archive_root(extract_parent)
    except Exception:
        if extract_parent.exists():
            shutil.rmtree(extract_parent, ignore_errors=True)
        raise


def _load_update_plan(ctx: UpgradeContext) -> None:
    """
    从 ``ctx.staging_dir`` 读取 ``update_plan.json``；若无则读 ``core/system.json`` 中的 ``update_plan``
    （与 ``SystemMeta`` 回退规则一致），校验后写入 ``ctx.update_plan``。
    """
    if ctx.staging_dir is None or not ctx.staging_dir.is_dir():
        raise RuntimeError("NTQ updater: staging_dir is missing before load_update_plan")
    ctx.update_plan = helper.load_update_plan_from_staging(ctx.staging_dir)


def _snapshot_core_table_schemas_before_managed_scope(ctx: UpgradeContext) -> None:
    """
    在 ``_update_managed_scope`` 覆盖或删除 ``core/`` 下文件 **之前**，把当前 ``core/tables`` 全量
    schema 写入 ``userspace/.ntq/update/cache/``；否则镜像后无法再读取升级前的代码期望。

    结果路径写入 ``ctx.pre_mirror_schema_snapshot_path``（跳过或未写入时为 ``None``）。
    """
    ctx.pre_mirror_schema_snapshot_path = helper.snapshot_core_table_schemas_for_migration(
        ctx.repo_root
    )


def _backup_exceptions(ctx: UpgradeContext) -> None:
    """
    **Lift-out**：对 ``update_ignored_paths`` 中落在 ``managed_scope`` 前缀下的已存在路径，
    在 ``_update_managed_scope`` 之前复制到 ``userspace/.ntq/update/lift-out/<UTC>/``，
    并写入 ``lift_out_manifest.json``；路径记在 ``ctx.lift_out_backup_dir``（无则 ``None``）。

    跳过位于 ``userspace/.ntq/update`` 下的路径，避免把缓存/ staging 拷进备份。
    """
    if ctx.update_plan is None:
        raise RuntimeError("NTQ updater: update_plan is missing before backup_exceptions")
    ctx.lift_out_backup_dir = helper.run_lift_out_backup(
        ctx.repo_root,
        ctx.update_plan["managed_scope"],
        ctx.update_plan["update_ignored_paths"],
    )


def _update_managed_scope(ctx: UpgradeContext) -> None:
    """
    **编排**：读旧/新 ``managed_scope`` → 删「已退出 map」的顶层项 → 对新表逐项删后从 staging 拷贝。

    单项语义为 **整棵目录或单个文件** 替换（无细粒度 merge）；全局保留名见 ``helper.is_global_preserve_managed_entry``。
    """
    _managed_scope_require_context(ctx)
    old_ms = _managed_scope_read_old(ctx)
    new_ms = _managed_scope_read_new(ctx)
    _managed_scope_remove_obsolete_top_levels(ctx, old_ms, new_ms)
    _managed_scope_install_each_from_staging(ctx, new_ms)


def _managed_scope_require_context(ctx: UpgradeContext) -> None:
    if ctx.staging_dir is None or not ctx.staging_dir.is_dir():
        raise RuntimeError("NTQ updater: staging_dir is missing before managed_scope update")
    if ctx.update_plan is None:
        raise RuntimeError("NTQ updater: update_plan is missing before managed_scope update")


def _managed_scope_read_old(ctx: UpgradeContext) -> List[str]:
    """升级前本地 ``core/system.json`` 中的 ``managed_scope``（可能为空）。"""
    return helper.read_managed_scope_from_repo(ctx.repo_root)


def _managed_scope_read_new(ctx: UpgradeContext) -> List[str]:
    """新版 ``update_plan`` 中的 ``managed_scope``（已由 ``_load_update_plan`` 校验）。"""
    return list(ctx.update_plan["managed_scope"])


def _managed_scope_remove_obsolete_top_levels(
    ctx: UpgradeContext, old_ms: List[str], new_ms: List[str]
) -> None:
    """旧 map 有、新 map 无的顶层路径整项删除（全局保留跳过）。"""
    helper.remove_obsolete_managed_top_levels(ctx.repo_root, old_ms, new_ms)


def _managed_scope_install_each_from_staging(ctx: UpgradeContext, new_ms: List[str]) -> None:
    """对新 map 每一项：删本地同名路径，再从 staging（含 ``payload_root``）覆盖拷贝。"""
    staging_dir = ctx.staging_dir
    plan = ctx.update_plan
    if staging_dir is None or plan is None:
        raise RuntimeError("NTQ updater: internal error, managed_scope context incomplete")
    helper.install_managed_items_from_staging(
        ctx.repo_root,
        staging_dir,
        plan["payload_root"],
        new_ms,
    )


def _restore_exceptions(ctx: UpgradeContext) -> None:
    """
    将 ``_backup_exceptions`` 产生的 lift-out 按 ``lift_out_manifest.json`` **覆盖还原**到 ``repo_root``。

    ``ctx.lift_out_backup_dir`` 为 ``None``（未备份）时直接返回。
    """
    if ctx.lift_out_backup_dir is None:
        return
    helper.run_lift_out_restore(ctx.repo_root, ctx.lift_out_backup_dir)


def _reinstall_dependencies(ctx: UpgradeContext) -> None:
    """
    **纯命令行** 重装运行期依赖（与后续 UI update 向导共用底层实现）。

    调用 ``reinstall_runtime_dependencies_cli``：可选根 ``requirements.txt``，再
    ``setup.ui_runtime.install_ui_runtime(force=True)``（BFF + FED）。

    调试跳过：``NTQ_UPDATE_SKIP_RUNTIME_REINSTALL=1``；仅跳过根 requirements：
    ``NTQ_UPDATE_SKIP_ROOT_REQUIREMENTS=1``。
    """
    if helper._env_truthy("NTQ_UPDATE_SKIP_ROOT_REQUIREMENTS"):
        helper.pipeline_step_note("跳过根目录 requirements.txt（NTQ_UPDATE_SKIP_ROOT_REQUIREMENTS）")
    else:
        helper.pipeline_step_note("正在 pip install -r requirements.txt …")
    helper.pipeline_step_note("正在安装 UI 运行依赖（BFF / FED）…")
    helper.reinstall_runtime_dependencies_cli(ctx.repo_root, force=True)


def _run_database_migrations(ctx: UpgradeContext) -> None:
    """
    子进程调用 ``core.infra.db.migrate apply``（见 ``helper.spawn_database_migration_cli``）。

    使用 ``ctx.pre_mirror_schema_snapshot_path``；无快照时默认 **失败**（见
    ``NTQ_UPDATE_ALLOW_MISSING_SCHEMA_SNAPSHOT``）。结果写入 ``ctx.database_migration``。
    跳过整步：``NTQ_UPDATE_SKIP_DB_MIGRATION=1``。
    """
    helper.pipeline_step_note("正在调用 core.infra.db.migrate apply …")
    ctx.database_migration = helper.spawn_database_migration_cli(
        ctx.repo_root,
        ctx.pre_mirror_schema_snapshot_path,
    )


def _cleanup_staging(ctx: UpgradeContext) -> None:
    """
    清理本次升级在 ``userspace/.ntq/update`` 下产生的临时文件（staging、inbox zip、lift-out 等）。

    结果写入 ``ctx.cleanup``；并清空 ``ctx.staging_dir`` / ``ctx.zip_path``。
    跳过：``NTQ_UPDATE_SKIP_CLEANUP=1``；保留项见 ``helper.cleanup_after_upgrade`` 文档。
    """
    ctx.cleanup = helper.cleanup_after_upgrade(
        ctx.repo_root,
        staging_dir=ctx.staging_dir,
        zip_path=ctx.zip_path,
        lift_out_backup_dir=ctx.lift_out_backup_dir,
        pre_mirror_snapshot_path=ctx.pre_mirror_schema_snapshot_path,
    )
    ctx.staging_dir = None
    ctx.zip_path = None


def _kill_running_app(ctx: UpgradeContext) -> None:
    """
    通过环境变量钩子尝试停主进程（见 ``helper.kill_main_app_hooks``）。

    未配置任何钩子时 **no-op**：由 launcher 在调用流水线前停服，或配置 ``NTQ_UPDATE_KILL_CMD`` /
    ``NTQ_UPDATE_STOP_URL`` / ``NTQ_UPDATE_PID_FILE`` / ``NTQ_UPDATE_MAIN_PIDS``。
    """
    helper.kill_main_app_hooks(ctx.repo_root)
