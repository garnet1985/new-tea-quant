"""安装用静态数据包本地缓存（demo / member / full）。"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from core.infra.project_context.core.path_manager import PathManager

# 与官网 / 导出约定一致；各类型独立目录，避免混包。
PACKAGE_ZIP_BY_KIND = {
    "demo": "data_demo.zip",
    "member": "data_member.zip",
    "full": "data_full.zip",
}
PACKAGE_META_BY_KIND = {
    "demo": "data_demo.meta.json",
    "member": "data_member.meta.json",
    "full": "data_full.meta.json",
}

# 兼容旧常量名（demo）
GIT_DATA_ZIP_NAME = PACKAGE_ZIP_BY_KIND["demo"]
GIT_DATA_META_NAME = PACKAGE_META_BY_KIND["demo"]


def normalize_package_kind(kind: str = "demo") -> str:
    key = str(kind or "demo").strip().lower() or "demo"
    if key not in PathManager.DATA_PACKAGE_KINDS:
        raise ValueError(
            f"未知数据包类型: {kind!r}（可选: {', '.join(PathManager.DATA_PACKAGE_KINDS)}）"
        )
    return key


def package_zip_name(kind: str = "demo") -> str:
    return PACKAGE_ZIP_BY_KIND[normalize_package_kind(kind)]


def package_meta_name(kind: str = "demo") -> str:
    return PACKAGE_META_BY_KIND[normalize_package_kind(kind)]


def default_package_dir(kind: str = "demo") -> Path:
    """数据包目录；不检查 userspace 是否已存在。"""
    from core.infra.project_context import ProjectContext

    return ProjectContext.path.get_data_package_directory(normalize_package_kind(kind))


def migrate_legacy_demo_package(demo_dir: Path) -> None:
    """若仅有旧 ``packages/install_demo``，把 zip/meta 迁到 ``packages/demo``。"""
    from core.infra.project_context import ProjectContext

    legacy = ProjectContext.path.get_packages_root() / PathManager._LEGACY_DEMO_PACKAGE_DIR
    if not legacy.is_dir() or legacy.resolve() == demo_dir.resolve():
        return
    demo_dir.mkdir(parents=True, exist_ok=True)
    for name in (GIT_DATA_ZIP_NAME, GIT_DATA_META_NAME):
        src = legacy / name
        dst = demo_dir / name
        if not src.is_file() or dst.is_file():
            continue
        try:
            src.replace(dst)
        except OSError:
            try:
                shutil.copy2(src, dst)
            except OSError:
                pass


def require_package_dir(kind: str = "demo") -> Path:
    """
    返回可写的数据包目录；userspace 根目录不存在时抛出明确错误。
    """
    from core.infra.project_context import ProjectContext

    userspace = ProjectContext.path.get_userspace_root()
    if not userspace.is_dir():
        raise RuntimeError(
            "需要先有 userspace 文件夹才能导出或存放演示数据包。\n"
            f"当前路径不存在: {userspace}\n"
            "请先完成安装（python install.py 或 launcher），"
            "或检查 NTQ_USERSPACE_ROOT / .ntq/userspace-path.json。"
        )
    key = normalize_package_kind(kind)
    out = ProjectContext.path.get_data_package_directory(key)
    out.mkdir(parents=True, exist_ok=True)
    if key == "demo":
        migrate_legacy_demo_package(out)
    return out


def discover_package_zips(data_dir: Path) -> List[Path]:
    """目录下的 ``*.zip``（排除解压中间产物约定外的多包冲突由调用方处理）。"""
    if not data_dir.is_dir():
        return []
    return sorted(p for p in data_dir.glob("*.zip") if p.is_file())


def find_local_package_zip(kind: str = "demo") -> Optional[Path]:
    """本地是否已有该类型 zip；demo 会先尝试迁 legacy。"""
    key = normalize_package_kind(kind)
    try:
        from core.infra.project_context import ProjectContext

        userspace = ProjectContext.path.get_userspace_root()
        if not userspace.is_dir():
            return None
    except Exception:
        return None

    data_dir = default_package_dir(key)
    if key == "demo":
        migrate_legacy_demo_package(data_dir)
        legacy = PathManager.get_legacy_install_demo_package_directory()
        for folder in (data_dir, legacy):
            preferred = folder / package_zip_name(key)
            if preferred.is_file():
                return preferred
            zips = discover_package_zips(folder)
            if zips:
                return zips[0]
        return None

    preferred = data_dir / package_zip_name(key)
    if preferred.is_file():
        return preferred
    zips = discover_package_zips(data_dir)
    return zips[0] if zips else None


def describe_data_packages(
    kinds: Optional[Iterable[str]] = None,
) -> Dict[str, Any]:
    """给 UI / 设置页的本地缓存摘要。"""
    selected = list(kinds) if kinds is not None else list(PathManager.DATA_PACKAGE_KINDS)
    packages: Dict[str, Any] = {}
    for raw in selected:
        key = normalize_package_kind(raw)
        path = find_local_package_zip(key)
        present = path is not None and path.is_file()
        size_bytes = int(path.stat().st_size) if present else 0
        packages[key] = {
            "kind": key,
            "present": present,
            "fileName": path.name if present else package_zip_name(key),
            "path": str(path) if present else str(default_package_dir(key) / package_zip_name(key)),
            "sizeBytes": size_bytes,
            "sizeLabel": _size_label(size_bytes) if present else "",
        }
    any_present = any(bool(item.get("present")) for item in packages.values())
    return {
        "packages": packages,
        "anyPresent": any_present,
        "demoPresent": bool(packages.get("demo", {}).get("present")),
    }


def clear_static_data_packages() -> int:
    """删除 packages 下 demo/member/full 与旧 install_demo。返回清理的目录数。"""
    from core.infra.project_context import ProjectContext

    root = ProjectContext.path.get_packages_root()
    removed = 0
    names = list(PathManager.DATA_PACKAGE_KINDS) + [PathManager._LEGACY_DEMO_PACKAGE_DIR]
    for name in names:
        path = root / name
        if not path.exists():
            continue
        if path.is_dir():
            shutil.rmtree(path, ignore_errors=True)
        else:
            path.unlink(missing_ok=True)
        removed += 1
    return removed


def _size_label(size_bytes: int) -> str:
    mb = size_bytes / (1024 * 1024)
    if mb >= 100:
        return f"{mb:.0f} MB"
    if mb >= 1:
        return f"{mb:.1f} MB"
    kb = size_bytes / 1024
    if kb >= 1:
        return f"{kb:.0f} KB"
    return f"{size_bytes} B"
