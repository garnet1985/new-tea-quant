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
    return out


def discover_package_zips(data_dir: Path) -> List[Path]:
    """目录下的 ``*.zip``（排除解压中间产物约定外的多包冲突由调用方处理）。"""
    if not data_dir.is_dir():
        return []
    return sorted(p for p in data_dir.glob("*.zip") if p.is_file())


def find_local_package_zip(kind: str = "demo") -> Optional[Path]:
    """本地是否已有该类型 zip。"""
    key = normalize_package_kind(kind)
    try:
        from core.infra.project_context import ProjectContext

        userspace = ProjectContext.path.get_userspace_root()
        if not userspace.is_dir():
            return None
    except Exception:
        return None

    data_dir = default_package_dir(key)
    if key == "member":
        if member_package_present(data_dir):
            parts = sorted(data_dir.glob("data_member_3y_part*.zip"))
            return parts[0] if parts else data_dir / package_zip_name(key)
        preferred = data_dir / package_zip_name(key)
        if preferred.is_file():
            return preferred
        return None

    preferred = data_dir / package_zip_name(key)
    if preferred.is_file():
        return preferred
    zips = discover_package_zips(data_dir)
    return zips[0] if zips else None


def member_package_present(data_dir: Optional[Path] = None) -> bool:
    """会员分卷是否已在本地齐套。"""
    from core.modules.ntq_external.install_member import member_parts_complete

    folder = Path(data_dir) if data_dir is not None else default_package_dir("member")
    return member_parts_complete(folder)


def describe_data_packages(
    kinds: Optional[Iterable[str]] = None,
) -> Dict[str, Any]:
    """给 UI / 设置页的本地缓存摘要。"""
    selected = list(kinds) if kinds is not None else list(PathManager.DATA_PACKAGE_KINDS)
    packages: Dict[str, Any] = {}
    for raw in selected:
        key = normalize_package_kind(raw)
        data_dir = default_package_dir(key)
        if key == "member":
            present = member_package_present(data_dir)
            parts = sorted(data_dir.glob("data_member_3y_part*.zip")) if present else []
            size_bytes = sum(p.stat().st_size for p in parts) if parts else 0
            packages[key] = {
                "kind": key,
                "present": present,
                "fileName": parts[0].name if parts else package_zip_name(key),
                "path": str(data_dir),
                "sizeBytes": size_bytes,
                "sizeLabel": _size_label(size_bytes) if present else "",
                "partCount": len(parts),
            }
            continue
        path = find_local_package_zip(key)
        present = path is not None and path.is_file()
        size_bytes = int(path.stat().st_size) if present else 0
        packages[key] = {
            "kind": key,
            "present": present,
            "fileName": path.name if present else package_zip_name(key),
            "path": str(path) if present else str(data_dir / package_zip_name(key)),
            "sizeBytes": size_bytes,
            "sizeLabel": _size_label(size_bytes) if present else "",
        }
    any_present = any(bool(item.get("present")) for item in packages.values())
    return {
        "packages": packages,
        "anyPresent": any_present,
        "demoPresent": bool(packages.get("demo", {}).get("present")),
        "memberPresent": bool(packages.get("member", {}).get("present")),
    }


def clear_static_data_packages() -> int:
    """删除 packages 下 demo/member/full。返回清理的目录数。"""
    from core.infra.project_context import ProjectContext

    root = ProjectContext.path.get_packages_root()
    removed = 0
    for name in PathManager.DATA_PACKAGE_KINDS:
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
