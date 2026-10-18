"""模型请求写入时的硬准则。提示词里的约定不能代替这里的检查。"""

from __future__ import annotations

from pathlib import Path

from core.infra.project_context import ProjectContext
from core.modules.agent.contracts import AgentError

_PATH_LIMIT = 240


def resolve_user_write_path(relative: str) -> Path:
    """把相对路径解析到允许的 userspace 子目录。

    只允许 ``strategies/``、``extensions/tags/``、``extensions/adapters/`` 之下。
    拒绝绝对路径、``..``、以及 userspace 里的配置、密钥和会员凭证。
    """
    raw = str(relative or "").strip().replace("\\", "/")
    if not raw or len(raw) > _PATH_LIMIT or "\x00" in raw:
        raise AgentError("写入路径不在允许范围内")
    if raw.startswith("/") or Path(raw).is_absolute():
        raise AgentError(f"写入路径不在允许范围内：{raw}")
    parts = [part for part in raw.split("/") if part not in ("", ".")]
    if not parts or any(part == ".." for part in parts):
        raise AgentError(f"写入路径不在允许范围内：{raw}")

    userspace = ProjectContext.path.get_userspace_root().resolve()
    candidate = (userspace.joinpath(*parts)).resolve()
    roots = _write_roots()
    allowed = any(
        candidate != root and candidate.is_relative_to(root) for root in roots
    )
    if not allowed:
        raise AgentError(
            f"写入路径不在允许范围内：{raw}。"
            "只允许 strategies/、extensions/tags/、extensions/adapters/ 下的相对路径"
        )
    return candidate


def _write_roots() -> tuple[Path, ...]:
    path = ProjectContext.path
    return (
        path.get_strategies_root().resolve(),
        path.get_tags_root().resolve(),
        path.get_adapters_directory().resolve(),
    )
