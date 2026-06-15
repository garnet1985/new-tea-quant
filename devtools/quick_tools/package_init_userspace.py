"""
将仓库根 ``userspace/`` 同步到 ``setup/init_userspace/userspace/`` 并生成 ``userspace.zip``。

由 ``dev-cli.py -userspace`` 或 ``dev-cli.py -p -vX.Y.Z -userspace`` 调用。
"""
from __future__ import annotations

import json
import shutil
import subprocess
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Sequence

from core.utils import i as icon
from devtools.quick_tools._paths import REPO_ROOT

INIT_USERSPACE_DIR = REPO_ROOT / "setup" / "init_userspace"
INIT_TREE = INIT_USERSPACE_DIR / "userspace"
ZIP_PATH = INIT_USERSPACE_DIR / "userspace.zip"
META_PATH = INIT_USERSPACE_DIR / "userspace.meta.json"
SYSTEM_JSON = REPO_ROOT / "core" / "system.json"
UPDATER_SRC = REPO_ROOT / "setup" / "updater"
UPDATER_RUNTIME_FILES: Sequence[str] = (
    "pipeline.py",
    "helper.py",
    "run_apply.py",
    "upgrade_entry.py",
    "README.md",
)

_COPY_IGNORE = shutil.ignore_patterns(
    "__pycache__",
    "*.pyc",
    "*.pyo",
    ".DS_Store",
    ".pytest_cache",
    ".git",
    "node_modules",
    ".venv",
    "*.log",
    "*.wal",
)

# 任意层级出现的运行时目录（复制阶段即跳过）
_RUNTIME_DIR_NAMES = frozenset({".ntq", "results", "cache", "output", ".cache"})


def _is_under_data_source_handlers(directory: Path) -> bool:
    parts = directory.parts
    if "handlers" not in parts or "data_source" not in parts:
        return False
    idx = parts.index("handlers")
    return idx > 0 and parts[idx - 1] == "data_source"


def _is_data_source_handler_csv(tree: Path, path: Path) -> bool:
    """``extensions/data_source/handlers/**.csv`` 为运行时产出，不进 init 包。"""
    if not path.is_file() or path.suffix.lower() != ".csv":
        return False
    parts = _relative_parts_under(tree, path)
    return (
        len(parts) >= 4
        and parts[0] == "extensions"
        and parts[1] == "data_source"
        and parts[2] == "handlers"
    )


def _is_under_strategies(tree: Path, path: Path) -> bool:
    """``path`` 位于 ``tree/strategies/**`` 下。"""
    try:
        path.relative_to(tree / "strategies")
        return True
    except ValueError:
        return False


def _is_strategy_results_dir(parent: Path, name: str) -> bool:
    """``strategies/**/results``（任意嵌套深度）。"""
    return name == "results" and "strategies" in parent.parts


def _is_tag_runtime_dir(parent: Path, name: str) -> bool:
    """``extensions/tags/<scenario>/{results,cache,...}``"""
    if name not in _RUNTIME_DIR_NAMES - {".ntq"}:
        return False
    parts = parent.parts
    return "extensions" in parts and "tags" in parts


def _copy_ignore(directory: str, names: list[str]) -> set[str]:
    """复制时跳过已知缓存/敏感目录，避免先拷后删。"""
    ignored = set(_COPY_IGNORE(directory, names) or [])
    d = Path(directory)
    for name in names:
        if name == ".ntq":
            ignored.add(name)
        if _is_strategy_results_dir(d, name) or _is_tag_runtime_dir(d, name):
            ignored.add(name)
        if name == "db" and d.name == "system":
            ignored.add(name)
        if name == "data" and d.name == "backup":
            ignored.add(name)
        if name == "auth_token.txt":
            ignored.add(name)
        if name in (".env", "secrets.json", "credentials.json"):
            ignored.add(name)
        if _is_under_data_source_handlers(d) and name.lower().endswith(".csv"):
            ignored.add(name)
    # userspace 根下的 data/（DuckDB 等）
    if (d / "strategies").is_dir() and (d / "system").is_dir() and "data" in names:
        ignored.add("data")
    return ignored


def _relative_parts_under(tree: Path, path: Path) -> tuple[str, ...]:
    return path.relative_to(tree).parts


def _is_runtime_path_in_tree(tree: Path, path: Path) -> bool:
    """打 zip 前的最后一道过滤：``.ntq``、策略 ``results/``、tag 运行时、handler csv。"""
    parts = _relative_parts_under(tree, path)
    if ".ntq" in parts:
        return True
    if _is_data_source_handler_csv(tree, path):
        return True
    if "strategies" in parts and "results" in parts[parts.index("strategies") :]:
        return True
    if "extensions" in parts and "tags" in parts and parts[-1] in _RUNTIME_DIR_NAMES:
        return True
    return False

_USER_CONFIG_JSON_NAMES = frozenset(
    {
        "data.json",
        "market.json",
        "system.json",
        "worker.json",
    }
)


def _rm_tree(path: Path) -> None:
    if not path.exists():
        return
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()


def _is_user_config_json(path: Path) -> bool:
    if path.suffix != ".json":
        return False
    if path.name.endswith(".example.json") or ".example." in path.name:
        return False
    parts = path.parts
    if "database" in parts:
        idx = parts.index("database")
        if idx > 0 and parts[idx - 1] == "config":
            return True
    if path.parent.name == "config" and path.name in _USER_CONFIG_JSON_NAMES:
        return True
    return False


def _sanitize_init_userspace(tree: Path) -> List[str]:
    """清理敏感信息与运行时缓存；返回简要操作日志。"""
    notes: List[str] = []

    for ntq in sorted({p for p in tree.rglob(".ntq") if p.is_dir()}, key=lambda p: len(p.parts)):
        _rm_tree(ntq)
        notes.append(f"删除 {ntq.relative_to(tree)}")

    for rel in ("system/db", "data"):
        p = tree / rel
        if p.exists():
            _rm_tree(p)
            notes.append(f"删除 {p.relative_to(tree)}")

    backup_data = tree / "system" / "backup" / "data"
    if backup_data.is_dir():
        for child in list(backup_data.iterdir()):
            _rm_tree(child)
            notes.append(f"删除 {child.relative_to(tree)}")

    config_dir = tree / "system" / "config"
    if config_dir.is_dir():
        for p in sorted(config_dir.rglob("*.json")):
            if _is_user_config_json(p):
                p.unlink()
                notes.append(f"删除用户配置 {p.relative_to(tree)}")

    for p in sorted(tree.rglob("auth_token.txt")):
        if p.name == "auth_token.txt":
            p.unlink()
            notes.append(f"删除 {p.relative_to(tree)}")

    ds_config = tree / "extensions" / "data_source" / "config.py"
    if ds_config.is_file():
        ds_config.unlink()
        notes.append(f"删除 {ds_config.relative_to(tree)}")

    for name in (".env", "secrets.json", "credentials.json"):
        for p in tree.rglob(name):
            _rm_tree(p)
            notes.append(f"删除 {p.relative_to(tree)}")

    ds_handlers = tree / "extensions" / "data_source" / "handlers"
    if ds_handlers.is_dir():
        for csv in sorted(ds_handlers.rglob("*.csv")):
            csv.unlink()
            notes.append(f"删除 {csv.relative_to(tree)}")

    for results in sorted(tree.rglob("results"), key=lambda p: len(p.parts), reverse=True):
        if not results.is_dir() or not _is_under_strategies(tree, results):
            continue
        _rm_tree(results)
        notes.append(f"删除 {results.relative_to(tree)}")

    tags = tree / "extensions" / "tags"
    if tags.is_dir():
        for scenario in sorted(tags.iterdir()):
            if not scenario.is_dir() or scenario.name.startswith("."):
                continue
            for sub in _RUNTIME_DIR_NAMES - {".ntq"}:
                p = scenario / sub
                if p.exists():
                    _rm_tree(p)
                    notes.append(f"删除 {p.relative_to(tree)}")

    for p in sorted(tree.rglob("*"), reverse=True):
        if p.name == "__pycache__" and p.is_dir():
            shutil.rmtree(p)
        elif p.name == ".DS_Store" and p.is_file():
            p.unlink()
        elif p.is_file() and p.suffix in (".pyc", ".pyo", ".log", ".wal", ".duckdb"):
            p.unlink()

    return notes


def _sync_updater_from_setup(tree: Path) -> List[str]:
    """用 ``setup/updater/`` 运行时文件覆盖 ``system/updater/``。"""
    notes: List[str] = []
    dest = tree / "system" / "updater"
    dest.mkdir(parents=True, exist_ok=True)
    for name in UPDATER_RUNTIME_FILES:
        src = UPDATER_SRC / name
        if not src.is_file():
            continue
        out = dest / name
        shutil.copy2(src, out)
        notes.append(f"同步 updater → {out.relative_to(tree)}")
    return notes


def _read_core_version() -> str:
    if not SYSTEM_JSON.is_file():
        raise FileNotFoundError(SYSTEM_JSON)
    data = json.loads(SYSTEM_JSON.read_text(encoding="utf-8"))
    version = str(data.get("version", "")).strip()
    if not version:
        raise RuntimeError(f"{SYSTEM_JSON} 中未配置 version")
    return version


def _git_rev(repo_root: Path) -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True,
        )
        return out.stdout.strip()
    except Exception:
        return "unknown"


def _write_userspace_meta(*, repo_root: Path, zip_path: Path | None) -> None:
    """写入 ``setup/init_userspace/userspace.meta.json``（与 ``data_demo.meta.json`` 同类）。"""
    core_raw = _read_core_version()
    core_display = core_raw if core_raw.startswith("v") else f"v{core_raw}"
    fit = core_raw.lstrip("vV")
    payload: dict[str, object] = {
        "fit_version": f">= {fit}",
        "core_version": core_display,
        "zip_file": ZIP_PATH.name,
        "built_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "git_rev": _git_rev(repo_root),
        "source": "userspace/",
    }
    target = zip_path if zip_path is not None and zip_path.is_file() else ZIP_PATH
    if target.is_file():
        payload["zip_size_bytes"] = target.stat().st_size
    META_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"{icon('success')} 已写入 {META_PATH.relative_to(REPO_ROOT)} "
        f"(core_version={core_display})",
        flush=True,
    )


def _write_userspace_zip(source_tree: Path, zip_path: Path) -> None:
    if zip_path.exists():
        zip_path.unlink()
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(source_tree.rglob("*")):
            if not path.is_file() or path.name == ".DS_Store":
                continue
            if _is_runtime_path_in_tree(source_tree, path):
                continue
            arcname = Path("userspace") / path.relative_to(source_tree)
            parts = arcname.parts
            if "__MACOSX" in parts or any(part.startswith("._") for part in parts):
                continue
            zf.write(path, arcname.as_posix())


def package_init_userspace(
    repo_root: Path | None = None,
    *,
    write_zip: bool = True,
) -> int:
    """
    复制 ``<repo>/userspace`` → ``setup/init_userspace/userspace``，清理后可选写 zip。

    Returns:
        0 成功；1 源目录不存在或其它错误。
    """
    root = (repo_root or REPO_ROOT).resolve()
    src = root / "userspace"
    if not src.is_dir():
        print(f"{icon('error')} 未找到源目录: {src}", flush=True)
        return 1

    print(f"[package-userspace] 源: {src}", flush=True)
    print(f"[package-userspace] 目标树: {INIT_TREE}", flush=True)

    if INIT_TREE.exists():
        shutil.rmtree(INIT_TREE)
    shutil.copytree(src, INIT_TREE, ignore=_copy_ignore)

    sanitize_notes = _sanitize_init_userspace(INIT_TREE)
    updater_notes = _sync_updater_from_setup(INIT_TREE)

    for line in sanitize_notes + updater_notes:
        print(f"  · {line}", flush=True)

    if write_zip:
        _write_userspace_zip(INIT_TREE, ZIP_PATH)
        print(
            f"{icon('success')} 已写入 {ZIP_PATH.relative_to(REPO_ROOT)} "
            f"（{ZIP_PATH.stat().st_size // 1024} KiB）",
            flush=True,
        )
    else:
        print(f"{icon('success')} init userspace 源树已更新（未写 zip）", flush=True)

    _write_userspace_meta(repo_root=root, zip_path=ZIP_PATH if write_zip else None)

    return 0
