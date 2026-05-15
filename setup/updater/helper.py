"""升级器的实施细节与小工具（HTTP、semver、raw URL、zip 等）；对外编排见 ``pipeline``。"""
from __future__ import annotations

import json
import os
import shlex
import shutil
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
import zipfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

REMOTE_REPO = ("https://gitee.com/garnet/new-tea-quant", "https://github.com/garnet1985/new-tea-quant")
VERSION_FILE = "core/system.json"
UPDATE_PLAN_FILE = "update_plan.json"
SUPPORTED_PLAN_SCHEMA_VERSIONS = frozenset({1, 2})
_DEFAULT_REMOTE_REF = "master"
DEFAULT_REMOTE_REF = _DEFAULT_REMOTE_REF

_raw_timeout = (os.environ.get("NTQ_UPDATE_CHECK_TIMEOUT") or "15").strip() or "15"
try:
    REQUEST_TIMEOUT_SEC = float(_raw_timeout)
except ValueError:
    REQUEST_TIMEOUT_SEC = 15.0
if REQUEST_TIMEOUT_SEC <= 0:
    REQUEST_TIMEOUT_SEC = 15.0

_zip_raw = (os.environ.get("NTQ_UPDATE_ZIP_TIMEOUT") or "300").strip() or "300"
try:
    ZIP_DOWNLOAD_TIMEOUT_SEC = float(_zip_raw)
except ValueError:
    ZIP_DOWNLOAD_TIMEOUT_SEC = 300.0
if ZIP_DOWNLOAD_TIMEOUT_SEC <= 0:
    ZIP_DOWNLOAD_TIMEOUT_SEC = 300.0


def update_bundle_dir(repo_root: Path) -> Path:
    """缓存 zip、staging 等：``<repo>/userspace/.ntq/update``。"""
    return (repo_root / "userspace" / ".ntq" / "update").resolve()


PRE_MIRROR_CORE_TABLE_SCHEMAS_FILE = "pre_mirror_core_table_schemas.json"


def snapshot_core_table_schemas_for_migration(repo_root: Path) -> Optional[Path]:
    """
    在 ``managed_scope`` 覆盖本地 ``core/`` **之前**，把当前 ``core/tables`` 下全部 ``schema.py``
    解析结果写入 ``userspace/.ntq/update/cache/pre_mirror_core_table_schemas.json``，
    供 ``core/infra/db`` 迁移与旧版期望 schema 对照（镜像后磁盘上的旧版 ``core/tables`` 可能已不存在）。

    **跳过**（返回 ``None``）：环境变量 ``NTQ_UPDATE_SKIP_SCHEMA_SNAPSHOT=1``；
    ``core/tables`` 目录不存在；无法导入 ``SchemaManager``（例如未设置 ``PYTHONPATH``）。

    Returns:
        写入的 JSON 文件路径；跳过时为 ``None``。
    """
    skip = (os.environ.get("NTQ_UPDATE_SKIP_SCHEMA_SNAPSHOT") or "").strip().lower()
    if skip in {"1", "true", "yes", "on"}:
        return None

    tables = (repo_root / "core" / "tables").resolve()
    if not tables.is_dir():
        return None

    try:
        from core.infra.db.schema_management.schema_manager import SchemaManager
    except ImportError:
        return None

    cache = update_bundle_dir(repo_root) / "cache"
    cache.mkdir(parents=True, exist_ok=True)
    out = (cache / PRE_MIRROR_CORE_TABLE_SCHEMAS_FILE).resolve()

    sm = SchemaManager(tables_dir=str(tables))
    schemas = sm.load_all_schemas()
    payload = {name: json.loads(json.dumps(s, default=str)) for name, s in schemas.items()}
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def default_remote_ref() -> str:
    return (os.environ.get("NTQ_REMOTE_REF") or _DEFAULT_REMOTE_REF).strip() or _DEFAULT_REMOTE_REF


def read_local_version(repo_root: Path, relative_path: str = VERSION_FILE) -> Optional[str]:
    path = (repo_root / relative_path).resolve()
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    v = data.get("version")
    return str(v).strip() if isinstance(v, str) and v.strip() else None


def extract_version_string(payload: Dict[str, Any]) -> Optional[str]:
    v = payload.get("version")
    if isinstance(v, str) and v.strip():
        return v.strip()
    return None


def raw_system_json_url(repo_base: str, ref: str, relative_path: str) -> str:
    base = repo_base.rstrip("/")
    rel = relative_path.strip().lstrip("/")
    if "gitee.com" in base:
        return f"{base}/raw/{ref}/{rel}"
    if "github.com" in base:
        tail = base.split("github.com/", 1)[-1].strip("/")
        parts = tail.split("/")
        if len(parts) < 2:
            return ""
        owner, repo = parts[0], parts[1]
        return f"https://raw.githubusercontent.com/{owner}/{repo}/{ref}/{rel}"
    return ""


def archive_zip_url(repo_base: str, ref: str) -> str:
    """
    与 ``raw_system_json_url`` 同一套 ``REMOTE_REPO`` base，指向 **分支源码 zip**（非 Release 资产）。

    - Gitee: ``{base}/repository/archive/{ref}.zip``
    - GitHub: ``{base}/archive/refs/heads/{ref}.zip``
    """
    base = repo_base.rstrip("/")
    if "gitee.com" in base:
        return f"{base}/repository/archive/{ref}.zip"
    if "github.com" in base:
        return f"{base}/archive/refs/heads/{ref}.zip"
    return ""


def download_url_to_file(url: str, dest: Path, timeout_sec: float) -> bool:
    """HTTP GET 写入 ``dest``（先写同目录 ``.part`` 再 ``replace``）。成功返回 True。"""
    dest = dest.resolve()
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_name(dest.name + ".part")
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "NTQ-update-zip/1"},
            method="GET",
        )
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            code = getattr(resp, "status", None) or resp.getcode()
            if code != 200:
                return False
            with open(part, "wb") as out:
                shutil.copyfileobj(resp, out, length=64 * 1024)
    except (
        urllib.error.URLError,
        TimeoutError,
        OSError,
        TypeError,
        ValueError,
    ):
        if part.is_file():
            part.unlink(missing_ok=True)
        return False

    try:
        if dest.is_file():
            dest.unlink()
        part.replace(dest)
    except OSError:
        if part.is_file():
            part.unlink(missing_ok=True)
        return False
    return True


def safe_extract_zip(zip_path: Path, dest_dir: Path) -> None:
    """将 zip 解压到 ``dest_dir``；拒绝 zip slip（路径跳出目标目录）。"""
    dest_dir = dest_dir.resolve()
    dest_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zf:
        for info in zf.infolist():
            name = info.filename
            if name.startswith("/") or ".." in Path(name).parts:
                raise ValueError(f"Unsafe zip entry: {name!r}")
            target = (dest_dir / name).resolve()
            try:
                target.relative_to(dest_dir)
            except ValueError as e:
                raise ValueError(f"Zip slip: {name!r}") from e
        zf.extractall(dest_dir)


def resolve_archive_root(extract_parent: Path) -> Path:
    """
    GitHub/Gitee 源码 zip 解压后通常有一层 ``{repo}-{ref}/``；若仅一层子目录则返回该目录，否则返回 ``extract_parent``。
    """
    extract_parent = extract_parent.resolve()
    if not extract_parent.is_dir():
        return extract_parent
    children = [p for p in extract_parent.iterdir() if p.name not in ("__MACOSX",)]
    if len(children) == 1 and children[0].is_dir():
        return children[0].resolve()
    return extract_parent


def is_zip_archive(path: Path) -> bool:
    """若路径为可读 zip 则 True（用于过滤 HTML 错误页等非 zip 响应）。"""
    if not path.is_file():
        return False
    return zipfile.is_zipfile(path)


def http_get_json(url: str, timeout_sec: float) -> Optional[Dict[str, Any]]:
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "NTQ-update-check/1"},
            method="GET",
        )
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            code = getattr(resp, "status", None) or resp.getcode()
            if code != 200:
                return None
            raw = resp.read().decode("utf-8")
        data = json.loads(raw)
    except (
        urllib.error.URLError,
        TimeoutError,
        OSError,
        TypeError,
        json.JSONDecodeError,
        UnicodeDecodeError,
        ValueError,
    ):
        return None
    return data if isinstance(data, dict) else None


def semver_gt(a: str, b: str) -> bool:
    """若 ``a`` 比 ``b`` 新则 True；解析失败则 False。"""
    ta, tb = semver_tuple(a), semver_tuple(b)
    if ta is None or tb is None:
        return False
    return ta > tb


def semver_tuple(version: str) -> Optional[tuple[int, ...]]:
    s = version.strip().lstrip("vV")
    if not s:
        return None
    parts: list[int] = []
    for seg in s.split(".")[:4]:
        n = ""
        for ch in seg:
            if ch.isdigit():
                n += ch
            else:
                break
        parts.append(int(n) if n else 0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts)


def read_json_dict(path: Path) -> Optional[Dict[str, Any]]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError, TypeError):
        return None
    return raw if isinstance(raw, dict) else None


def _is_safe_rel_posix(rel: str) -> bool:
    if rel == "":
        return True
    p = Path(rel.replace("\\", "/"))
    if p.is_absolute():
        return False
    return ".." not in p.parts


def _normalize_scope_entry(item: str) -> str:
    s = item.strip().replace("\\", "/")
    if not s:
        raise ValueError("managed_scope entry must not be empty")
    if s.startswith("/") or not _is_safe_rel_posix(s):
        raise ValueError(f"invalid managed_scope entry: {item!r}")
    return s


def validate_update_plan(raw: Dict[str, Any]) -> Dict[str, Any]:
    """返回规范化后的 plan（``plan_schema_version``、``managed_scope``、``update_ignored_paths``、``payload_root``）。"""
    schema_raw = raw.get("plan_schema_version", 1)
    if isinstance(schema_raw, bool) or not isinstance(schema_raw, int):
        raise ValueError("plan_schema_version must be an integer")
    if schema_raw not in SUPPORTED_PLAN_SCHEMA_VERSIONS:
        raise ValueError(f"unsupported plan_schema_version: {schema_raw}")

    ms = raw.get("managed_scope")
    if not isinstance(ms, list) or not ms:
        raise ValueError("managed_scope must be a non-empty list of strings")
    scope: List[str] = []
    for x in ms:
        if not isinstance(x, str):
            raise ValueError("managed_scope entries must be strings")
        scope.append(_normalize_scope_entry(x))

    ig = raw.get("update_ignored_paths", [])
    if ig is None:
        ig = []
    if not isinstance(ig, list):
        raise ValueError("update_ignored_paths must be a list")
    ignored: List[str] = []
    for x in ig:
        if not isinstance(x, str) or not x.strip():
            continue
        sx = x.strip().replace("\\", "/")
        if sx.startswith("/") or not _is_safe_rel_posix(sx):
            raise ValueError(f"invalid update_ignored_paths entry: {x!r}")
        ignored.append(sx)

    pr_raw = raw.get("payload_root", "")
    if pr_raw is None:
        pr_raw = ""
    if not isinstance(pr_raw, str):
        raise ValueError("payload_root must be a string")
    pr = pr_raw.strip().replace("\\", "/")
    if pr == ".":
        pr = ""
    if pr.startswith("/") or not _is_safe_rel_posix(pr):
        raise ValueError(f"invalid payload_root: {pr_raw!r}")

    return {
        "plan_schema_version": schema_raw,
        "managed_scope": scope,
        "update_ignored_paths": ignored,
        "payload_root": pr,
    }


def build_update_plan_from_system_json(data: Dict[str, Any]) -> Dict[str, Any]:
    """与 ``core.system.SystemMeta`` 一致：优先 ``update_plan`` 嵌套，否则根级 ``managed_scope`` / ``update_ignored_paths``。"""
    plan = data.get("update_plan") if isinstance(data.get("update_plan"), dict) else {}
    out: Dict[str, Any] = {}
    pv = plan.get("plan_schema_version", 1)
    if isinstance(pv, int) and not isinstance(pv, bool) and pv in SUPPORTED_PLAN_SCHEMA_VERSIONS:
        out["plan_schema_version"] = pv
    else:
        out["plan_schema_version"] = 1

    ms = plan.get("managed_scope")
    if not (isinstance(ms, list) and all(isinstance(x, str) for x in ms)):
        ms = data.get("managed_scope")
    out["managed_scope"] = ms if isinstance(ms, list) else []

    ig = plan.get("update_ignored_paths")
    if not (isinstance(ig, list) and all(isinstance(x, str) for x in ig)):
        ig = data.get("update_ignored_paths")
    out["update_ignored_paths"] = ig if isinstance(ig, list) else []

    pr = plan.get("payload_root", "")
    out["payload_root"] = pr if isinstance(pr, str) else ""
    return out


def load_update_plan_from_staging(staging_dir: Path) -> Dict[str, Any]:
    """
    从 staging 根目录读取 ``update_plan.json``；若无则读 ``core/system.json`` 并抽取 ``update_plan``（及根级回退字段）。

    源码 zip 无独立 plan 时 ``payload_root`` 一般为空字符串，表示 ``managed_scope`` 项相对 **staging 仓库根**。
    """
    staging_dir = staging_dir.resolve()
    if not staging_dir.is_dir():
        raise FileNotFoundError(f"staging_dir is not a directory: {staging_dir}")

    plan_path = staging_dir / UPDATE_PLAN_FILE
    if plan_path.is_file():
        raw = read_json_dict(plan_path)
        if raw is None:
            raise ValueError(f"invalid or empty JSON object in {plan_path}")
        return validate_update_plan(raw)

    sys_path = staging_dir / VERSION_FILE
    if sys_path.is_file():
        raw = read_json_dict(sys_path)
        if raw is None:
            raise ValueError(f"invalid or empty JSON object in {sys_path}")
        merged = build_update_plan_from_system_json(raw)
        return validate_update_plan(merged)

    raise FileNotFoundError(
        f"no {UPDATE_PLAN_FILE} or {VERSION_FILE} under staging {staging_dir}"
    )


def http_post(url: str, timeout_sec: float) -> bool:
    """空 body POST；2xx 返回 True。"""
    try:
        req = urllib.request.Request(
            url,
            data=b"",
            headers={"User-Agent": "NTQ-update-stop/1"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            code = getattr(resp, "status", None) or resp.getcode()
            return 200 <= int(code) < 300
    except (
        urllib.error.URLError,
        TimeoutError,
        OSError,
        TypeError,
        ValueError,
    ):
        return False


def _pid_exists(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _terminate_pid(pid: int, wait_sec: float) -> None:
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    deadline = time.monotonic() + wait_sec
    while time.monotonic() < deadline and _pid_exists(pid):
        time.sleep(0.2)
    force = os.environ.get("NTQ_UPDATE_FORCE_KILL", "").strip().lower() in ("1", "true", "yes")
    if force and _pid_exists(pid):
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass


def _read_pid_file(path: Path) -> Optional[int]:
    try:
        line = path.read_text(encoding="utf-8").splitlines()[0].strip()
    except (OSError, UnicodeDecodeError, IndexError):
        return None
    if not line:
        return None
    try:
        return int(line)
    except ValueError:
        return None


def kill_main_app_hooks(repo_root: Path) -> None:
    """
    按 **首个生效** 的环境钩子停主进程（避免重复执行）：

    1. ``NTQ_UPDATE_KILL_CMD``：``shlex.split`` 后在 ``repo_root`` 下 ``subprocess.run``（超时 ``NTQ_UPDATE_KILL_CMD_TIMEOUT``，默认 120s）。
    2. ``NTQ_UPDATE_STOP_URL``：HTTP POST（超时 ``NTQ_UPDATE_STOP_TIMEOUT``，默认 30s）；不校验响应体。
    3. ``NTQ_UPDATE_PID_FILE``：相对 ``repo_root`` 或绝对路径，首行 PID，``SIGTERM``；等待 ``NTQ_UPDATE_PID_WAIT_SEC``（默认 8s）；可选 ``NTQ_UPDATE_FORCE_KILL`` 再 ``SIGKILL``。
    4. ``NTQ_UPDATE_MAIN_PIDS``：逗号分隔 PID，同上信号逻辑。

    若均未配置则 **no-op**（由调用方在启动流水线前自行停服）。
    """
    repo_root = repo_root.resolve()
    cmd = os.environ.get("NTQ_UPDATE_KILL_CMD", "").strip()
    if cmd:
        t_raw = (os.environ.get("NTQ_UPDATE_KILL_CMD_TIMEOUT") or "120").strip() or "120"
        try:
            t = float(t_raw)
        except ValueError:
            t = 120.0
        subprocess.run(shlex.split(cmd), cwd=str(repo_root), timeout=t if t > 0 else None, check=False)
        return

    url = os.environ.get("NTQ_UPDATE_STOP_URL", "").strip()
    if url:
        t_raw = (os.environ.get("NTQ_UPDATE_STOP_TIMEOUT") or "30").strip() or "30"
        try:
            t = float(t_raw)
        except ValueError:
            t = 30.0
        http_post(url, max(t, 1.0))
        return

    pid_file = os.environ.get("NTQ_UPDATE_PID_FILE", "").strip()
    if pid_file:
        p = Path(pid_file)
        if not p.is_absolute():
            p = (repo_root / p).resolve()
        pid = _read_pid_file(p)
        if pid is not None and pid > 0:
            w_raw = (os.environ.get("NTQ_UPDATE_PID_WAIT_SEC") or "8").strip() or "8"
            try:
                w = float(w_raw)
            except ValueError:
                w = 8.0
            _terminate_pid(pid, max(w, 0.5))
        return

    raw_pids = os.environ.get("NTQ_UPDATE_MAIN_PIDS", "").strip()
    if raw_pids:
        w_raw = (os.environ.get("NTQ_UPDATE_PID_WAIT_SEC") or "8").strip() or "8"
        try:
            w = float(w_raw)
        except ValueError:
            w = 8.0
        for part in raw_pids.split(","):
            part = part.strip()
            if not part:
                continue
            try:
                pid = int(part)
            except ValueError:
                continue
            if pid > 0:
                _terminate_pid(pid, max(w, 0.5))
        return


def _norm_rel_posix(s: str) -> str:
    return s.strip().replace("\\", "/").strip("/")


def ignored_paths_under_managed_scope(
    managed_scope: List[str],
    update_ignored_paths: List[str],
) -> List[str]:
    """
    返回 ``update_ignored_paths`` 中落在任一 ``managed_scope`` 前缀下的相对路径（posix）。

    与 README「管辖内镜像会动到子树」一致：例如 ``setup`` 在 map 内且 ``setup/init_data`` 在忽略名单，
    则需在镜像前 lift-out ``setup/init_data``。
    """
    scopes = [_norm_rel_posix(x) for x in managed_scope if _norm_rel_posix(x)]
    out: List[str] = []
    for ig in update_ignored_paths:
        ig_n = _norm_rel_posix(ig)
        if not ig_n:
            continue
        for ms in scopes:
            if ig_n == ms or ig_n.startswith(ms + "/"):
                out.append(ig_n)
                break
    return sorted(set(out))


def repo_path_under_root(repo_root: Path, rel_posix: str) -> Path:
    """``repo_root / rel`` 解析后必须仍在仓库根下，否则 ``ValueError``。"""
    root = repo_root.resolve()
    if not rel_posix or rel_posix.startswith("/") or ".." in Path(rel_posix.replace("\\", "/")).parts:
        raise ValueError(f"unsafe repo rel: {rel_posix!r}")
    p = (root / rel_posix).resolve()
    p.relative_to(root)
    return p


def _is_under_ntq_update_bundle(path: Path, repo_root: Path) -> bool:
    """避免把 ``userspace/.ntq/update`` 自身拷进 lift-out（递归/膨胀）。"""
    try:
        path.resolve().relative_to(update_bundle_dir(repo_root).resolve())
        return True
    except ValueError:
        return False


def lift_out_session_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def copy_tree_or_file_overwrite(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        if dest.is_dir():
            shutil.rmtree(dest)
        else:
            dest.unlink()
    if src.is_dir():
        shutil.copytree(src, dest, symlinks=False, dirs_exist_ok=False)
    elif src.is_file():
        shutil.copy2(src, dest)
    else:
        raise OSError(f"copy source is not a file or directory: {src}")


def write_lift_out_manifest(backup_dir: Path, entries: List[Dict[str, Any]]) -> Path:
    payload = {"schema_version": 1, "entries": entries}
    path = backup_dir / "lift_out_manifest.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def run_lift_out_backup(
    repo_root: Path,
    managed_scope: List[str],
    update_ignored_paths: List[str],
) -> Optional[Path]:
    """
    将「在管辖内且被忽略」的已存在路径递归 **复制** 到
    ``userspace/.ntq/update/lift-out/<UTC 时间>/``，并写入 ``lift_out_manifest.json``。

    若无候选、或候选在磁盘上均不存在、或均在 ``.ntq/update`` bundle 内被跳过，则返回 ``None``。
    """
    targets = ignored_paths_under_managed_scope(managed_scope, update_ignored_paths)
    if not targets:
        return None

    root = repo_root.resolve()
    bundle = update_bundle_dir(root)
    to_copy: List[tuple[str, Path]] = []
    for rel in targets:
        try:
            src = repo_path_under_root(root, rel)
        except ValueError:
            continue
        if not src.exists():
            continue
        if _is_under_ntq_update_bundle(src, root):
            continue
        to_copy.append((rel, src))

    if not to_copy:
        return None

    backup_dir = (bundle / "lift-out" / lift_out_session_id()).resolve()
    backup_dir.mkdir(parents=True, exist_ok=False)
    manifest_entries: List[Dict[str, Any]] = []
    try:
        for rel, src in to_copy:
            dest = backup_dir / rel
            copy_tree_or_file_overwrite(src, dest)
            kind = "directory" if src.is_dir() else "file"
            manifest_entries.append({"repo_rel": rel, "kind": kind, "backup_relpath": rel})
        write_lift_out_manifest(backup_dir, manifest_entries)
    except Exception:
        shutil.rmtree(backup_dir, ignore_errors=True)
        raise
    return backup_dir


def read_lift_out_manifest(backup_dir: Path) -> Dict[str, Any]:
    """读取并校验 ``lift_out_manifest.json``（``schema_version`` 必须为 1）。"""
    backup_dir = backup_dir.resolve()
    path = backup_dir / "lift_out_manifest.json"
    if not path.is_file():
        raise FileNotFoundError(f"missing lift_out_manifest.json under {backup_dir}")
    data = read_json_dict(path)
    if data is None:
        raise ValueError(f"invalid manifest JSON: {path}")
    if data.get("schema_version") != 1:
        raise ValueError(f"unsupported lift_out manifest schema: {data.get('schema_version')!r}")
    entries = data.get("entries")
    if not isinstance(entries, list):
        raise ValueError("manifest entries must be a list")
    for i, e in enumerate(entries):
        if not isinstance(e, dict):
            raise ValueError(f"manifest entry {i} must be an object")
        rel = e.get("repo_rel")
        if not isinstance(rel, str) or not _norm_rel_posix(rel):
            raise ValueError(f"manifest entry {i} needs non-empty string repo_rel")
        br = e.get("backup_relpath", rel)
        if not isinstance(br, str) or not _norm_rel_posix(br):
            raise ValueError(f"manifest entry {i} needs non-empty string backup_relpath")
    return data


def run_lift_out_restore(repo_root: Path, backup_dir: Path) -> None:
    """
    按 manifest 将 ``backup_dir`` 下的树 **覆盖写回** ``repo_root`` 下对应 ``repo_rel``。

    条目按路径深度 **从深到浅** 还原，避免父子条目互相覆盖。备份侧缺失的条目跳过。
    禁止还原目标落在 ``userspace/.ntq/update`` 下。
    """
    backup_dir = backup_dir.resolve()
    root = repo_root.resolve()
    if not backup_dir.is_dir():
        raise FileNotFoundError(f"lift-out backup dir not found: {backup_dir}")
    manifest = read_lift_out_manifest(backup_dir)
    entries: List[Dict[str, Any]] = list(manifest["entries"])

    def _entry_depth(repo_rel: str) -> int:
        return len(_norm_rel_posix(repo_rel).split("/"))

    entries.sort(key=lambda e: _entry_depth(str(e["repo_rel"])), reverse=True)
    bundle = update_bundle_dir(root).resolve()

    for e in entries:
        rel = _norm_rel_posix(str(e["repo_rel"]))
        br = _norm_rel_posix(str(e.get("backup_relpath", rel)))
        src = (backup_dir / br).resolve()
        try:
            src.relative_to(backup_dir)
        except ValueError as ex:
            raise ValueError(f"backup artifact escapes backup dir: {br!r}") from ex
        if not src.exists():
            continue
        dest = repo_path_under_root(root, rel)
        try:
            dest.resolve().relative_to(bundle)
        except ValueError:
            pass
        else:
            raise ValueError(f"refusing to restore into update bundle: {rel!r}")
        copy_tree_or_file_overwrite(src, dest)


def read_managed_scope_from_repo(repo_root: Path) -> List[str]:
    """
    从本地 ``VERSION_FILE``（``core/system.json``）读取 ``managed_scope``，
    规则与 ``build_update_plan_from_system_json`` 一致；文件缺失或无效时返回空列表。
    """
    root = repo_root.resolve()
    p = root / VERSION_FILE
    if not p.is_file():
        return []
    raw = read_json_dict(p)
    if not raw:
        return []
    merged = build_update_plan_from_system_json(raw)
    ms = merged.get("managed_scope", [])
    if not isinstance(ms, list):
        return []
    out: List[str] = []
    for x in ms:
        if isinstance(x, str) and _norm_rel_posix(x):
            out.append(_norm_rel_posix(x))
    return out


def unique_managed_scope_preserve_order(managed_scope: List[str]) -> List[str]:
    """``managed_scope`` 去重（posix 规范化），保留首次出现顺序。"""
    seen: set[str] = set()
    out: List[str] = []
    for x in managed_scope:
        n = _norm_rel_posix(x)
        if not n or n in seen:
            continue
        seen.add(n)
        out.append(n)
    return out


_GLOBAL_MIRROR_SKIP_FIRST = frozenset(
    ("userspace", ".git", "backup", ".env", "config.ini", "secrets.json")
)


def is_global_preserve_managed_entry(rel: str) -> bool:
    """
    顶层镜像永不触碰的路径（防配置误伤）。

    正常 ``managed_scope`` 不应包含这些名；若包含则 **跳过** 该项。
    """
    n = _norm_rel_posix(rel)
    if not n:
        return True
    seg0 = n.split("/")[0]
    if seg0 in _GLOBAL_MIRROR_SKIP_FIRST:
        return True
    if seg0.startswith(".env."):
        return True
    return False


def obsolete_managed_top_levels(old_ms: List[str], new_ms: List[str]) -> List[str]:
    """「旧 map 有、新 map 无」的顶层项（规范化、排序）。"""
    old_s = {_norm_rel_posix(x) for x in old_ms if _norm_rel_posix(x)}
    new_s = {_norm_rel_posix(x) for x in new_ms if _norm_rel_posix(x)}
    return sorted(old_s - new_s)


def remove_obsolete_managed_top_levels(repo_root: Path, old_ms: List[str], new_ms: List[str]) -> None:
    """删掉已退出 ``managed_scope`` 的顶层路径（全局保留项不删）。"""
    root = repo_root.resolve()
    for rel in obsolete_managed_top_levels(old_ms, new_ms):
        if is_global_preserve_managed_entry(rel):
            continue
        try:
            target = repo_path_under_root(root, rel)
        except ValueError:
            continue
        if not target.exists():
            continue
        if target.is_dir():
            shutil.rmtree(target)
        else:
            target.unlink()


def staging_source_for_managed_item(staging_dir: Path, payload_root: str, item: str) -> Path:
    """解析 ``staging`` 内对应 ``managed_scope`` 条目的源路径，并保证落在 ``staging_dir`` 下。"""
    staging_dir = staging_dir.resolve()
    pr = _norm_rel_posix(payload_root)
    it = _norm_rel_posix(item)
    src = (staging_dir / pr / it) if pr else (staging_dir / it)
    src = src.resolve()
    src.relative_to(staging_dir)
    return src


def install_managed_items_from_staging(
    repo_root: Path,
    staging_dir: Path,
    payload_root: str,
    new_managed_scope: List[str],
) -> None:
    """
    对新 ``managed_scope`` 每一项（去重保序）：删除 ``repo_root/<项>`` 后，
    自 ``staging_dir[/payload_root]/<项>`` 整目录/整文件覆盖拷贝。
    """
    root = repo_root.resolve()
    staging_dir = staging_dir.resolve()
    for item in unique_managed_scope_preserve_order(new_managed_scope):
        if is_global_preserve_managed_entry(item):
            continue
        src = staging_source_for_managed_item(staging_dir, payload_root, item)
        if not src.exists():
            raise RuntimeError(f"NTQ updater: staging missing managed item {item!r} (expected {src})")
        dest = repo_path_under_root(root, item)
        if dest.exists():
            if dest.is_dir():
                shutil.rmtree(dest)
            else:
                dest.unlink()
        copy_tree_or_file_overwrite(src, dest)


def repo_venv_python(repo_root: Path) -> Optional[Path]:
    """若存在标准 ``venv/`` 则返回其 ``python`` 可执行文件路径，否则 ``None``。"""
    root = repo_root.resolve()
    if os.name == "nt":
        p = root / "venv" / "Scripts" / "python.exe"
    else:
        p = root / "venv" / "bin" / "python"
    return p if p.is_file() else None


def python_for_repo_commands(repo_root: Path) -> Path:
    """优先使用仓库 ``venv`` 解释器，否则退回当前 ``sys.executable``。"""
    v = repo_venv_python(repo_root)
    return v if v is not None else Path(sys.executable).resolve()


def _env_truthy(name: str) -> bool:
    return (os.environ.get(name) or "").strip().lower() in ("1", "true", "yes", "on")


def migration_logs_dir(repo_root: Path) -> Path:
    d = (update_bundle_dir(repo_root) / "logs").resolve()
    d.mkdir(parents=True, exist_ok=True)
    return d


def resolve_pre_mirror_snapshot_path(
    repo_root: Path,
    pre_mirror_snapshot: Optional[Path] = None,
) -> Path:
    if pre_mirror_snapshot is not None:
        return pre_mirror_snapshot.resolve()
    return (
        update_bundle_dir(repo_root) / "cache" / PRE_MIRROR_CORE_TABLE_SCHEMAS_FILE
    ).resolve()


@dataclass
class DatabaseMigrationResult:
    """``spawn_database_migration_cli`` 的执行摘要（供 ``UpgradeContext`` 与 UI 使用）。"""

    skipped: bool = False
    skipped_reason: Optional[str] = None
    snapshot_path: Optional[Path] = None
    log_path: Optional[Path] = None
    result_json_path: Optional[Path] = None
    exit_code: Optional[int] = None
    applied: bool = False
    step_count: Optional[int] = None
    old_schema_count: Optional[int] = None
    new_schema_count: Optional[int] = None


def _preflight_migrate_module(repo_root: Path, py: Path, env: Dict[str, str]) -> None:
    r = subprocess.run(
        [str(py), "-c", "import core.infra.db.migrate"],
        cwd=str(repo_root),
        env=env,
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        detail = (r.stderr or r.stdout or "").strip()
        raise RuntimeError(
            "NTQ updater: cannot import core.infra.db.migrate "
            f"(check PYTHONPATH/venv). {detail}"
        )


def _load_migration_result_json(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def spawn_database_migration_cli(
    repo_root: Path,
    pre_mirror_snapshot: Optional[Path] = None,
    *,
    dry_run: bool = False,
) -> DatabaseMigrationResult:
    """
    子进程调用 ``python -m core.infra.db.migrate apply``，stdout/stderr 写入 ``userspace/.ntq/update/logs/``。

    - 跳过整步：``NTQ_UPDATE_SKIP_DB_MIGRATION=1``
    - 无快照文件：默认 **抛出 RuntimeError**；设 ``NTQ_UPDATE_ALLOW_MISSING_SCHEMA_SNAPSHOT=1`` 则跳过并返回 ``skipped=True``
  """
    if _env_truthy("NTQ_UPDATE_SKIP_DB_MIGRATION"):
        return DatabaseMigrationResult(
            skipped=True,
            skipped_reason="NTQ_UPDATE_SKIP_DB_MIGRATION",
        )

    repo_root = repo_root.resolve()
    snap = resolve_pre_mirror_snapshot_path(repo_root, pre_mirror_snapshot)

    if not snap.is_file():
        msg = (
            f"schema 快照不存在，无法执行数据库迁移: {snap} "
            f"(须先完成步骤 6 快照，或设置 NTQ_UPDATE_ALLOW_MISSING_SCHEMA_SNAPSHOT=1 显式跳过)"
        )
        if _env_truthy("NTQ_UPDATE_ALLOW_MISSING_SCHEMA_SNAPSHOT"):
            return DatabaseMigrationResult(
                skipped=True,
                skipped_reason=msg,
                snapshot_path=snap,
            )
        raise RuntimeError(f"NTQ updater: {msg}")

    py = python_for_repo_commands(repo_root)
    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo_root)

    _preflight_migrate_module(repo_root, py, env)

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    log_path = migration_logs_dir(repo_root) / f"migrate-{ts}.log"
    result_json_path = (
        update_bundle_dir(repo_root) / "cache" / "last_migration_result.json"
    ).resolve()
    result_json_path.parent.mkdir(parents=True, exist_ok=True)

    cmd: List[str] = [
        str(py),
        "-m",
        "core.infra.db.migrate",
        "apply",
        "--pre-mirror-snapshot",
        str(snap),
        "--repo-root",
        str(repo_root),
        "--result-json",
        str(result_json_path),
    ]
    if dry_run:
        cmd.append("--dry-run")
    if _env_truthy("NTQ_UPDATE_VERBOSE_MIGRATION"):
        cmd.insert(3, "-v")

    with log_path.open("w", encoding="utf-8") as log_f:
        log_f.write(f"# cmd: {' '.join(shlex.quote(c) for c in cmd)}\n\n")
        log_f.flush()
        r = subprocess.run(
            cmd,
            cwd=str(repo_root),
            env=env,
            stdout=log_f,
            stderr=subprocess.STDOUT,
            text=True,
        )

    summary = _load_migration_result_json(result_json_path)
    out = DatabaseMigrationResult(
        skipped=bool(summary.get("skipped_reason")),
        skipped_reason=summary.get("skipped_reason"),
        snapshot_path=snap,
        log_path=log_path,
        result_json_path=result_json_path,
        exit_code=r.returncode,
        applied=bool(summary.get("applied")),
        step_count=summary.get("step_count"),
        old_schema_count=summary.get("old_schema_count"),
        new_schema_count=summary.get("new_schema_count"),
    )

    if r.returncode != 0:
        raise RuntimeError(
            f"NTQ updater: database migration failed (exit {r.returncode}), log: {log_path}"
        )

    return out


@dataclass
class PostUpgradeResult:
    """``spawn_post_upgrade_actions_cli`` 的执行摘要。"""

    skipped: bool = False
    skipped_reason: Optional[str] = None
    log_path: Optional[Path] = None
    result_json_path: Optional[Path] = None
    exit_code: Optional[int] = None
    executed_count: int = 0
    action_ids: Optional[List[str]] = None


def _preflight_post_upgrade_module(repo_root: Path, py: Path, env: Dict[str, str]) -> None:
    r = subprocess.run(
        [str(py), "-c", "import core.infra.update.post_upgrade"],
        cwd=str(repo_root),
        env=env,
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        detail = (r.stderr or r.stdout or "").strip()
        raise RuntimeError(
            "NTQ updater: cannot import core.infra.update.post_upgrade "
            f"(check PYTHONPATH/venv). {detail}"
        )


def spawn_post_upgrade_actions_cli(repo_root: Path) -> PostUpgradeResult:
    """
    子进程调用 ``python -m core.infra.update.post_upgrade run``。

    执行 **新版** ``core/infra/update/post_upgrade`` 中已注册的收尾动作；注册表为空时子进程正常退出（跳过）。
    跳过整步：``NTQ_UPDATE_SKIP_POST_UPGRADE=1``。
    """
    if _env_truthy("NTQ_UPDATE_SKIP_POST_UPGRADE"):
        return PostUpgradeResult(
            skipped=True,
            skipped_reason="NTQ_UPDATE_SKIP_POST_UPGRADE",
        )

    repo_root = repo_root.resolve()
    py = python_for_repo_commands(repo_root)
    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo_root)

    _preflight_post_upgrade_module(repo_root, py, env)

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    log_path = migration_logs_dir(repo_root) / f"post-upgrade-{ts}.log"
    result_json_path = (
        update_bundle_dir(repo_root) / "cache" / "last_post_upgrade_result.json"
    ).resolve()
    result_json_path.parent.mkdir(parents=True, exist_ok=True)

    cmd: List[str] = [
        str(py),
        "-m",
        "core.infra.update.post_upgrade",
        "run",
        "--repo-root",
        str(repo_root),
        "--result-json",
        str(result_json_path),
    ]
    if _env_truthy("NTQ_UPDATE_VERBOSE_POST_UPGRADE"):
        cmd.insert(3, "-v")

    with log_path.open("w", encoding="utf-8") as log_f:
        log_f.write(f"# cmd: {' '.join(shlex.quote(c) for c in cmd)}\n\n")
        log_f.flush()
        r = subprocess.run(
            cmd,
            cwd=str(repo_root),
            env=env,
            stdout=log_f,
            stderr=subprocess.STDOUT,
            text=True,
        )

    summary = _load_migration_result_json(result_json_path)
    action_ids = summary.get("action_ids")
    if not isinstance(action_ids, list):
        action_ids = None

    out = PostUpgradeResult(
        skipped=bool(summary.get("skipped")),
        skipped_reason=summary.get("skipped_reason"),
        log_path=log_path,
        result_json_path=result_json_path,
        exit_code=r.returncode,
        executed_count=int(summary.get("executed_count") or 0),
        action_ids=action_ids,
    )

    if r.returncode != 0:
        raise RuntimeError(
            f"NTQ updater: post-upgrade failed (exit {r.returncode}), log: {log_path}"
        )

    return out


@dataclass
class UpgradeCleanupResult:
    """``cleanup_after_upgrade`` 的摘要。"""

    skipped: bool = False
    skipped_reason: Optional[str] = None
    removed_paths: List[str] = field(default_factory=list)


def _remove_path(path: Path, removed: List[str]) -> None:
    p = path.resolve()
    if not p.exists():
        return
    if p.is_dir():
        shutil.rmtree(p, ignore_errors=False)
    else:
        p.unlink(missing_ok=True)
    removed.append(str(p))


def cleanup_after_upgrade(
    repo_root: Path,
    *,
    staging_dir: Optional[Path] = None,
    zip_path: Optional[Path] = None,
    lift_out_backup_dir: Optional[Path] = None,
    pre_mirror_snapshot_path: Optional[Path] = None,
) -> UpgradeCleanupResult:
    """
    升级成功后清理 ``userspace/.ntq/update`` 下的 **临时** 产物。

    默认删除：
    - ``staging/``（含 ``staging/current`` 解压树）
    - ``inbox/`` 内本次下载的 zip（``zip_path``）
    - 已还原的 ``lift-out/<session>/``（``lift_out_backup_dir``）
    - ``cache/pre_mirror_core_table_schemas.json``（镜像前快照，迁移已结束后一般不再需要）

    默认 **保留**：``logs/``、``cache/last_migration_result.json``、``cache/last_post_upgrade_result.json``。

    跳过整步：``NTQ_UPDATE_SKIP_CLEANUP=1``。
    保留项：``NTQ_UPDATE_KEEP_INBOX_ZIP``、``NTQ_UPDATE_KEEP_LIFT_OUT``、
    ``NTQ_UPDATE_KEEP_PRE_MIRROR_SNAPSHOT``、``NTQ_UPDATE_KEEP_STAGING``。
    """
    if _env_truthy("NTQ_UPDATE_SKIP_CLEANUP"):
        return UpgradeCleanupResult(
            skipped=True,
            skipped_reason="NTQ_UPDATE_SKIP_CLEANUP",
        )

    repo_root = repo_root.resolve()
    bundle = update_bundle_dir(repo_root)
    removed: List[str] = []

    if not _env_truthy("NTQ_UPDATE_KEEP_STAGING"):
        staging_root = (bundle / "staging").resolve()
        if staging_root.exists():
            _remove_path(staging_root, removed)

    if zip_path is not None and not _env_truthy("NTQ_UPDATE_KEEP_INBOX_ZIP"):
        zp = zip_path.resolve()
        if zp.is_file():
            _remove_path(zp, removed)

    if lift_out_backup_dir is not None and not _env_truthy("NTQ_UPDATE_KEEP_LIFT_OUT"):
        _remove_path(lift_out_backup_dir.resolve(), removed)

    if pre_mirror_snapshot_path is not None and not _env_truthy("NTQ_UPDATE_KEEP_PRE_MIRROR_SNAPSHOT"):
        _remove_path(pre_mirror_snapshot_path.resolve(), removed)
    elif not _env_truthy("NTQ_UPDATE_KEEP_PRE_MIRROR_SNAPSHOT"):
        default_snap = bundle / "cache" / PRE_MIRROR_CORE_TABLE_SCHEMAS_FILE
        if default_snap.is_file():
            _remove_path(default_snap, removed)

    return UpgradeCleanupResult(removed_paths=removed)


def reinstall_runtime_dependencies_cli(repo_root: Path, *, force: bool = True) -> None:
    """
    **纯命令行**：重装运行期依赖，供 ``pipeline._reinstall_dependencies`` 与后续 UI 共用。

    1. 若存在 ``requirements.txt`` 且未设 ``NTQ_UPDATE_SKIP_ROOT_REQUIREMENTS``：``pip install -r``（仓库根）。
    2. 子进程内 ``setup.ui_runtime.install_ui_runtime(force=...)``（BFF pip + FED ``npm install``，与 ``install.py`` 对齐）。

    跳过整步：``NTQ_UPDATE_SKIP_RUNTIME_REINSTALL=1``。``PYTHONPATH`` 设为 ``repo_root`` 以便导入 ``setup`` / ``core``。
    """
    if os.environ.get("NTQ_UPDATE_SKIP_RUNTIME_REINSTALL", "").strip().lower() in ("1", "true", "yes"):
        return

    repo_root = repo_root.resolve()
    py = python_for_repo_commands(repo_root)
    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo_root)

    skip_root = os.environ.get("NTQ_UPDATE_SKIP_ROOT_REQUIREMENTS", "").strip().lower() in ("1", "true", "yes")
    req = repo_root / "requirements.txt"
    if req.is_file() and not skip_root:
        cmd: List[str] = [str(py), "-m", "pip", "install", "--no-compile", "--prefer-binary", "-r", str(req)]
        if os.environ.get("NTQ_PIP_NO_CACHE", "").strip().lower() in ("1", "true", "yes"):
            cmd.insert(-2, "--no-cache-dir")
        r = subprocess.run(cmd, cwd=str(repo_root), env=env)
        if r.returncode != 0:
            raise RuntimeError("NTQ updater: pip install -r requirements.txt failed")

    snippet = (
        "from setup.ui_runtime import install_ui_runtime\n"
        f"install_ui_runtime(force={force!r})\n"
    )
    r = subprocess.run([str(py), "-c", snippet], cwd=str(repo_root), env=env)
    if r.returncode != 0:
        raise RuntimeError("NTQ updater: install_ui_runtime failed")
