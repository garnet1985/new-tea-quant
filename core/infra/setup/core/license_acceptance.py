"""使用条款同意。记录在仓库 ``.ntq/``，不写 userspace。

``LICENSE_REVISION`` 变了就再问一次。改条款正文时把这里抬一档。
"""

from __future__ import annotations

import json
import os
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path

from core.infra.setup.core.install_runtime import REPO_ROOT

LICENSE_REVISION = "1"
_ACCEPT_ENV = "NTQ_ACCEPT_LICENSE"
_FILENAME = "license_acceptance.json"


def acceptance_path() -> Path:
    return REPO_ROOT / ".ntq" / _FILENAME


def is_accepted() -> bool:
    path = acceptance_path()
    if not path.is_file():
        return False
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, TypeError):
        return False
    if not isinstance(raw, dict):
        return False
    return str(raw.get("revision") or "") == LICENSE_REVISION


def accept(*, source: str) -> None:
    path = acceptance_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "revision": LICENSE_REVISION,
        "accepted_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source": str(source or "")[:32],
    }
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)
    apply_trace_consent()


def apply_trace_consent() -> None:
    """使用条款已包含使用统计。userspace 就绪且尚未选择时记为同意。

    userspace 还没建好时不写文件，避免提前创建目录挡住 init_userspace。
    设置里已经关过的保持关闭。
    """
    if not is_accepted():
        return
    try:
        from core.infra.project_context.core.path_manager import PathManager

        marker = (
            PathManager.get_userspace_root()
            / "system"
            / "config"
            / "database"
            / "common.json"
        )
        if not marker.is_file():
            return
        from core.infra.trace.core.services.consent_service import TraceConsentService

        if TraceConsentService.is_decided():
            return
        TraceConsentService.grant(source="license")
    except Exception:
        return


def _site_urls() -> dict:
    """官网页面地址。模块不在时为空，安装流程仍只认本地 LICENSE。"""
    try:
        from core.modules.ntq_external import site_urls
    except ImportError:
        return {}
    raw = site_urls()
    return raw if isinstance(raw, dict) else {}


def status_payload() -> dict:
    urls = _site_urls()
    return {
        "accepted": is_accepted(),
        "revision": LICENSE_REVISION,
        "disclaimer_url": str(urls.get("disclaimer_url") or ""),
        "license_url": str(urls.get("license_url") or ""),
    }


def env_accepts() -> bool:
    raw = os.environ.get(_ACCEPT_ENV)
    if raw is None:
        return False
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def ensure_accepted(*, source: str, assume_accepted: bool = False) -> bool:
    """当前修订已同意则直接通过。否则只认交互里的 y / Y，或显式放行。"""
    if is_accepted():
        return True
    if assume_accepted or env_accepts():
        accept(source=source)
        return True
    if not _stdin_is_tty():
        print(_noninteractive_message(), flush=True)
        return False
    print(_prompt_text(), flush=True)
    try:
        answer = input("同意并继续请输入 y：")
    except EOFError:
        print("未同意使用条款，已停止。", flush=True)
        return False
    if str(answer or "").strip() in {"y", "Y"}:
        accept(source=source)
        return True
    print("未同意使用条款，已停止。", flush=True)
    return False


def entry_path() -> str:
    if is_accepted():
        return "/strategy-design"
    return "/setup/license"


def exit_process_soon() -> None:
    """让当前进程在响应发出后退出。launcher 看到子进程结束就会关掉界面。"""

    def _exit() -> None:
        os._exit(0)

    timer = threading.Timer(0.3, _exit)
    timer.daemon = True
    timer.start()


def _stdin_is_tty() -> bool:
    try:
        return bool(sys.stdin.isatty())
    except Exception:
        return False


def _prompt_text() -> str:
    urls = _site_urls()
    lines = [
        "使用 New Tea Quant 前需要同意使用条款。不同意将停止。",
        "",
    ]
    disclaimer = str(urls.get("disclaimer_url") or "").strip()
    license_url = str(urls.get("license_url") or "").strip()
    if disclaimer:
        lines.append(f"使用条款：{disclaimer}")
    if license_url:
        lines.append(f"许可证：{license_url}")
    lines.extend(["本地全文：仓库根目录的 DISCLAIMER.md 与 LICENSE", ""])
    return "\n".join(lines)


def _noninteractive_message() -> str:
    return (
        "未同意使用条款。当前没有交互终端。"
        "请在终端输入 y，或执行 install.py --accept-license，"
        "或设置 NTQ_ACCEPT_LICENSE=1。"
    )
