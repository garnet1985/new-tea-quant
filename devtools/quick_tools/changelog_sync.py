"""
从根目录 ``CHANGELOG.md`` 解析指定版本的 ``-`` 条目，同步到 ``core/system.json`` / ``core/system.py``。
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import List, Optional, Tuple

from devtools.quick_tools._paths import REPO_ROOT

CHANGELOG_PATH = REPO_ROOT / "CHANGELOG.md"
SYSTEM_JSON = REPO_ROOT / "core" / "system.json"
SYSTEM_PY = REPO_ROOT / "core" / "system.py"

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


def format_new_features_python_block(features: List[str], *, base_indent: str = "    ") -> str:
    """生成 ``system.py`` _FALLBACK 内 ``new_features`` 数组文本（含尾逗号）。"""
    item_indent = base_indent + "    "
    out = [f'{base_indent}"new_features": [']
    for item in features:
        out.append(f"{item_indent}{json.dumps(item, ensure_ascii=False)},")
    out.append(f"{base_indent}],")
    return "\n".join(out)


def _replace_new_features_block(text: str, features: List[str], *, marker: str) -> str:
    start = text.find(marker)
    if start < 0:
        raise RuntimeError(f"未找到 {marker!r}")
    bracket = text.find("[", start)
    if bracket < 0:
        raise RuntimeError(f"{marker} 后缺少 [")

    depth = 0
    end = bracket
    for i in range(bracket, len(text)):
        ch = text[i]
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                end = i + 1
                if end < len(text) and text[end] == ",":
                    end += 1
                break
    else:
        raise RuntimeError(f"无法定位 {marker} 数组结束")

    replacement = format_new_features_python_block(features)
    return text[:start] + replacement + text[end:]


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


def update_system_py_fallback_new_features(
    version: str,
    release_date: str,
    new_features: List[str],
) -> None:
    text = SYSTEM_PY.read_text(encoding="utf-8")
    block_start = text.find("_FALLBACK")
    if block_start < 0:
        raise RuntimeError("core/system.py 中未找到 _FALLBACK")
    brace = text.find("{", block_start)
    if brace < 0:
        raise RuntimeError("core/system.py 中 _FALLBACK 后缺少 {")
    block_end = text.find("\n\n\ndef _load_payload", block_start)
    if block_end < 0:
        block_end = text.find("\ndef _load_payload", block_start)
    if block_end < 0:
        raise RuntimeError("无法定位 _FALLBACK 块结束")

    block = text[block_start:block_end]
    block = re.sub(
        r'("version":\s*")[^"]+(")',
        rf"\g<1>{version}\2",
        block,
        count=1,
    )
    block = re.sub(
        r'("release_date":\s*")[^"]+(")',
        rf"\g<1>{release_date}\2",
        block,
        count=1,
    )
    block = _replace_new_features_block(block, new_features, marker='"new_features":')

    new_text = text[:block_start] + block + text[block_end:]
    SYSTEM_PY.write_text(new_text, encoding="utf-8")


def sync_version_metadata_from_changelog(
    version: str,
    *,
    release_date: str,
) -> List[str]:
    """
    从 CHANGELOG 读取 ``new_features``，写入 ``system.json`` 与 ``system.py`` _FALLBACK。

    若 CHANGELOG 标题含发布日期则优先使用（覆盖 ``release_date`` 参数）。
    返回写入的 feature 列表。
    """
    features, heading_date = parse_changelog_section(version)
    effective_date = heading_date or release_date
    update_system_json_new_features(version, effective_date, features)
    update_system_py_fallback_new_features(version, effective_date, features)
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
