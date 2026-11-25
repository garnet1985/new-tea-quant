"""模型请求写入/只读路径的硬准则。提示词里的约定不能代替这里的检查。"""

from __future__ import annotations

from pathlib import Path

from core.infra.project_context import ProjectContext
from core.modules.agent.contracts import AgentError
from core.modules.agent.core.code.conf.conf import WRITE_PATH_LIMIT

_SECRET_NAMES = frozenset(
    {
        "api_key.txt",
        "credentials.json",
        "membership.json",
        ".env",
    }
)


def resolve_user_write_path(relative: str) -> Path:
    """把相对路径解析到允许的 userspace 子目录。

    只允许 ``strategies/``、``extensions/tags/``、``extensions/tables/``、
    ``extensions/post_process/adapters/``、``extensions/post_process/post_processors/`` 之下。
    拒绝绝对路径、``..``、以及 userspace 里的配置、密钥和会员凭证。
    """
    parts = _normalize_relative(relative, label="写入")
    userspace = ProjectContext.path.get_userspace_root().resolve()
    candidate = (userspace.joinpath(*parts)).resolve()
    roots = _write_roots()
    allowed = any(
        candidate != root and candidate.is_relative_to(root) for root in roots
    )
    if not allowed:
        raise AgentError(
            f"写入路径不在允许范围内：{relative}。"
            "只允许 strategies/、extensions/tags/、extensions/tables/、"
            "extensions/post_process/adapters/、extensions/post_process/post_processors/ 下的相对路径"
        )
    return candidate


def resolve_user_read_path(relative: str) -> Path:
    """把相对路径解析到允许只读的 userspace 子树。

    允许 ``strategies/`` 与 ``extensions/``（不含 ``llm_providers`` / 密钥文件）。
    目录根本身可读（用于 list_dir）。
    """
    parts = _normalize_relative(relative, label="读取")
    if parts[0] == "system" or (
        len(parts) >= 2 and parts[0] == "extensions" and parts[1] == "llm_providers"
    ):
        raise AgentError(f"读取路径不在允许范围内：{relative}")
    if parts[-1] in _SECRET_NAMES:
        raise AgentError(f"拒绝读取敏感文件：{relative}")

    userspace = ProjectContext.path.get_userspace_root().resolve()
    candidate = (userspace.joinpath(*parts)).resolve()
    if not candidate.is_relative_to(userspace):
        raise AgentError(f"读取路径不在允许范围内：{relative}")
    roots = _read_roots()
    allowed = any(
        candidate == root or candidate.is_relative_to(root) for root in roots
    )
    if not allowed:
        raise AgentError(
            f"读取路径不在允许范围内：{relative}。"
            "只允许 strategies/ 与 extensions/（不含 llm_providers）下的相对路径"
        )
    # 子树内再挡 llm_providers（经 symlink / 深层路径）
    try:
        rel = candidate.relative_to(userspace).parts
    except ValueError as exc:
        raise AgentError(f"读取路径不在允许范围内：{relative}") from exc
    if "llm_providers" in rel or "system" in rel:
        raise AgentError(f"读取路径不在允许范围内：{relative}")
    if candidate.name in _SECRET_NAMES:
        raise AgentError(f"拒绝读取敏感文件：{relative}")
    return candidate


def _normalize_relative(relative: str, *, label: str) -> list[str]:
    raw = str(relative or "").strip().replace("\\", "/")
    if not raw or len(raw) > WRITE_PATH_LIMIT or "\x00" in raw:
        raise AgentError(f"{label}路径不在允许范围内")
    if raw.startswith("/") or Path(raw).is_absolute():
        raise AgentError(f"{label}路径不在允许范围内：{raw}")
    parts = [part for part in raw.split("/") if part not in ("", ".")]
    if not parts or any(part == ".." for part in parts):
        raise AgentError(f"{label}路径不在允许范围内：{raw}")
    return parts


def _write_roots() -> tuple[Path, ...]:
    path = ProjectContext.path
    return (
        path.get_strategies_root().resolve(),
        path.get_tags_root().resolve(),
        path.get_extensions_tables_directory().resolve(),
        path.get_adapters_directory().resolve(),
        path.get_post_processors_directory().resolve(),
    )


def _read_roots() -> tuple[Path, ...]:
    path = ProjectContext.path
    return (
        path.get_strategies_root().resolve(),
        path.get_extensions_root().resolve(),
    )
