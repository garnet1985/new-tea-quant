"""
模块版本字段与 ``module_info.yaml`` 对齐。

由 ``devcli.py pack`` / ``p`` 调用。``module_info.yaml`` 为 SSOT。

文首字段（硬性命名，禁止别名）：

- Markdown：``**版本：** `X.Y.Z` ``
- ``glossary.yaml``：``# Version: X.Y.Z``
- ``API.md`` 另须：``**最低支持核心版本：** `<range>` ``（= ``compatible_core_versions``）
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
_MD_VERSION_RE = re.compile(rf"\*\*版本：\*\*\s*`?(?P<ver>{_SEMVER})`?")
_GLOSSARY_VERSION_RE = re.compile(rf"^#\s*Version:\s*(?P<ver>{_SEMVER})\s*$", re.M)
_CORE_COMPAT_RE = re.compile(r"\*\*最低支持核心版本：\*\*\s*`(?P<ver>[^`]+)`")

# 历史别名（校验时报非标准；sync 改写成 **版本：**）
_LEGACY_COVER_LINE_RE = re.compile(r"\*\*覆盖版本：\*\*[^\n]*")
_LEGACY_BASELINE_LINE_RE = re.compile(r"\*\*当前基线版本：\*\*[^\n]*")

_MD_VERSION_SUB_RE = re.compile(rf"(\*\*版本：\*\*\s*`?)({_SEMVER})(`?)")
_GLOSSARY_VERSION_SUB_RE = re.compile(rf"(# Version:\s*)({_SEMVER})")
_CORE_COMPAT_SUB_RE = re.compile(r"(\*\*最低支持核心版本：\*\*\s*`)([^`]+)(`)")


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


def _extract_standard_version(header: str, *, is_glossary: bool) -> Optional[str]:
    if is_glossary:
        found = _GLOSSARY_VERSION_RE.search(header)
        return found.group("ver") if found else None
    found = _MD_VERSION_RE.search(header)
    return found.group("ver") if found else None


def _has_legacy_version_alias(header: str) -> bool:
    return bool(_LEGACY_COVER_LINE_RE.search(header) or _LEGACY_BASELINE_LINE_RE.search(header))


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
    """文档头 ``**版本：**`` / ``# Version:`` / API 最低核心版本须与 ``module_info.yaml`` 一致。"""
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
        if not ssot:
            issues.append(f"{_rel(info_path)}: 缺少 version")
            continue
        root = info_path.parent
        for doc_path, policy in iter_versioned_doc_paths(root):
            rel = _rel(doc_path)
            header = _header_text(doc_path)
            is_glossary = doc_path.name == "glossary.yaml"
            if _has_legacy_version_alias(header):
                issues.append(
                    f"{rel}: 文首使用非标准版本字段（**覆盖版本：** / **当前基线版本：**），"
                    f"须改为 **版本：** `{ssot}`"
                )
            found = _extract_standard_version(header, is_glossary=is_glossary)
            if found is None:
                if policy == "required":
                    issues.append(f"{rel}: 文首未找到标准版本字段（应为 **版本：** `{ssot}`）")
                continue
            if found != ssot:
                issues.append(
                    f"{rel}: 版本 {found!r} ≠ module_info.version {ssot!r}"
                )
            if doc_path.name == "API.md" and core_compat:
                core_found = _CORE_COMPAT_RE.search(header)
                if core_found is None:
                    issues.append(
                        f"{rel}: 文首未找到最低支持核心版本（应为 {core_compat}）"
                    )
                elif core_found.group("ver").strip() != core_compat:
                    issues.append(
                        f"{rel}: 最低支持核心版本 {core_found.group('ver')!r} "
                        f"≠ module_info.compatible_core_versions {core_compat!r}"
                    )
    return issues


def _rewrite_header(path: Path, pattern: re.Pattern[str], replacement: str) -> bool:
    raw = path.read_text(encoding="utf-8")
    lines = raw.splitlines(keepends=True)
    head = "".join(lines[:_HEADER_LINES])
    rest = "".join(lines[_HEADER_LINES:])
    new_head, n = pattern.subn(replacement, head, count=1)
    if n == 0:
        return False
    if new_head != head:
        path.write_text(new_head + rest, encoding="utf-8")
        return True
    return False


def _rewrite_legacy_alias_line(path: Path, ssot: str) -> bool:
    raw = path.read_text(encoding="utf-8")
    lines = raw.splitlines(keepends=True)
    head = "".join(lines[:_HEADER_LINES])
    rest = "".join(lines[_HEADER_LINES:])
    replacement = f"**版本：** `{ssot}`  "
    new_head, n1 = _LEGACY_COVER_LINE_RE.subn(replacement, head, count=1)
    new_head, n2 = _LEGACY_BASELINE_LINE_RE.subn(replacement, new_head, count=1)
    if n1 + n2 == 0 or new_head == head:
        return False
    path.write_text(new_head + rest, encoding="utf-8")
    return True


def sync_module_doc_versions(
    info_paths: Optional[Sequence[Path]] = None,
) -> List[str]:
    """按 module_info 改写已有文档头版本（只动文首第一次出现）。返回改过的相对路径。"""
    changed: List[str] = []
    for info_path in info_paths or iter_module_info_paths():
        if not info_path.is_file():
            continue
        data, err = _read_module_info(info_path)
        if err or not data:
            continue
        ssot = str(data.get("version") or "").strip()
        core_compat = str(data.get("compatible_core_versions") or "").strip()
        if not ssot:
            continue
        for doc_path, _policy in iter_versioned_doc_paths(info_path.parent):
            touched = False
            if _rewrite_legacy_alias_line(doc_path, ssot):
                touched = True
            if doc_path.name == "glossary.yaml":
                touched = (
                    _rewrite_header(
                        doc_path, _GLOSSARY_VERSION_SUB_RE, rf"\g<1>{ssot}"
                    )
                    or touched
                )
            else:
                touched = (
                    _rewrite_header(
                        doc_path, _MD_VERSION_SUB_RE, rf"\g<1>{ssot}\g<3>"
                    )
                    or touched
                )
            if doc_path.name == "API.md" and core_compat:
                touched = (
                    _rewrite_header(
                        doc_path, _CORE_COMPAT_SUB_RE, rf"\g<1>{core_compat}\g<3>"
                    )
                    or touched
                )
            if touched:
                changed.append(_rel(doc_path))
    return changed
