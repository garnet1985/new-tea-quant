"""安装用静态数据包本地缓存（demo / member / full）。"""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from core.infra.project_context.contracts import DATA_PACKAGE_KINDS
from core.infra.setup.core.shared.size_format import format_size_label

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

# 会员分卷 manifest（本地齐套判定；下载实现可在官网层）。
MEMBER_MANIFEST_NAME = "data_member_3y.manifest.json"


def normalize_package_kind(kind: str = "demo") -> str:
    key = str(kind or "demo").strip().lower() or "demo"
    if key not in DATA_PACKAGE_KINDS:
        raise ValueError(
            f"未知数据包类型: {kind!r}（可选: {', '.join(DATA_PACKAGE_KINDS)}）"
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


def list_member_part_files(
    dest_dir: Path, meta: Optional[Dict[str, Any]] = None
) -> List[Path]:
    """按 manifest（或目录扫描）列出本地分卷。"""
    dest_dir = Path(dest_dir)
    if meta and isinstance(meta.get("parts"), list):
        out: List[Path] = []
        for part in meta["parts"]:
            if not isinstance(part, dict):
                continue
            name = str(part.get("file") or "").strip()
            if not name or "/" in name or "\\" in name or ".." in name:
                continue
            out.append(dest_dir / name)
        return out
    return sorted(dest_dir.glob("data_member_3y_part*.zip"))


def member_parts_complete(
    dest_dir: Path, meta: Optional[Dict[str, Any]] = None
) -> bool:
    """本地分卷是否齐全且（有 sha 时）校验通过。"""
    dest_dir = Path(dest_dir)
    if meta is None:
        manifest = dest_dir / MEMBER_MANIFEST_NAME
        if not manifest.is_file():
            return False
        try:
            meta = json.loads(manifest.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return False
    if not isinstance(meta, dict):
        return False
    parts = meta.get("parts")
    if not isinstance(parts, list) or not parts:
        return False
    for part in parts:
        if not isinstance(part, dict):
            return False
        name = str(part.get("file") or "").strip()
        path = dest_dir / name
        if not path.is_file():
            return False
        expected_sha = str(part.get("sha256") or "").strip().lower()
        expected_size = part.get("size_bytes")
        try:
            size = path.stat().st_size
        except OSError:
            return False
        if expected_size is not None:
            try:
                if size != int(expected_size):
                    return False
            except (TypeError, ValueError):
                pass
        if expected_sha:
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
            if actual != expected_sha:
                return False
    return True


def member_package_present(data_dir: Optional[Path] = None) -> bool:
    """会员分卷是否已在本地齐套。"""
    folder = Path(data_dir) if data_dir is not None else default_package_dir("member")
    return member_parts_complete(folder)


def describe_data_packages(
    kinds: Optional[Iterable[str]] = None,
) -> Dict[str, Any]:
    """给 UI / 设置页的本地缓存摘要。"""
    selected = list(kinds) if kinds is not None else list(DATA_PACKAGE_KINDS)
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
                "sizeLabel": format_size_label(size_bytes) if present else "",
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
            "sizeLabel": format_size_label(size_bytes) if present else "",
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
    for name in DATA_PACKAGE_KINDS:
        path = root / name
        if not path.exists():
            continue
        if path.is_dir():
            shutil.rmtree(path, ignore_errors=True)
        else:
            path.unlink(missing_ok=True)
        removed += 1
    return removed
