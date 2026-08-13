"""
从根目录 ``CHANGELOG.md`` 解析指定版本的 ``-`` 条目，同步到 ``core/system.json``。
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import List, Optional, Tuple

from core.infra.project_context import ProjectContext

REPO_ROOT = ProjectContext.path.get_project_root()
CHANGELOG_PATH = REPO_ROOT / "CHANGELOG.md"
SYSTEM_JSON = REPO_ROOT / "core" / "system.json"

_VERSION_HEADING_RE = re.compile(
    r"^###\s+v(?P<version>\d+\.\d+\.\d+)\s*(?:\((?P<date>[^)]+)\))?\s*$"
)
_NEXT_VERSION_HEADING_RE = re.compile(r"^###\s+v\d+\.\d+\.\d+")


def normalize_version(raw: str) -> str:
    v = str(raw or "").strip().lstrip("vV")
    if not re.match(r"^\d+\.\d+\.\d+$", v):
        raise ValueError(f"版本号须为 X.Y.Z，收到: {raw!r}")
    return v


def _normalize_release_date(raw: str) -> Optional[str]:
    text = str(raw or "").strip()
    if not text or text.upper() == "TBD":
        return None
    m = re.match(r"^(\d{4})-(\d{1,2})-(\d{1,2})$", text)
    if not m:
        return None
    y, mo, d = m.groups()
    return f"{y}-{int(mo):02d}-{int(d):02d}"


def parse_changelog_section(version: str) -> Tuple[List[str], Optional[str]]:
    """
    读取 ``CHANGELOG.md`` 中 ``### vX.Y.Z (...)`` 段落的 ``-`` 列表项。

    返回 ``(new_features, release_date_or_none)``；日期来自标题括号（非 TBD 时）。
    """
    ver = normalize_version(version)
    if not CHANGELOG_PATH.is_file():
        raise FileNotFoundError(f"缺少 {CHANGELOG_PATH.relative_to(REPO_ROOT)}")

    lines = CHANGELOG_PATH.read_text(encoding="utf-8").splitlines()
    heading_idx: Optional[int] = None
    heading_date: Optional[str] = None

    for idx, line in enumerate(lines):
        m = _VERSION_HEADING_RE.match(line.strip())
        if m and m.group("version") == ver:
            heading_idx = idx
            heading_date = _normalize_release_date(m.group("date") or "")
            break

    if heading_idx is None:
        raise ValueError(f"CHANGELOG 中未找到 v{ver} 段落（### v{ver} ...）")

    features: List[str] = []
    for line in lines[heading_idx + 1 :]:
        stripped = line.strip()
        if not stripped:
            continue
        if _NEXT_VERSION_HEADING_RE.match(stripped):
            break
        if stripped.startswith("- "):
            features.append(stripped[2:].strip())

    if not features:
        raise ValueError(f"CHANGELOG v{ver} 段落下没有 `-` 条目")

    return features, heading_date


def update_system_json_new_features(
    version: str,
    release_date: str,
    new_features: List[str],
) -> None:
    data = json.loads(SYSTEM_JSON.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise RuntimeError(f"{SYSTEM_JSON} 不是 object")
    data["version"] = version
    data["release_date"] = release_date
    data["new_features"] = list(new_features)
    SYSTEM_JSON.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def sync_version_metadata_from_changelog(
    version: str,
    *,
    release_date: str,
) -> List[str]:
    """
    从 CHANGELOG 读取 ``new_features``，写入 ``system.json``。

    若 CHANGELOG 标题含发布日期则优先使用（覆盖 ``release_date`` 参数）。
    返回写入的 feature 列表。
    """
    features, heading_date = parse_changelog_section(version)
    effective_date = heading_date or release_date
    update_system_json_new_features(version, effective_date, features)
    return features


def compare_system_new_features(version: str) -> List[str]:
    """check-only：对比 CHANGELOG 与 system.json 的 new_features。"""
    issues: List[str] = []
    try:
        expected, _ = parse_changelog_section(version)
    except (FileNotFoundError, ValueError) as exc:
        return [str(exc)]

    if not SYSTEM_JSON.is_file():
        return [f"缺少 {SYSTEM_JSON.relative_to(REPO_ROOT)}"]

    data = json.loads(SYSTEM_JSON.read_text(encoding="utf-8"))
    actual = data.get("new_features")
    if not isinstance(actual, list):
        return ["system.json 缺少 new_features 数组"]
    if actual != expected:
        issues.append(
            f"system.json new_features 与 CHANGELOG v{normalize_version(version)} 不一致 "
            f"（CHANGELOG {len(expected)} 条，system.json {len(actual)} 条）"
        )
    return issues


__all__ = [
    "compare_system_new_features",
    "parse_changelog_section",
    "sync_version_metadata_from_changelog",
]
