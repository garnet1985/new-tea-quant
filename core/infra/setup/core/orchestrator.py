"""Setup 编排：统一协调安装步骤与全局状态（CLI / UI 入口）。

CLI：``install_cli_runtime`` / ``ensure_cli_install_via_install_py`` / ``CliInstallOptions``
UI：``install_ui_runtime`` / ``check_runtime_prerequisites`` / ``launch_ui_stack``
全局步骤状态见 ``core.infra.setup.core.shared.setup_session``。
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.infra.cmd_layout import CmdLayout
from core.infra.utils import Utils
from core.system import python_minimum
from core.ui.ports import ALL_UI_PORTS, UI_BFF_PORT, UI_DEV_PORT
from core.ui.process_cleanup import (
    install_interrupt_force_exit,
    interrupt_requested,
    kill_process_group,
    pids_listening_on,
    process_cmdline,
    windows_new_process_group_flag,
)

from core.infra.setup.core.shared import setup_session
from core.infra.setup.core.shared.env import NewTeaQuantSetup
from core.infra.setup.core.shared.install_progress import (
    begin_install_step,
    close_install,
    fail_install,
    finish_install_step,
    open_install,
)
from core.infra.setup.core.shared.install_runtime import (
    REPO_ROOT,
    UI_BFF_REQUIREMENTS,
    UI_FED_BUILD_DIR,
    UI_FED_LOCKFILE,
    UI_FED_ROOT,
    fed_build_fingerprint,
    fed_build_ready,
    mark_cli_success_fingerprint,
    mark_runtime,
    needs_install,
    python_env_id,
    sha256_file,
    ui_dev_mode,
)
from core.infra.setup.core.shared.meta_loader import load_setup_step_meta
from core.infra.setup.core.shared.trace_events import SetupTrace
from core.infra.setup.core.steps.db_connection.db_install_config import write_database_install_config

INSTALL_PY = REPO_ROOT / "install.py"
FED_ROOT = UI_FED_ROOT
BFF_REQUIREMENTS = UI_BFF_REQUIREMENTS
FED_LOCKFILE = UI_FED_LOCKFILE

DB_TYPES = ("duckdb", "postgresql", "mysql")
CONFLICT_POLICIES = ("skip", "overwrite")
DEFAULT_DB_PORTS = {"postgresql": 5432, "mysql": 3306}


@dataclass
class CliInstallOptions:
    userspace: Optional[str] = None
    userspace_conflict: Optional[str] = None
    db: Optional[str] = None
    db_host: Optional[str] = None
    db_port: Optional[str] = None
    db_name: Optional[str] = None
    db_user: Optional[str] = None
    db_password: Optional[str] = None
    db_schema: Optional[str] = None
    import_demo: bool = True
    deps_only: bool = False

    @property
    def conflict_policy(self) -> str:
        raw = str(self.userspace_conflict or "skip").strip().lower() or "skip"
        return raw if raw in CONFLICT_POLICIES else "skip"

    @property
    def has_db_connection_flags(self) -> bool:
        return any(
            str(value or "").strip()
            for value in (
                self.db_host,
                self.db_port,
                self.db_name,
                self.db_user,
                self.db_password,
                self.db_schema,
            )
        )


def validate_cli_install_options(options: CliInstallOptions) -> None:
    """Fail fast when flags are present but incomplete or contradictory."""
    if options.userspace_conflict is not None:
        policy = str(options.userspace_conflict).strip().lower()
        if policy not in CONFLICT_POLICIES:
            raise RuntimeError(
                f"--userspace-conflict 必须是 skip 或 overwrite，收到: {options.userspace_conflict!r}"
            )

    db = None if options.db is None else str(options.db).strip().lower()
    if db == "":
        db = None
    if db is not None and db not in DB_TYPES:
        raise RuntimeError(f"--db 必须是 duckdb / postgresql / mysql，收到: {options.db!r}")

    if db is None:
        if options.has_db_connection_flags:
            raise RuntimeError(
                "已指定 --db-host / --db-name 等连接参数，请同时指定 --db postgresql 或 --db mysql"
            )
        return

    if db == "duckdb" and options.has_db_connection_flags:
        raise RuntimeError("DuckDB 不使用 --db-host / --db-name 等连接参数")

    if db in ("postgresql", "mysql"):
        missing: list[str] = []
        if not str(options.db_host or "").strip():
            missing.append("--db-host")
        if not str(options.db_name or "").strip():
            missing.append("--db-name")
        if not str(options.db_user or "").strip():
            missing.append("--db-user")
        if missing:
            raise RuntimeError(f"{db} 必须提供: {', '.join(missing)}")
        raw_port = options.db_port
        if raw_port not in (None, ""):
            try:
                int(str(raw_port).strip())
            except (TypeError, ValueError) as exc:
                raise RuntimeError(f"--db-port 无效: {raw_port!r}") from exc


def db_inputs_from_options(options: CliInstallOptions) -> Optional[Dict[str, Any]]:
    """UI-shaped db_connection inputs, or None when the caller did not choose a DB."""
    if options.db is None:
        return None
    db = str(options.db).strip().lower()
    inputs: Dict[str, Any] = {"dbType": db}
    if db == "duckdb":
        return inputs
    port = str(options.db_port or "").strip() or str(DEFAULT_DB_PORTS[db])
    inputs.update(
        {
            "host": str(options.db_host or "").strip(),
            "port": port,
            "database": str(options.db_name or "").strip(),
            "user": str(options.db_user or "").strip(),
            "password": str(options.db_password or ""),
        }
    )
    if db == "postgresql":
        inputs["defaultPgsqlSchema"] = str(options.db_schema or "public").strip() or "public"
    return inputs


def userspace_inputs_from_options(options: CliInstallOptions, default_path: str) -> Dict[str, Any]:
    target = str(options.userspace or "").strip() or default_path
    return {
        "userspaceTargetPath": target,
        "userspaceConflictPolicy": options.conflict_policy,
    }


# requirements 指纹变化时只跑这两步。userspace、数据库和演示包都不重做。
_DEP_STEP_IDS = ("sys_req_check", "resolve_deps")


def _ordered_cli_steps() -> List[str]:
    metas = load_setup_step_meta(ui_only=False)
    if metas:
        return [str(s["id"]) for s in metas if not bool(s.get("cliSkip"))]
    return [
        "sys_req_check",
        "resolve_deps",
        "init_userspace",
        "db_connection",
        "import_data",
    ]


def _run_step(step_id: str, options: Optional[CliInstallOptions] = None) -> int:
    options = options or CliInstallOptions()
    extra_env: dict[str, str] = {}
    if step_id == "init_userspace":
        target = str(options.userspace or "").strip()
        if target:
            extra_env["NTQ_USERSPACE_TARGET_PATH"] = str(Path(target).expanduser().resolve())
        extra_env["NTQ_USERSPACE_CONFLICT_POLICY"] = options.conflict_policy
    return NewTeaQuantSetup.run_install_script(step_id, extra_env=extra_env or None)


def _default_userspace_path() -> str:
    from core.infra.project_context import ProjectContext

    return str(ProjectContext.path.resolve_userspace_target(None))


def _userspace_root_after_init(options: CliInstallOptions) -> Path:
    from core.infra.project_context import ProjectContext

    ProjectContext.cache.clear_userspace_cache()
    target = str(options.userspace or "").strip()
    if target:
        return Path(target).expanduser().resolve()
    return Path(ProjectContext.path.get_userspace_root()).resolve()


def _session_inputs(options: CliInstallOptions) -> dict:
    inputs = {
        "init_userspace": userspace_inputs_from_options(
            options, _default_userspace_path()
        ),
    }
    db_inputs = db_inputs_from_options(options)
    if db_inputs is None:
        db_inputs = {"dbType": "duckdb"}
    inputs["db_connection"] = db_inputs
    return inputs


def _steps_for_options(options: CliInstallOptions) -> List[str]:
    steps = _ordered_cli_steps()
    if options.deps_only:
        return [step_id for step_id in steps if step_id in _DEP_STEP_IDS]
    if not options.import_demo:
        return [step_id for step_id in steps if step_id != "import_data"]
    return steps


def _apply_db_config(options: CliInstallOptions) -> None:
    db_inputs = db_inputs_from_options(options)
    if db_inputs is None:
        return
    userspace_root = _userspace_root_after_init(options)
    write_database_install_config(userspace_root, db_inputs)


def install_cli_runtime(
    force: bool = False,
    options: Optional[CliInstallOptions] = None,
) -> None:
    options = options or CliInstallOptions()
    validate_cli_install_options(options)

    if not force and not needs_install("cli"):
        print("CLI 安装状态已就绪。", flush=True)
        return

    NewTeaQuantSetup.to_root_dir()
    SetupTrace.ensure_install_id()
    started = time.monotonic()
    step_seconds: dict = {}
    session_inputs = _session_inputs(options)
    current_step_id = ""
    steps = list(_steps_for_options(options))

    if steps:
        open_install(steps)

    print()
    print("=" * 60)
    print("  New Tea Quant — 安装")
    print("=" * 60)
    print()

    try:
        for step_id in steps:
            current_step_id = step_id
            begin_install_step(step_id)
            NewTeaQuantSetup.print_check_item("running", f"步骤: {step_id}")
            setup_session.record_step(
                step_id,
                setup_session.STATUS_RUNNING,
                inputs=session_inputs.get(step_id),
                source="cli",
            )
            t0 = time.monotonic()
            if step_id == "db_connection":
                _apply_db_config(options)
            code = _run_step(step_id, options)
            step_seconds[step_id] = round(max(0.0, time.monotonic() - t0), 2)
            if code != 0:
                raise RuntimeError(f"步骤失败: {step_id}（exit={code}），详见上方日志")
            setup_session.record_step(
                step_id,
                setup_session.STATUS_SUCCESS,
                inputs=session_inputs.get(step_id),
                source="cli",
            )
            finish_install_step(step_id)
    except Exception as exc:
        failed_step = current_step_id
        message = str(exc)
        if failed_step:
            setup_session.mark_pipeline_failed(failed_step, message, source="cli")
        mark_runtime("cli", success=False, failed_step_id=failed_step)
        SetupTrace.install_step_failed(
            step=failed_step or "cli_install",
            entry="cli",
            message=message,
            exc=exc,
        )
        SetupTrace.install_complete(
            success=False,
            entry="cli",
            error_code=failed_step or "cli_install",
            elapsed_seconds=time.monotonic() - started,
            step_seconds=step_seconds,
        )
        print(f"{CmdLayout.icon.get('error')} 安装失败: {exc}", flush=True)
        fail_install(failed_step, message)
        raise

    if steps:
        close_install()

    skipped_import = ["import_data"] if not options.import_demo and not options.deps_only else None
    if skipped_import:
        NewTeaQuantSetup.print_check_item("skip", "步骤: import_data（未导入演示数据）")
    setup_session.mark_pipeline_complete(
        source="cli",
        inputs_by_step=session_inputs,
        skipped_step_ids=skipped_import,
    )
    mark_cli_success_fingerprint()

    print()
    NewTeaQuantSetup.print_check_ok("安装完成")
    print()
    print("下一步:")
    print("  python cli.py --help")
    if not options.import_demo:
        print("  尚未导入演示数据。需要时运行: python cli.py id（会覆盖同名表）")
    print("=" * 60)
    try:
        from core.infra.setup.core.shared.license_acceptance import apply_trace_consent

        apply_trace_consent()
    except Exception:
        pass
    SetupTrace.install_complete(
        success=True,
        entry="cli",
        elapsed_seconds=time.monotonic() - started,
        step_seconds=step_seconds,
    )


def ensure_cli_install_via_install_py() -> int:
    """
    通过根目录 ``install.py --if-needed`` 执行 CLI 安装（user CLI 自动触发）。

    冷启动与显式 ``python install.py`` 共用同一入口。
    """
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    proc = subprocess.run(
        [sys.executable, str(INSTALL_PY), "--if-needed"],
        cwd=str(REPO_ROOT),
        env=env,
    )
    return int(proc.returncode)


# ----- UI runtime -----


def _env_truthy(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in ("1", "true", "yes")


def _should_open_browser() -> bool:
    """默认打开。devcli ui 传入 NTQ_OPEN_BROWSER=0 时只打印地址。"""
    raw = os.environ.get("NTQ_OPEN_BROWSER")
    if raw is None or not str(raw).strip():
        return True
    return str(raw).strip().lower() not in ("0", "false", "no", "none")


_BOOTSTRAP_MIN = (
    ("pip", (24, 0)),
    ("setuptools", (65,)),
    ("wheel", (0,)),
)


def _parse_pkg_version(raw: str) -> tuple:
    nums = []
    for part in str(raw).split("."):
        digits = ""
        for ch in part:
            if ch.isdigit():
                digits += ch
            else:
                break
        if not digits:
            break
        nums.append(int(digits))
    return tuple(nums) if nums else (0,)


def _installed_version(name: str) -> str:
    try:
        from importlib.metadata import version
        return version(name)
    except Exception:
        return ""


def _version_meets(installed: str, minimum: tuple) -> bool:
    if not installed:
        return False
    got = _parse_pkg_version(installed)
    n = max(len(got), len(minimum))
    got = got + (0,) * (n - len(got))
    need = minimum + (0,) * (n - len(minimum))
    return got >= need


def _bootstrap_pip_ready() -> bool:
    for name, minimum in _BOOTSTRAP_MIN:
        if not _version_meets(_installed_version(name), minimum):
            return False
    return True


def _bootstrap_pip() -> None:
    if _env_truthy("NTQ_SKIP_PIP_BOOTSTRAP"):
        return
    if _bootstrap_pip_ready():
        print("pip / setuptools / wheel 已满足最低版本，跳过联网自升级。", flush=True)
        return
    Utils.pkg.announce()
    print("正在安装 pip / setuptools / wheel…", flush=True)
    ret = Utils.pkg.run_pip(["install", "pip>=24.0", "setuptools>=65", "wheel"], cwd=str(REPO_ROOT))
    if ret != 0:
        if _bootstrap_pip_ready():
            print(
                f"{CmdLayout.icon.get('warning')} pip 工具包联网安装失败，本地版本已可用，继续。",
                flush=True,
            )
            return
        print(f"{CmdLayout.icon.get('warning')} pip 工具包安装失败，将继续尝试安装 BFF 依赖", flush=True)
        print(Utils.pkg.pip_hint(), flush=True)


def _node_toolchain_available() -> bool:
    return shutil.which("node") is not None and shutil.which("npm") is not None


def check_runtime_prerequisites() -> Tuple[bool, str]:
    py_min = python_minimum()
    if sys.version_info < py_min:
        return False, (
            f"Python 版本过低，当前 {sys.version_info.major}.{sys.version_info.minor}，"
            f"需要 >= {py_min[0]}.{py_min[1]}"
        )
    if not BFF_REQUIREMENTS.is_file():
        return False, f"缺少 BFF 依赖文件: {BFF_REQUIREMENTS}"

    if ui_dev_mode():
        if not _node_toolchain_available():
            return False, "开发模式（launcher.py -d）需要 Node.js 与 npm"
        if not (FED_ROOT / "package.json").is_file():
            return False, f"缺少 FED package.json: {FED_ROOT / 'package.json'}"
        return True, "ok"

    if fed_build_ready():
        return True, "ok"

    if _node_toolchain_available():
        return True, "ok"

    return (
        False,
        "未找到 core/ui/fed/build/。请 npm run build，或使用 launcher.py -d",
    )


def _pip_install_bff() -> None:
    Utils.pkg.announce()
    if (
        Utils.pkg.run_pip(
            [
                "install",
                "--no-compile",
                "--only-binary",
                "numpy,pandas,duckdb,psycopg2-binary,cffi,curl-cffi,lxml,mini-racer,psutil",
                "-r",
                str(BFF_REQUIREMENTS),
            ],
            cwd=str(REPO_ROOT),
        )
        != 0
    ):
        raise RuntimeError("安装 BFF Python 依赖失败\n" + Utils.pkg.pip_hint())


def _npm_install_fed() -> None:
    Utils.pkg.announce()
    if subprocess.run(
        ["npm", "install"],
        cwd=str(FED_ROOT),
        env=Utils.pkg.npm_env(),
    ).returncode != 0:
        raise RuntimeError("安装 FED Node 依赖失败")


def _npm_build_fed() -> None:
    print("正在构建 FED（npm run build）…", flush=True)
    if subprocess.run(["npm", "run", "build"], cwd=str(FED_ROOT)).returncode != 0:
        raise RuntimeError("FED 构建失败")
    if not fed_build_ready():
        raise RuntimeError(f"构建完成但未找到 {UI_FED_BUILD_DIR / 'index.html'}")


def install_ui_runtime(force: bool = False) -> None:
    if not force and not needs_install("ui"):
        print("安装检查通过，跳过依赖安装。", flush=True)
        return

    traced_failure = False
    SetupTrace.ensure_install_id()
    started = time.monotonic()
    step_seconds: dict = {}

    def _elapsed() -> float:
        return time.monotonic() - started

    def _run_timed(name: str, fn):
        t0 = time.monotonic()
        try:
            return fn()
        finally:
            step_seconds[name] = round(max(0.0, time.monotonic() - t0), 2)

    def _fail(error_code: str, exc: Optional[BaseException] = None) -> None:
        nonlocal traced_failure
        mark_runtime("ui", success=False, failed_step_id=error_code)
        SetupTrace.install_step_failed(
            step=error_code,
            entry="ui",
            message=str(exc or error_code),
            exc=exc,
        )
        SetupTrace.install_complete(
            success=False,
            entry="ui",
            error_code=error_code,
            elapsed_seconds=_elapsed(),
            step_seconds=step_seconds,
        )
        traced_failure = True

    try:
        _run_timed("pip_bootstrap", _bootstrap_pip)
        try:
            _run_timed("pip_bff", _pip_install_bff)
        except Exception as exc:
            _fail("pip_bff", exc)
            raise

        fingerprints: dict = {
            "python": {
                "uiRequirementsHash": sha256_file(BFF_REQUIREMENTS),
                "venvId": python_env_id(),
                "lastInstallAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            },
        }

        if ui_dev_mode():
            print("安装 UI 开发依赖（BFF + node_modules）…", flush=True)
            try:
                _run_timed("npm_fed", _npm_install_fed)
            except Exception as exc:
                _fail("npm_fed", exc)
                raise
            fingerprints["node"] = {
                "fedLockHash": sha256_file(FED_LOCKFILE),
                "lastInstallAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
        else:
            print("安装 UI 运行依赖（BFF + fed/build）…", flush=True)
            if not fed_build_ready():
                if not _node_toolchain_available():
                    missing = RuntimeError("缺少 fed/build 且未检测到 Node.js")
                    _fail("missing_node", missing)
                    raise missing
                try:
                    _run_timed("npm_fed", _npm_install_fed)
                except Exception as exc:
                    _fail("npm_fed", exc)
                    raise
                try:
                    _run_timed("fed_build", _npm_build_fed)
                except Exception as exc:
                    _fail("fed_build", exc)
                    raise
            fingerprints["fedBuild"] = {
                "buildFingerprint": fed_build_fingerprint(),
                "lastInstallAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }

        mark_runtime("ui", success=True, fingerprints=fingerprints)
        SetupTrace.install_complete(
            success=True,
            entry="ui",
            elapsed_seconds=_elapsed(),
            step_seconds=step_seconds,
        )
        print("UI 运行依赖安装完成。", flush=True)
    except Exception as exc:
        if not traced_failure:
            _fail("unknown", exc)
        raise


def _pids_listening_on(port: int) -> list[int]:
    return pids_listening_on(port)


def _process_cmdline(pid: int) -> str:
    return process_cmdline(pid)


def _wait_port_free(port: int, *, timeout_sec: float = 15.0) -> bool:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        if not _pids_listening_on(port):
            return True
        time.sleep(0.25)
    return not _pids_listening_on(port)


def _release_stale_listen_port(port: int, *, match_substrings: tuple[str, ...]) -> None:
    fed_root = str(FED_ROOT.resolve())

    def _should_kill(cmd: str) -> bool:
        if any(s in cmd for s in match_substrings) or fed_root in cmd:
            return True
        # Windows 取不到 cmdline 时仍回收本产品占用的 UI 端口。
        return not cmd and os.name == "nt"

    for attempt in range(2):
        for pid in _pids_listening_on(port):
            cmd = _process_cmdline(pid)
            if _should_kill(cmd):
                print(f"结束占用 {port} 的旧进程 pid={pid}", flush=True)
                try:
                    kill_process_group(pid, grace_sec=2.0 if attempt == 0 else 0.5)
                except (ProcessLookupError, OSError, AttributeError):
                    pass
        if _wait_port_free(port, timeout_sec=8.0):
            return


def _force_shutdown_ui_ports() -> None:
    """退出时强制释放 UI 端口（不依赖 cmdline，避免 CRA node 孤儿）。"""
    for port in ALL_UI_PORTS:
        for attempt in range(2):
            pids = _pids_listening_on(port)
            if not pids:
                break
            for pid in pids:
                cmd = _process_cmdline(pid)
                label = cmd[:80] if cmd else "(unknown)"
                print(f"结束 UI 进程 pid={pid}（:{port}） {label}", flush=True)
                try:
                    kill_process_group(pid, grace_sec=2.0 if attempt == 0 else 0.5)
                except (ProcessLookupError, OSError, AttributeError):
                    pass
            if _wait_port_free(port, timeout_sec=8.0):
                break
    blocked = [p for p in ALL_UI_PORTS if _pids_listening_on(p)]
    if blocked:
        print(f"{CmdLayout.icon.get('warning')} 端口仍占用: {blocked}，请执行 python devcli.py uk", flush=True)


def release_ui_listen_ports(ports: tuple[int, ...] = ALL_UI_PORTS) -> None:
    """启动前清掉指定 UI 端口上的 NTQ 监听进程。"""
    markers = (
        "core.bff.app",
        "react-scripts",
        "webpack",
        "webpack-dev-server",
        "launcher.py",
        "devcli.py",
        str(FED_ROOT.resolve()),
        str(REPO_ROOT),
    )
    for port in ports:
        _release_stale_listen_port(port, match_substrings=markers)
    blocked = [p for p in ports if _pids_listening_on(p)]
    if blocked:
        print(f"{CmdLayout.icon.get('warning')} 端口仍被占用: {blocked}，后续启动可能失败", flush=True)


def _wait_http_ok(url: str, timeout_sec: int = 30) -> bool:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        if interrupt_requested():
            raise KeyboardInterrupt
        try:
            # 开发服务器只对浏览器的 HTML 请求回退到首页。不带 Accept 时
            # /strategy-design 会是 404，启动就会误判成页面没起来。
            request = urllib.request.Request(
                url,
                headers={"Accept": "text/html,application/json"},
            )
            with urllib.request.urlopen(request, timeout=5) as resp:
                if 200 <= resp.status < 400:
                    return True
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError):
            pass
        try:
            time.sleep(0.5)
        except KeyboardInterrupt:
            raise
    return False


def _warm_bff_api(host: str, port: int) -> None:
    """预加载 strategy 栈，避免 CRA 首屏并发请求时 BFF 冷启动导致 proxy ECONNRESET。"""
    url = f"http://{host}:{port}/api/v1/strategy/catalog/1/1"
    print("正在预加载 BFF API（首次较慢）…", flush=True)
    try:
        with urllib.request.urlopen(url, timeout=120) as resp:
            resp.read()
        print("BFF API 预加载完成", flush=True)
    except Exception as exc:
        print(f"{CmdLayout.icon.get('warning')} BFF API 预加载失败: {exc}", flush=True)


def _fed_dev_env() -> dict[str, str]:
    env = os.environ.copy()
    env["BROWSER"] = "none"
    env["PORT"] = str(UI_DEV_PORT)
    env["DANGEROUSLY_DISABLE_HOST_CHECK"] = "true"
    return env


def _terminate_proc(proc: subprocess.Popen | None, *, grace_sec: float = 3.0) -> None:
    if proc is None:
        return
    if proc.poll() is not None:
        return
    wait_cap = 1.0 if interrupt_requested() else 8.0
    try:
        kill_process_group(proc.pid, grace_sec=grace_sec)
    except Exception:
        pass
    try:
        proc.wait(timeout=wait_cap)
    except subprocess.TimeoutExpired:
        try:
            kill_process_group(proc.pid, grace_sec=0.2)
        except Exception:
            pass
        try:
            proc.kill()
        except (ProcessLookupError, OSError):
            pass
        try:
            proc.wait(timeout=min(2.0, wait_cap))
        except subprocess.TimeoutExpired:
            pass
    except Exception:
        try:
            proc.kill()
        except (ProcessLookupError, OSError):
            pass


def _shutdown_ui_stack_procs(
    *,
    bff_proc: subprocess.Popen | None,
    fed_proc: subprocess.Popen | None,
) -> None:
    """结束 CRA/BFF 子进程；若进程组信号未生效，按端口兜底（避免 Ctrl+C 后孤儿 BFF）。"""
    grace = 0.2 if interrupt_requested() else 3.0
    _terminate_proc(bff_proc, grace_sec=grace)
    _terminate_proc(fed_proc, grace_sec=grace)
    _force_shutdown_ui_ports()


def _ui_entry_path() -> str:
    from core.infra.setup.core.shared.license_acceptance import entry_path

    return entry_path()


def _wait_any_child(*procs: subprocess.Popen | None) -> int:
    """任一子进程退出即返回。不同意条款时 BFF 会退出，开发模式也要跟着关掉。"""
    live = [proc for proc in procs if proc is not None]
    while True:
        for proc in live:
            code = proc.poll()
            if code is not None:
                return int(code)
        if interrupt_requested():
            raise KeyboardInterrupt
        try:
            time.sleep(0.25)
        except KeyboardInterrupt:
            raise


def launch_ui_stack() -> None:
    # 尽早安装：否则卡在 BFF wait / 预加载时 Ctrl+C 可能无法强制退出
    install_interrupt_force_exit()
    host = os.getenv("NTQ_BFF_HOST", "127.0.0.1").strip() or "127.0.0.1"
    dev = ui_dev_mode()

    release_ui_listen_ports(ALL_UI_PORTS)

    bff_env = os.environ.copy()
    bff_env["NTQ_BFF_HOST"] = host
    bff_env["NTQ_BFF_PORT"] = str(UI_BFF_PORT)
    bff_env.pop("NTQ_UI_DEV_GATEWAY", None)
    bff_env.pop("NTQ_WEBPACK_DEV_UPSTREAM", None)
    if dev:
        bff_env["NTQ_UI_DEV"] = "1"
    else:
        bff_env.pop("NTQ_UI_DEV", None)

    bff_proc: subprocess.Popen | None = None
    fed_proc: subprocess.Popen | None = None
    popen_kw: dict = {}
    win_flag = windows_new_process_group_flag()
    if win_flag:
        popen_kw["creationflags"] = win_flag
    try:
        bff_proc = subprocess.Popen(
            [sys.executable, "-m", "core.bff.app"],
            cwd=str(REPO_ROOT),
            env=bff_env,
            **popen_kw,
        )

        health_url = f"http://{host}:{UI_BFF_PORT}/api/health"
        if not _wait_http_ok(health_url, timeout_sec=90):
            raise RuntimeError(f"BFF 启动超时（{health_url}）")

        _warm_bff_api(host, UI_BFF_PORT)

        if dev:
            fed_proc = subprocess.Popen(
                ["npm", "start"],
                cwd=str(FED_ROOT),
                env=_fed_dev_env(),
                **popen_kw,
            )
            ui_url = f"http://localhost:{UI_DEV_PORT}{_ui_entry_path()}"
            print(
                f"开发模式：浏览器 http://localhost:{UI_DEV_PORT} "
                f"（共享 BFF :{UI_BFF_PORT} 仅 /api，不挂载 fed/build）",
                flush=True,
            )
            if not _wait_http_ok(f"http://localhost:{UI_DEV_PORT}/", timeout_sec=180):
                print(f"{CmdLayout.icon.get('warning')} CRA 未就绪，请查看 npm 输出；目标: {ui_url}", flush=True)
            elif not _wait_http_ok(f"http://{host}:{UI_BFF_PORT}/api/health", timeout_sec=15):
                print(f"{CmdLayout.icon.get('warning')} BFF 在 CRA 就绪后未响应，/api 代理可能失败", flush=True)
        else:
            if not fed_build_ready():
                raise RuntimeError("缺少 fed/build，请 npm run build 或使用 launcher.py -d")
            ui_url = f"http://{host}:{UI_BFF_PORT}{_ui_entry_path()}"
            print(f"生产模式：入口 {ui_url}", flush=True)
            if not _wait_http_ok(ui_url, timeout_sec=30):
                raise RuntimeError(f"前端未就绪: {ui_url}")

        if _wait_http_ok(ui_url, timeout_sec=5):
            print(f"访问: {ui_url}", flush=True)
            if _should_open_browser():
                try:
                    webbrowser.open(ui_url)
                except Exception:
                    pass
        else:
            print(f"请手动打开: {ui_url}", flush=True)

        try:
            _wait_any_child(bff_proc, fed_proc)
        except KeyboardInterrupt:
            print("\n正在关闭…", flush=True)
    except KeyboardInterrupt:
        print("\n正在关闭…", flush=True)
    finally:
        _shutdown_ui_stack_procs(bff_proc=bff_proc, fed_proc=fed_proc)
