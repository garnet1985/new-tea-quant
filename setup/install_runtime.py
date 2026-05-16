"""
安装状态与 ``needs_install`` 共用层（UI / CLI 入口均通过本模块判断）。

- ``launcher.py`` → ``needs_install("ui")`` + ``install_ui_runtime``
- ``install.py`` / ``start-cli.py`` → ``needs_install("cli")`` + ``install_cli_runtime``

状态文件：``.ntq/install-state.json``（结构见 ``launcher-and-setup-runtime-design.md``）。
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Literal, Optional

from core.system import system_meta

InstallProfileName = Literal["ui", "cli"]

REPO_ROOT = Path(__file__).resolve().parent.parent
STATE_FILE = REPO_ROOT / ".ntq" / "install-state.json"
REQUIREMENTS = REPO_ROOT / "requirements.txt"
UI_BFF_REQUIREMENTS = REPO_ROOT / "core" / "ui" / "bff" / "requirements.txt"
UI_FED_ROOT = REPO_ROOT / "core" / "ui" / "fed"
UI_FED_LOCKFILE = UI_FED_ROOT / "package-lock.json"
UI_FED_NODE_MODULES = UI_FED_ROOT / "node_modules"
UI_FED_BUILD_DIR = UI_FED_ROOT / "build"
UI_FED_BUILD_INDEX = UI_FED_BUILD_DIR / "index.html"


def sha256_file(path: Path) -> str:
    if not path.is_file():
        return ""
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_state() -> Dict[str, Any]:
    if not STATE_FILE.is_file():
        return {}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_state(state: Dict[str, Any]) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def userspace_ready() -> bool:
    from core.infra.project_context.path_manager import PathManager

    return (PathManager.userspace() / "config" / "database" / "common.json").is_file()


def _runtime_status(state: Dict[str, Any], profile: InstallProfileName) -> str:
    """读取 profile 对应 runtime 状态；UI 兼容旧键 ``setupRuntime``。"""
    if profile == "ui":
        ui_rt = state.get("uiRuntime") or {}
        if ui_rt.get("lastStatus"):
            return str(ui_rt.get("lastStatus", ""))
        legacy = state.get("setupRuntime") or {}
        return str(legacy.get("lastStatus", ""))
    cli_rt = state.get("cliRuntime") or {}
    return str(cli_rt.get("lastStatus", ""))


@dataclass(frozen=True)
class _ProfileSpec:
    name: InstallProfileName
    runtime_key: str
    extra_needs_checks: tuple[Callable[[Dict[str, Any]], bool], ...]


def fed_build_ready() -> bool:
    return UI_FED_BUILD_INDEX.is_file()


def fed_build_fingerprint() -> str:
    """CRA 构建产物指纹（用于生产模式 needs_install）。"""
    parts: List[str] = []
    for rel in ("index.html", "asset-manifest.json"):
        p = UI_FED_BUILD_DIR / rel
        if p.is_file():
            parts.append(sha256_file(p))
    if not parts:
        return ""
    return hashlib.sha256("|".join(parts).encode()).hexdigest()


def set_ui_dev_mode(enabled: bool) -> None:
    """由 ``launcher.py -d`` / ``-dev`` 设置；内部仍用环境变量传递（venv 重启后保留）。"""
    import os

    if enabled:
        os.environ["NTQ_UI_DEV"] = "1"
    else:
        os.environ.pop("NTQ_UI_DEV", None)


def ui_dev_mode() -> bool:
    import os

    return os.environ.get("NTQ_UI_DEV", "").strip().lower() in ("1", "true", "yes")


def _ui_extra_needs(state: Dict[str, Any]) -> bool:
    python_state = state.get("python", {})
    if python_state.get("uiRequirementsHash") != sha256_file(UI_BFF_REQUIREMENTS):
        return True

    if ui_dev_mode():
        node_state = state.get("node", {})
        if node_state.get("fedLockHash") != sha256_file(UI_FED_LOCKFILE):
            return True
        if not UI_FED_NODE_MODULES.is_dir():
            return True
        return False

    fed_build_state = state.get("fedBuild", {})
    if fed_build_state.get("buildFingerprint") != fed_build_fingerprint():
        return True
    if not fed_build_ready():
        return True
    return False


def _cli_extra_needs(state: Dict[str, Any]) -> bool:
    cli_state = state.get("cli", {})
    if cli_state.get("requirementsHash") != sha256_file(REQUIREMENTS):
        return True
    return False


_PROFILES: Dict[InstallProfileName, _ProfileSpec] = {
    "ui": _ProfileSpec("ui", "uiRuntime", (_ui_extra_needs,)),
    "cli": _ProfileSpec("cli", "cliRuntime", (_cli_extra_needs,)),
}


def needs_install(profile: InstallProfileName) -> bool:
    """
    UI / CLI 共用判断顺序（完全一致）：

    1. 状态文件不存在
    2. ``coreVersion`` 与当前 core 不一致
    3. userspace 未就绪
    4. 对应 profile 的 runtime ``lastStatus`` 非 ``success``
    5. profile 专有依赖指纹（UI: BFF/FED；CLI: requirements.txt）
    """
    state = load_state()
    if not state:
        return True

    if state.get("coreVersion") != system_meta.version:
        return True

    if not userspace_ready():
        return True

    if _runtime_status(state, profile) != "success":
        return True

    spec = _PROFILES[profile]
    for check in spec.extra_needs_checks:
        if check(state):
            return True

    return False


def mark_runtime(
    profile: InstallProfileName,
    *,
    success: bool,
    failed_step_id: str = "",
    fingerprints: Optional[Dict[str, Any]] = None,
) -> None:
    """安装结束后写入状态（合并已有字段，不覆盖另一 profile）。"""
    state = load_state()
    state["coreVersion"] = system_meta.version

    if fingerprints:
        state.update(fingerprints)

    spec = _PROFILES[profile]
    state[spec.runtime_key] = {
        "lastStatus": "success" if success else "failed",
        "lastFailedStepId": failed_step_id if not success else "",
    }
    if profile == "ui":
        state.pop("setupRuntime", None)
    save_state(state)
