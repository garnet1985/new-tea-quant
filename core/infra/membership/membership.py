"""官网通用凭证。文件在 userspace，设置页写入，以后的会员功能读取。"""

from __future__ import annotations

import re
from typing import Optional

from core.infra.project_context import ProjectContext

TOKEN_FILE_NAME = "membership_token.txt"
RELATIVE_PATH = f"userspace/system/membership/{TOKEN_FILE_NAME}"
TOKEN_PATTERN = re.compile(r"^ntq_[0-9a-f]{48}$")


class Membership:
    """装载状态与读写。HTTP 层只暴露 status / save / clear，不回传明文。"""

    @staticmethod
    def token_file():
        return ProjectContext.path.get_membership_token_file()

    @staticmethod
    def read() -> Optional[str]:
        """有效凭证。文件不存在或内容不是通用凭证时返回 None。"""
        path = Membership.token_file()
        if not path.is_file():
            return None
        try:
            raw = path.read_text(encoding="utf-8")
        except OSError:
            return None
        for line in raw.splitlines():
            token = line.strip()
            if not token or token.startswith("#"):
                continue
            return token if TOKEN_PATTERN.fullmatch(token) else None
        return None

    @staticmethod
    def status() -> dict:
        path = Membership.token_file()
        exists = path.is_file()
        configured = Membership.read() is not None
        return {
            "configured": configured,
            "invalid": exists and not configured,
            "path": RELATIVE_PATH,
        }

    @staticmethod
    def save(token: str) -> Optional[str]:
        """写入凭证。格式不对时返回错误文案，成功返回 None。"""
        value = str(token or "").strip()
        if not TOKEN_PATTERN.fullmatch(value):
            return "凭证格式不对。请粘贴官网会员中心显示的通用凭证。"
        path = Membership.token_file()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value + "\n", encoding="utf-8")
        try:
            path.chmod(0o600)
        except OSError:
            pass
        return None

    @staticmethod
    def clear() -> None:
        path = Membership.token_file()
        if path.is_file():
            path.unlink()
