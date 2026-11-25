"""
模块版本字段与 ``module_info.yaml`` 对齐。

由 ``devcli.py pack`` / ``p`` 调用。``module_info.yaml`` 为 SSOT。

统一 Markdown 文首（两行，硬性命名，禁止别名）：

1. ``**模块：** `<name>` · **版本：** `<version>` ``
2. ``**最低支持核心版本：** `<compatible_core_versions>` ``

``glossary.yaml`` 头注释：

- ``# Version: <version>``
- ``# Compatible-Core: <compatible_core_versions>``
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

import yaml

from core.infra.project_context import ProjectContext

REPO_ROOT = ProjectContext.path.get_project_root()

_MODULE_PACKAGE_ROOTS: Tuple[Tuple[str, Path], ...] = (
    ("core/modules", REPO_ROOT / "core" / "modules"),
    ("core/infra", REPO_ROOT / "core" / "infra"),
)
_SINGLE_MODULE_ROOTS: Tuple[Tuple[str, Path], ...] = (
    ("core/ui", REPO_ROOT / "core" / "ui"),
    ("core/bff", REPO_ROOT / "core" / "bff"),
    ("core/tables", REPO_ROOT / "core" / "tables"),
)

# 存在则文首必须有标准版本字段，且 = module_info.version
_REQUIRED_IF_EXISTS: Tuple[str, ...] = (
    "API.md",
    "glossary.yaml",
    "QUICKSTART.md",
    "docs/ARCHITECTURE.md",
    "docs/DESIGN.md",
    "docs/CONCEPTS.md",
    "__performance__/README.md",
    "__performance__/CASES.md",
)

_HEADER_LINES = 40
_SEMVER = r"\d+\.\d+\.\d+"

# 标准字段
_MD_MODULE_VERSION_RE = re.compile(
    rf"\*\*模块：\*\*\s*`(?P<name>[^`]+)`\s*·\s*\*\*版本：\*\*\s*`?(?P<ver>{_SEMVER})`?"
)
_MD_VERSION_ONLY_RE = re.compile(rf"\*\*版本：\*\*\s*`?(?P<ver>{_SEMVER})`?")
_GLOSSARY_VERSION_RE = re.compile(rf"^#\s*Version:\s*(?P<ver>{_SEMVER})\s*$", re.M)
_GLOSSARY_CORE_RE = re.compile(r"^#\s*Compatible-Core:\s*(?P<ver>\S+)\s*$", re.M)
_CORE_COMPAT_RE = re.compile(r"\*\*最低支持核心版本：\*\*\s*`(?P<ver>[^`]+)`")

# 历史别名（校验时报非标准；sync 改写成标准头）
_LEGACY_COVER_LINE_RE = re.compile(r"\*\*覆盖版本：\*\*[^\n]*")
_LEGACY_BASELINE_LINE_RE = re.compile(r"\*\*当前基线版本：\*\*[^\n]*")
_LEGACY_CORE_ALIAS_RE = re.compile(r"\*\*最低核心版本：\*\*[^\n]*")

# 文首可被 sync 收口的字段行（不含「引入版本」）
_MD_HEADER_FIELD_LINE_RE = re.compile(
    r"^\*\*(?:模块|版本|最低支持核心版本|最低核心版本|覆盖版本|当前基线版本)：\*\*.*$"
)
_GLOSSARY_HEADER_LINE_RE = re.compile(
    r"^#\s*(?:Version|Compatible-Core):\s*\S+\s*$"
)


def _module_package_dirs(root: Path) -> List[Path]:
    if not root.is_dir():
        return []
    out: List[Path] = []
    for child in sorted(root.iterdir()):
        if not child.is_dir():
            continue
        name = child.name
        if name.startswith(".") or name.startswith("__"):
            continue
        out.append(child)
    return out


def iter_module_info_paths() -> List[Path]:
    paths: List[Path] = []
    for _, root in _MODULE_PACKAGE_ROOTS:
        paths.extend(pkg / "module_info.yaml" for pkg in _module_package_dirs(root))
    for _, root in _SINGLE_MODULE_ROOTS:
        paths.append(root / "module_info.yaml")
    return paths


def expected_module_info_name(module_root: Path) -> str:
    """目录 → ``module_info.name``：``modules.x`` / ``infra.x`` / ``ui`` / ``bff`` / ``tables``。"""
    rel = module_root.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    singles = {"core/ui": "ui", "core/bff": "bff", "core/tables": "tables"}
    if rel in singles:
        return singles[rel]
    parts = rel.split("/")
    if len(parts) == 3 and parts[0] == "core" and parts[1] in {"modules", "infra"}:
        return f"{parts[1]}.{parts[2]}"
    raise ValueError(f"无法从路径推导 module_info.name: {rel}")


def _header_text(path: Path) -> str:
    lines = path.read_text(encoding="utf-8").splitlines()
    return "\n".join(lines[:_HEADER_LINES])


def _read_module_info(info_path: Path) -> Tuple[Optional[dict], Optional[str]]:
    try:
        data = yaml.safe_load(info_path.read_text(encoding="utf-8")) or {}
    except Exception as exc:
        return None, f"{_rel(info_path)}: 无法解析 YAML ({exc})"
    if not isinstance(data, dict):
        return None, f"{_rel(info_path)}: 根节点须为 mapping"
    return data, None


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return str(path)


def _standard_md_header(name: str, version: str, core_compat: str) -> str:
    # 两行之间空一行，确保 CommonMark 产出两个 <p>（站点分别套 release-version / release-date）
    return (
        f"**模块：** `{name}` · **版本：** `{version}`\n"
        f"\n"
        f"**最低支持核心版本：** `{core_compat}`"
    )


def _has_legacy_version_alias(header: str) -> bool:
    return bool(
        _LEGACY_COVER_LINE_RE.search(header)
        or _LEGACY_BASELINE_LINE_RE.search(header)
        or _LEGACY_CORE_ALIAS_RE.search(header)
    )


def _extract_md_module_name(header: str) -> Optional[str]:
    found = _MD_MODULE_VERSION_RE.search(header)
    return found.group("name").strip() if found else None


def _extract_standard_version(header: str, *, is_glossary: bool) -> Optional[str]:
    if is_glossary:
        found = _GLOSSARY_VERSION_RE.search(header)
        return found.group("ver") if found else None
    found = _MD_MODULE_VERSION_RE.search(header)
    if found:
        return found.group("ver")
    found = _MD_VERSION_ONLY_RE.search(header)
    return found.group("ver") if found else None


def _extract_core_compat(header: str, *, is_glossary: bool) -> Optional[str]:
    if is_glossary:
        found = _GLOSSARY_CORE_RE.search(header)
        return found.group("ver").strip() if found else None
    found = _CORE_COMPAT_RE.search(header)
    return found.group("ver").strip() if found else None


def iter_versioned_doc_paths(module_root: Path) -> List[Tuple[Path, str]]:
    """
    返回 ``(path, policy)``。

    - ``required``：文件存在则文首必须有标准版本字段
    - ``optional``：仅当文首已有版本字段时才校验（README、docs/ 根下其它 md）
    """
    seen: set[Path] = set()
    out: List[Tuple[Path, str]] = []

    def add(path: Path, policy: str) -> None:
        resolved = path.resolve()
        if resolved in seen or not path.is_file():
            return
        seen.add(resolved)
        out.append((path, policy))

    for rel in _REQUIRED_IF_EXISTS:
        add(module_root / rel, "required")

    add(module_root / "README.md", "optional")

    for path in sorted(module_root.rglob("TEST_CASES.md")):
        add(path, "required")

    docs_root = module_root / "docs"
    if docs_root.is_dir():
        for path in sorted(docs_root.glob("*.md")):
            if path.name in {"ARCHITECTURE.md", "DESIGN.md", "CONCEPTS.md"}:
                continue
            add(path, "optional")

    return out


def check_module_info_files() -> List[str]:
    missing: List[str] = []
    for label, root in _MODULE_PACKAGE_ROOTS:
        for pkg in _module_package_dirs(root):
            rel = pkg.relative_to(REPO_ROOT).as_posix()
            if not (pkg / "module_info.yaml").is_file():
                missing.append(f"{label}/{pkg.name} ({rel})")
    for label, root in _SINGLE_MODULE_ROOTS:
        if not (root / "module_info.yaml").is_file():
            missing.append(f"{label} ({root.relative_to(REPO_ROOT).as_posix()})")
    return missing


def validate_module_info_names(
    info_paths: Optional[Sequence[Path]] = None,
) -> List[str]:
    issues: List[str] = []
    for info_path in info_paths or iter_module_info_paths():
        if not info_path.is_file():
            continue
        data, err = _read_module_info(info_path)
        if err:
            issues.append(err)
            continue
        actual = str((data or {}).get("name") or "").strip()
        try:
            expected = expected_module_info_name(info_path.parent)
        except ValueError as exc:
            issues.append(str(exc))
            continue
        if actual != expected:
            issues.append(
                f"{_rel(info_path)}: name={actual!r} ≠ 标准名 {expected!r}"
            )
    return issues


def validate_module_info_changelog(
    info_paths: Optional[Sequence[Path]] = None,
) -> List[str]:
    issues: List[str] = []
    for info_path in info_paths or iter_module_info_paths():
        if not info_path.is_file():
            continue
        rel = _rel(info_path)
        data, err = _read_module_info(info_path)
        if err:
            issues.append(err)
            continue
        ver = data.get("version")
        changelog = data.get("changelog") or []
        if not changelog:
            issues.append(f"{rel}: 缺少 changelog")
            continue
        head = changelog[0] if isinstance(changelog[0], dict) else {}
        if str(head.get("version")) != str(ver):
            issues.append(
                f"{rel}: version={ver!r} 与 changelog[0].version={head.get('version')!r} 不一致"
            )
        if not head.get("changes"):
            issues.append(f"{rel}: changelog 首条 changes 为空")
    return issues


def validate_module_doc_versions(
    info_paths: Optional[Sequence[Path]] = None,
) -> List[str]:
    """文档头模块名 / 版本 / 最低支持核心版本须与 ``module_info.yaml`` 一致。"""
    issues: List[str] = []
    for info_path in info_paths or iter_module_info_paths():
        if not info_path.is_file():
            continue
        data, err = _read_module_info(info_path)
        if err:
            issues.append(err)
            continue
        ssot = str(data.get("version") or "").strip()
        core_compat = str(data.get("compatible_core_versions") or "").strip()
        mod_name = str(data.get("name") or "").strip()
        if not ssot:
            issues.append(f"{_rel(info_path)}: 缺少 version")
            continue
        if not core_compat:
            issues.append(f"{_rel(info_path)}: 缺少 compatible_core_versions")
            continue
        if not mod_name:
            issues.append(f"{_rel(info_path)}: 缺少 name")
            continue
        root = info_path.parent
        for doc_path, policy in iter_versioned_doc_paths(root):
            rel = _rel(doc_path)
            header = _header_text(doc_path)
            is_glossary = doc_path.name == "glossary.yaml"
            if _has_legacy_version_alias(header):
                issues.append(
                    f"{rel}: 文首使用非标准版本字段（覆盖版本 / 当前基线版本 / 最低核心版本），"
                    f"须改为标准两行头（模块·版本 + 最低支持核心版本）"
                )
            found = _extract_standard_version(header, is_glossary=is_glossary)
            if found is None:
                if policy == "required":
                    if is_glossary:
                        issues.append(
                            f"{rel}: 文首未找到 # Version:（应为 # Version: {ssot}）"
                        )
                    else:
                        issues.append(
                            f"{rel}: 文首未找到标准头"
                            f"（应为 **模块：** `{mod_name}` · **版本：** `{ssot}`）"
                        )
                continue
            if found != ssot:
                issues.append(
                    f"{rel}: 版本 {found!r} ≠ module_info.version {ssot!r}"
                )
            if not is_glossary:
                name_found = _extract_md_module_name(header)
                if name_found is None:
                    issues.append(
                        f"{rel}: 文首缺少 **模块：**（应与版本同行："
                        f"**模块：** `{mod_name}` · **版本：** `{ssot}`）"
                    )
                elif name_found != mod_name:
                    issues.append(
                        f"{rel}: 模块名 {name_found!r} ≠ module_info.name {mod_name!r}"
                    )
            core_found = _extract_core_compat(header, is_glossary=is_glossary)
            if core_found is None:
                if is_glossary:
                    issues.append(
                        f"{rel}: 文首未找到 # Compatible-Core:"
                        f"（应为 # Compatible-Core: {core_compat}）"
                    )
                else:
                    issues.append(
                        f"{rel}: 文首未找到最低支持核心版本（应为 {core_compat}）"
                    )
            elif core_found != core_compat:
                issues.append(
                    f"{rel}: 最低支持核心版本 {core_found!r} "
                    f"≠ module_info.compatible_core_versions {core_compat!r}"
                )
    return issues


def _insert_after_title(lines: List[str], block: str) -> List[str]:
    """在首个 AT1 后插入文首块；无 H1 则插到文件最前。"""
    block_lines = [ln + "\n" for ln in block.splitlines()]
    if block_lines and not block_lines[-1].endswith("\n"):
        block_lines[-1] += "\n"
    insert_at = 0
    for i, line in enumerate(lines[:_HEADER_LINES]):
        if line.lstrip().startswith("# ") and not line.lstrip().startswith("# Version"):
            insert_at = i + 1
            # skip one blank after title
            if insert_at < len(lines) and lines[insert_at].strip() == "":
                insert_at += 1
            break
    # ensure blank line after header block
    out_block = list(block_lines)
    if not out_block[-1].endswith("\n"):
        out_block[-1] += "\n"
    if insert_at < len(lines) and lines[insert_at].strip() != "":
        out_block.append("\n")
    return lines[:insert_at] + out_block + lines[insert_at:]


def _is_md_header_field_line(line: str) -> bool:
    s = line.strip()
    if _MD_HEADER_FIELD_LINE_RE.match(s):
        return True
    # 「**模块：** `x`」单独成行（旧拆分写法）
    if re.match(r"^\*\*模块：\*\*\s*`[^`]+`\s*$", s):
        return True
    # README 一行塞三个字段的旧写法
    if "最低核心版本" in s and "**模块：**" in s:
        return True
    return False


def _normalize_md_doc_header(path: Path, name: str, version: str, core_compat: str) -> bool:
    raw = path.read_text(encoding="utf-8")
    lines = raw.splitlines(keepends=True)

    stripped: List[str] = []
    for i, ln in enumerate(lines):
        if i < _HEADER_LINES and _is_md_header_field_line(ln):
            continue
        stripped.append(ln)

    # 压缩文首多余空行
    cleaned: List[str] = []
    blank_run = 0
    for i, ln in enumerate(stripped):
        if i < _HEADER_LINES and ln.strip() == "":
            blank_run += 1
            if blank_run > 1:
                continue
        else:
            blank_run = 0
        cleaned.append(ln)

    block = _standard_md_header(name, version, core_compat)
    desired = "".join(_insert_after_title(cleaned, block))
    if desired != raw:
        path.write_text(desired, encoding="utf-8")
        return True
    return False


def _normalize_glossary_header(path: Path, version: str, core_compat: str) -> bool:
    raw = path.read_text(encoding="utf-8")
    lines = raw.splitlines(keepends=True)
    kept: List[str] = []
    for ln in lines:
        if _GLOSSARY_HEADER_LINE_RE.match(ln.strip()):
            continue
        kept.append(ln)

    # Insert after first comment title line if present
    insert_at = 0
    if kept and kept[0].lstrip().startswith("# ") and "Version" not in kept[0]:
        insert_at = 1
    block = [
        f"# Version: {version}\n",
        f"# Compatible-Core: {core_compat}\n",
    ]
    new_lines = kept[:insert_at] + block + kept[insert_at:]
    new_text = "".join(new_lines)
    if new_text != raw:
        path.write_text(new_text, encoding="utf-8")
        return True
    return False


def sync_module_doc_versions(
    info_paths: Optional[Sequence[Path]] = None,
) -> List[str]:
    """按 module_info 改写 / 补齐文档头。返回改过的相对路径。"""
    changed: List[str] = []
    for info_path in info_paths or iter_module_info_paths():
        if not info_path.is_file():
            continue
        data, err = _read_module_info(info_path)
        if err or not data:
            continue
        ssot = str(data.get("version") or "").strip()
        core_compat = str(data.get("compatible_core_versions") or "").strip()
        mod_name = str(data.get("name") or "").strip()
        if not ssot or not core_compat or not mod_name:
            continue
        for doc_path, policy in iter_versioned_doc_paths(info_path.parent):
            header = _header_text(doc_path)
            has_version = _extract_standard_version(
                header, is_glossary=doc_path.name == "glossary.yaml"
            ) is not None or _has_legacy_version_alias(header)
            if policy == "optional" and not has_version:
                continue
            if doc_path.name == "glossary.yaml":
                touched = _normalize_glossary_header(doc_path, ssot, core_compat)
            else:
                touched = _normalize_md_doc_header(
                    doc_path, mod_name, ssot, core_compat
                )
            if touched:
                changed.append(_rel(doc_path))
    return changed
