"""
Init Data 导入流程（必跑步骤的执行体）。

约定：
- 数据包目录：setup/init_data
- 导入逻辑目录：setup/setup_data
- 导入方式：目标表 DELETE 再 INSERT（沿用现有 import_data 逻辑）
"""
from __future__ import annotations

import hashlib
import json
import logging
import shutil
import sys
import time
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.infra.db.helpers.db_helpers import DBHelper

from .archives import collect_table_archives

logger = logging.getLogger(__name__)

DEFAULT_INIT_SUBDIR = "init_data"
EXTRACT_SUBDIR = "_extract"
DEFAULT_TABLE_PREFIX = ""
PROGRESS_FILE = ".import_progress.json"


def default_init_data_dir() -> Path:
    return Path(__file__).resolve().parent.parent / DEFAULT_INIT_SUBDIR


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
        self.data_dir = Path(data_dir) if data_dir is not None else default_init_data_dir()
        self.table_prefix = table_prefix.rstrip("_") + "_" if table_prefix else ""
        self.progress_file = self.data_dir / PROGRESS_FILE

    def discover_data_packages(self) -> List[Path]:
        if not self.data_dir.is_dir():
            return []
        return sorted(self.data_dir.glob("*.zip"))

    def _extract_zips(self, extract_root: Path) -> List[Path]:
        from setup.setup import NewTeaQuantSetup

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
                qualified = DBHelper.sql_qualify_table_name(db.config, target)
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

    def run(
        self,
        *,
        force: bool = False,
        remove_extract: bool = True,
    ) -> None:
        from setup.setup import NewTeaQuantSetup
        from core.modules.data_manager import DataManager

        t0_all = time.perf_counter()
        data_dir = self.data_dir
        extract_root = data_dir / EXTRACT_SUBDIR

        zips = self.discover_data_packages()
        if not zips:
            NewTeaQuantSetup.print_check_item("warn", f"未发现任何初始化数据包: {data_dir}")
            NewTeaQuantSetup.print_check_item(
                "warn",
                "请将 zip 数据包放到 setup/init_data 后重跑: python3 install.py",
            )
            return

        fingerprint = _file_fingerprint(zips)
        NewTeaQuantSetup.print_check_item("done", f"发现初始化数据包 {len(zips)} 个")

        self._extract_zips(extract_root)
        plan = collect_table_archives(extract_root)
        if not plan:
            raise RuntimeError(
                f"解压后未找到任何 .tar.gz/.zip 数据归档，请检查 zip 内容: {extract_root}"
            )
        NewTeaQuantSetup.print_check_item("done", f"数据完整性检查通过，识别表 {len(plan)} 个")

        dm = DataManager(is_verbose=False)
        dm.initialize()
        db = dm.db
        if not db:
            raise RuntimeError("数据库不可用")

        rows = self._build_plan_rows(dm, plan)
        importable = [r for r in rows if r["will_import"]]
        if not importable:
            raise RuntimeError("没有可导入的表（均在框架中未注册 model）")

        NewTeaQuantSetup.print_check_item(
            "running",
            f"创建导入清单完成：可导入 {len(importable)} 张表",
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
            "in_progress_table": None,
            "interrupted_at": None,
        }
        self._save_progress(progress_payload)

        if not pending:
            NewTeaQuantSetup.print_check_item("done", "所有表已在当前数据包指纹下导入完成")
            # 断点文件仅服务导入过程；全部完成后删除。
            self._clear_progress()
            return

        total = len(pending)
        errors: List[Tuple[str, str]] = []
        for idx, r in enumerate(pending, start=1):
            logical = r["logical"]
            target = r["target"]
            paths = r["archives"]
            model = dm.get_table(logical)
            assert model is not None

            try:
                progress_payload["in_progress_table"] = logical
                progress_payload["updated_at"] = int(time.time())
                self._save_progress(progress_payload)

                t0 = time.perf_counter()
                NewTeaQuantSetup.print_check_item(
                    "running",
                    f"[{idx}/{total}] 导入 {logical} -> {target}",
                )
                model.import_data(paths, target_table=target)
                dt = time.perf_counter() - t0
                NewTeaQuantSetup.print_check_item(
                    "done",
                    f"[{idx}/{total}] {logical} 完成（{dt:.1f}s）",
                )
                progress_payload["completed_tables"][logical] = "done"
                progress_payload["in_progress_table"] = None
                progress_payload["updated_at"] = int(time.time())
                self._save_progress(progress_payload)
            except KeyboardInterrupt:
                # 当前表视为未完成：不写 done，保持可重跑整表。
                progress_payload["completed_tables"].pop(logical, None)
                progress_payload["in_progress_table"] = None
                progress_payload["interrupted_at"] = int(time.time())
                progress_payload["updated_at"] = int(time.time())
                self._save_progress(progress_payload)
                NewTeaQuantSetup.print_check_item(
                    "fail",
                    f"[{idx}/{total}] {logical} 被中断（可重跑继续）",
                )
                raise
            except Exception as e:
                logger.exception("导入失败: %s -> %s", logical, target)
                errors.append((logical, str(e)))
                # 当前表视为未完成：不写 done，保持可重跑整表。
                progress_payload["completed_tables"].pop(logical, None)
                progress_payload["in_progress_table"] = None
                progress_payload["updated_at"] = int(time.time())
                self._save_progress(progress_payload)
                NewTeaQuantSetup.print_check_item(
                    "fail",
                    f"[{idx}/{total}] {logical} 失败",
                )

        dt_all = time.perf_counter() - t0_all
        if remove_extract and not errors:
            shutil.rmtree(extract_root, ignore_errors=True)

        if errors:
            NewTeaQuantSetup.print_check_item(
                "fail",
                f"初始化数据导入存在失败项（总耗时 {dt_all:.1f}s）",
            )
            raise RuntimeError(f"部分表导入失败: {errors}")

        NewTeaQuantSetup.print_check_item(
            "done",
            f"初始化数据导入完成（总耗时 {dt_all:.1f}s）",
        )
        # 全部成功后清理断点文件。
        self._clear_progress()
