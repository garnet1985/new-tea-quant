"""
Init Data 导入流程（必跑步骤的执行体）。

约定：
- 数据包目录：userspace/.ntq/packages/install_demo/（与 ``devcli.py ex`` 共用）
- 导入逻辑目录：core/infra/setup/core/steps/import_data
- 导入方式：目标表清空后，由数据库直接读 CSV（DuckDB read_csv / PostgreSQL COPY）
"""
from __future__ import annotations

from core.infra.cmd_layout import CmdLayout

import hashlib
import json
import logging
import shutil
import sys
import time
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.infra.db import Db

from .archives import collect_table_archives

logger = logging.getLogger(__name__)

EXTRACT_SUBDIR = "_extract"
DEFAULT_TABLE_PREFIX = ""
PROGRESS_FILE = ".import_progress.json"


def default_init_data_dir() -> Path:
    """演示包目录；须在 userspace 已创建之后调用。"""
    from core.infra.setup.core.scripts.init_data.config import require_package_dir

    return require_package_dir()


def _bare_table_name_for_exists_check(qualified_table: str) -> str:
    s = qualified_table.strip().strip('"')
    if "." in s:
        return s.rsplit(".", 1)[-1].strip('"')
    return s


def _count_rows_in_table(db, qualified_table: str) -> int:
    try:
        bare = _bare_table_name_for_exists_check(qualified_table)
        if not db.is_table_exists(bare):
            return 0
        rows = db.execute_sync_query(f"SELECT COUNT(*) AS cnt FROM {qualified_table}")
        if not rows:
            return 0
        r = rows[0]
        n = r.get("cnt") if "cnt" in r else r.get("count", 0)
        return int(n or 0)
    except Exception:
        return 0


def _file_fingerprint(paths: List[Path]) -> str:
    parts: List[str] = []
    for p in sorted(paths):
        st = p.stat()
        parts.append(f"{p.name}:{st.st_size}:{st.st_mtime_ns}")
    payload = "|".join(parts).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


class SetupDataInstaller:
    def __init__(
        self,
        data_dir: Optional[Path] = None,
        *,
        table_prefix: str = DEFAULT_TABLE_PREFIX,
    ) -> None:
        try:
            self.data_dir = (
                Path(data_dir) if data_dir is not None else default_init_data_dir()
            )
        except RuntimeError as exc:
            raise RuntimeError(f"{CmdLayout.icon.get('error')} {exc}") from exc
        self.table_prefix = table_prefix.rstrip("_") + "_" if table_prefix else ""
        self.progress_file = self.data_dir / PROGRESS_FILE

    def discover_data_packages(self) -> List[Path]:
        if not self.data_dir.is_dir():
            return []
        zips = sorted(self.data_dir.glob("*.zip"))
        if len(zips) <= 1:
            return zips
        names = ", ".join(p.name for p in zips)
        raise RuntimeError(
            f"{CmdLayout.icon.get('error')} 为避免混包导入，演示包目录下只允许存在 1 个 .zip。\n"
            f"目录: {self.data_dir}\n"
            f"当前发现 {len(zips)} 个：{names}\n"
            "请保留您需要导入的 zip，另一个移走/改后缀后重新运行: python cli.py id"
        )

    def ensure_demo_package(self, *, force_download: bool = False) -> Path:
        """本地无 zip（或 force）时从官网公开接口下载 ``data_demo.zip``。"""
        from core.infra.setup.core.env import NewTeaQuantSetup
        from core.modules.ntq_external.install_demo import (
            InstallDemoError,
            download_install_demo,
        )

        existing = self.discover_data_packages()
        if existing and not force_download:
            return existing[0]

        NewTeaQuantSetup.print_check_item(
            "running",
            "正在从官网下载演示数据包（公开，无需会员）…",
        )
        try:
            path = download_install_demo(self.data_dir, force=force_download)
        except InstallDemoError as exc:
            raise RuntimeError(
                f"{CmdLayout.icon.get('error')} 下载演示数据包失败: {exc}\n"
                "请检查网络后重跑: python cli.py id\n"
                "本地联调可设 NTQ_INSTALL_DEMO_URL 指向官网或本机 XAMPP。"
            ) from exc
        NewTeaQuantSetup.print_check_item("done", f"演示数据包已就绪: {path.name}")
        return path

    def _extract_zips(self, extract_root: Path) -> List[Path]:
        from core.infra.setup.core.env import NewTeaQuantSetup

        zips = self.discover_data_packages()
        if not zips:
            raise FileNotFoundError(f"在 {self.data_dir} 下未找到 .zip 文件")

        if extract_root.exists():
            shutil.rmtree(extract_root)
        extract_root.mkdir(parents=True, exist_ok=True)

        for z in zips:
            dest = extract_root / z.stem
            dest.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(z, "r") as zf:
                zf.extractall(dest)
            NewTeaQuantSetup.print_check_info(f"已解压: {z.name} -> {dest}")
        return zips

    def _build_plan_rows(self, dm, plan: dict) -> List[Dict[str, Any]]:
        db = dm.db
        rows: List[Dict[str, Any]] = []
        for logical in sorted(plan.keys()):
            paths = plan[logical]
            target = f"{self.table_prefix}{logical}"
            model = dm.get_table(logical)
            registered = model is not None
            existing_rows = 0
            qualified = ""
            if registered and db:
                qualified = Db.sql.qualify_table_name(db.config, target)
                existing_rows = _count_rows_in_table(db, qualified)
            arch_names = [p.name for p in paths]
            if len(arch_names) == 1:
                arch_summary = arch_names[0]
            else:
                arch_summary = f"{len(arch_names)} 个归档"
            rows.append(
                {
                    "logical": logical,
                    "target": target,
                    "qualified": qualified,
                    "existing_rows": existing_rows,
                    "archive_basename_summary": arch_summary,
                    "archives": paths,
                    "will_import": registered,
                }
            )
        return rows

    def _load_progress(self) -> Dict[str, Any]:
        if not self.progress_file.is_file():
            return {}
        try:
            return json.loads(self.progress_file.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _save_progress(self, payload: Dict[str, Any]) -> None:
        self.progress_file.parent.mkdir(parents=True, exist_ok=True)
        self.progress_file.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _clear_progress(self) -> None:
        if self.progress_file.exists():
            self.progress_file.unlink()

    def _cleanup_temp_after_success(
        self,
        extract_root: Path,
        *,
        remove_extract: bool = True,
        remove_package_files: bool = True,
    ) -> None:
        """导入成功后清理解压目录、进度文件，以及已入库的下载包（可再从官网拉取）。"""
        from core.infra.setup.core.env import NewTeaQuantSetup
        from core.infra.setup.core.scripts.init_data.config import (
            GIT_DATA_META_NAME,
            GIT_DATA_ZIP_NAME,
        )

        if remove_extract and extract_root.exists():
            shutil.rmtree(extract_root, ignore_errors=True)
        self._clear_progress()
        if not remove_package_files:
            return
        removed: List[str] = []
        for name in (GIT_DATA_ZIP_NAME, GIT_DATA_META_NAME):
            path = self.data_dir / name
            if not path.is_file():
                continue
            try:
                path.unlink()
                removed.append(name)
            except OSError as exc:
                logger.warning("无法删除临时包文件 %s: %s", path, exc)
        if removed:
            NewTeaQuantSetup.print_check_item(
                "done",
                f"已清理临时演示包文件: {', '.join(removed)}",
            )

    def run(
        self,
        *,
        force: bool = False,
        remove_extract: bool = True,
    ) -> None:
        from core.infra.setup.core.env import NewTeaQuantSetup
        from core.modules.data_manager import DataManager

        t0_all = time.perf_counter()
        data_dir = self.data_dir
        extract_root = data_dir / EXTRACT_SUBDIR

        self.ensure_demo_package(force_download=force)
        zips = self.discover_data_packages()
        if not zips:
            raise RuntimeError(
                f"{CmdLayout.icon.get('error')} 未找到初始化数据包: {data_dir}\n"
                "请检查网络后重跑: python cli.py id"
            )

        fingerprint = _file_fingerprint(zips)
        NewTeaQuantSetup.print_check_item("done", f"发现初始化数据包 {len(zips)} 个")

        t_extract = time.perf_counter()
        self._extract_zips(extract_root)
        plan = collect_table_archives(extract_root)
        if not plan:
            raise RuntimeError(
                f"解压后未找到任何 .tar.gz/.zip 数据归档，请检查 zip 内容: {extract_root}"
            )
        dt_extract = time.perf_counter() - t_extract
        NewTeaQuantSetup.print_check_item(
            "done",
            f"数据完整性检查通过，识别表 {len(plan)} 个（解压与扫描 {dt_extract:.1f}s）",
        )

        t_dm = time.perf_counter()
        dm = DataManager(is_verbose=False)
        dm.initialize()
        dt_dm = time.perf_counter() - t_dm
        NewTeaQuantSetup.print_check_info(f"DataManager 初始化耗时 {dt_dm:.1f}s")
        db = dm.db
        if not db:
            raise RuntimeError("数据库不可用")

        try:
            t_plan = time.perf_counter()
            rows = self._build_plan_rows(dm, plan)
            importable = [r for r in rows if r["will_import"]]
            if not importable:
                raise RuntimeError("没有可导入的表（均在框架中未注册 model）")
            dt_plan = time.perf_counter() - t_plan

            NewTeaQuantSetup.print_check_item(
                "done",
                f"创建导入清单：可导入 {len(importable)} 张表（清单构建 {dt_plan:.1f}s）",
            )

            prev = self._load_progress() if not force else {}
            same_profile = prev.get("fingerprint") == fingerprint
            completed = prev.get("completed_tables", {}) if same_profile else {}
            pending = [r for r in importable if completed.get(r["logical"]) != "done"]

            progress_payload: Dict[str, Any] = {
                "fingerprint": fingerprint,
                "data_dir": str(data_dir),
                "updated_at": int(time.time()),
                "completed_tables": completed.copy(),
                "total_tables": len(importable),
                "table_order": [r["logical"] for r in importable],
                "in_progress_table": None,
                "interrupted_at": None,
            }
            self._save_progress(progress_payload)

            if not pending:
                dt_setup = time.perf_counter() - t0_all
                NewTeaQuantSetup.print_check_item(
                    "done",
                    f"所有表已在当前数据包指纹下导入完成（import_data 本步 {dt_setup:.1f}s）",
                )
                self._cleanup_temp_after_success(
                    extract_root,
                    remove_extract=remove_extract,
                )
                return

            from core.infra.setup.core.install_progress import (
                begin_import_table,
                cancel_import,
                cancel_import_table,
                close_import,
                fail_import,
                fail_import_table,
                finish_import_table,
                open_import,
            )

            total = len(importable)
            done_names = [
                name
                for name, state in completed.items()
                if state == "done"
            ]
            open_import([row["logical"] for row in importable], done_names=done_names)
            errors: List[Tuple[str, str]] = []
            t_import_loop = time.perf_counter()
            for r in pending:
                logical = r["logical"]
                target = r["target"]
                paths = r["archives"]
                model = dm.get_table(logical)
                assert model is not None

                begin_import_table(logical)
                try:
                    finished = len(progress_payload["completed_tables"])
                    position = finished + 1
                    progress_payload["in_progress_table"] = logical
                    progress_payload["updated_at"] = int(time.time())
                    self._save_progress(progress_payload)

                    t0 = time.perf_counter()
                    NewTeaQuantSetup.print_check_item(
                        "running",
                        f"[{position}/{total}] 导入 {logical} -> {target}",
                    )
                    model.import_data(paths, target_table=target)
                    dt = time.perf_counter() - t0
                    NewTeaQuantSetup.print_check_item(
                        "done",
                        f"[{position}/{total}] {logical} 完成（{dt:.1f}s）",
                    )
                    progress_payload["completed_tables"][logical] = "done"
                    progress_payload["in_progress_table"] = None
                    progress_payload["updated_at"] = int(time.time())
                    self._save_progress(progress_payload)
                    finish_import_table(logical)
                except KeyboardInterrupt:
                    progress_payload["completed_tables"].pop(logical, None)
                    progress_payload["in_progress_table"] = None
                    progress_payload["interrupted_at"] = int(time.time())
                    progress_payload["updated_at"] = int(time.time())
                    self._save_progress(progress_payload)
                    cancel_import_table(logical, "导入被中断")
                    cancel_import("导入被中断")
                    NewTeaQuantSetup.print_check_item(
                        "fail",
                        f"[{position}/{total}] {logical} 被中断（可重跑继续）",
                    )
                    raise
                except Exception as e:
                    logger.exception("导入失败: %s -> %s", logical, target)
                    errors.append((logical, str(e)))
                    progress_payload["completed_tables"].pop(logical, None)
                    progress_payload["in_progress_table"] = None
                    progress_payload["updated_at"] = int(time.time())
                    self._save_progress(progress_payload)
                    fail_import_table(logical, str(e))
                    NewTeaQuantSetup.print_check_item(
                        "fail",
                        f"[{position}/{total}] {logical} 失败",
                    )

            dt_import_tables = time.perf_counter() - t_import_loop
            dt_setup_all = time.perf_counter() - t0_all

            if errors:
                NewTeaQuantSetup.print_check_item(
                    "fail",
                    f"初始化数据导入存在失败项（导入各表 {dt_import_tables:.1f}s，import_data 全程 {dt_setup_all:.1f}s）",
                )
                fail_import("部分表导入失败")
                raise RuntimeError(f"部分表导入失败: {errors}")

            NewTeaQuantSetup.print_check_item(
                "done",
                f"初始化数据导入完成（导入各表 {dt_import_tables:.1f}s；import_data 全程 {dt_setup_all:.1f}s）",
            )
            close_import()
            self._cleanup_temp_after_success(
                extract_root,
                remove_extract=remove_extract,
            )
        finally:
            try:
                if db is not None:
                    db.checkpoint_duckdb()
                    db.close()
            except Exception as exc:
                logger.warning("导入结束后 DuckDB CHECKPOINT/close 未完全成功: %s", exc)
            DataManager.reset_instance()
