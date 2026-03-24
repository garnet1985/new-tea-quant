"""
Demo 数据安装流程（orchestration）。

产品约定（0.x，API 不保证兼容，暂不做包版本校验）：

- 目录：userspace/demo_data（见 default_demo_data_dir）。
- 官网提供 3 个 zip（两大表 + 其余小表）；用户全部放入该目录。处理步骤：将该目录下
  所有 .zip 解压到专用临时目录，再扫描解压产物并按表 import；**import 成功结束后删除该
  临时目录**（解压产物不保留）。用户放置的 .zip 可保留不动。
- 内容：无状态业务数据；不含缓存等（如 sys_cache / sys_meta_info 不在 demo 包内）。
- install.sh 中本步可跳过；执行前必须向用户展示「写入哪些目标表、如何写入（先 DELETE 再 INSERT）」，
  并在一次确认后开始逐表导入；交互式下输入 YES 即含「非空表则覆盖」的同意；非交互用 --confirm / --yes。
- 安装方式唯一：目标表 DELETE 再 INSERT（与 backup 脚本的多种 mode 无关，实现保持简单）。
- 某表导入失败：不做整库回滚；至多清空该表或保持失败时状态（实现择一即可）。
- 面向用户的流程走 install；开发者调试可另加 CLI，无硬性规范。
"""
from __future__ import annotations

import logging
import shutil
import sys
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.infra.db.helpers.db_helpers import DBHelper
from core.infra.project_context.path_manager import PathManager

from .archives import collect_table_archives

logger = logging.getLogger(__name__)

DEFAULT_DEMO_SUBDIR = "demo_data"
# 解压产物目录（相对 data_dir）；import 成功后整目录删除
EXTRACT_SUBDIR = "_extract"
DEFAULT_TABLE_PREFIX = "test_"


def default_demo_data_dir() -> Path:
    """userspace/demo_data（受 NTQ_USERSPACE_ROOT 等影响，与 PathManager 一致）。"""
    return PathManager.userspace() / DEFAULT_DEMO_SUBDIR


def format_demo_install_plan_text(
    rows: List[Dict[str, Any]],
    *,
    data_dir: Path,
    table_prefix: str,
) -> str:
    """
    供打印或日志使用：说明将向哪些表、如何写入数据（不含执行导入）。
    """
    lines = [
        "",
        "=" * 72,
        "Demo 数据安装 — 执行前请确认",
        "=" * 72,
        "",
        "操作方式（每张将导入的表均相同）：",
        "  1) 若不存在：按「源表」结构创建「目标表」（仅结构，无数据）。",
        "  2) 对「目标表」执行 DELETE，清空已有行。",
        "  3) 将解压归档中的 CSV 行 INSERT 进「目标表」。",
        "",
        "不会修改与 Demo 包同名的无前缀生产表；数据只写入带前缀的目标表。",
        "",
        f"数据目录: {data_dir}",
        f"目标表前缀: {table_prefix!r}",
        "",
        f"{'逻辑表名':<28} {'目标表名':<30} {'SQL 中写入的表名':<42} {'当前行数':>8}  归档",
        "-" * 120,
    ]
    for r in rows:
        if not r.get("will_import"):
            lines.append(
                f"{r['logical']:<28} {'—':<30} {'(跳过：未注册 model)':<42} {'—':>8}  —"
            )
            continue
        arch = r.get("archive_basename_summary", "-")
        qual = r.get("qualified") or r["target"]
        lines.append(
            f"{r['logical']:<28} {r['target']:<30} {qual:<42} {r['existing_rows']!s:>8}  {arch}"
        )
    lines.extend(
        [
            "-" * 120,
            "",
            "若「当前行数」> 0：安装将先清空该目标表再写入 Demo。",
            "交互式：随后会提示输入 YES 一次即表示同意计划（含覆盖已有数据）。",
            "非交互：需使用 --confirm，若存在非空目标表还需 --yes。",
            "",
            "=" * 72,
            "",
        ]
    )
    return "\n".join(lines)


def _bare_table_name_for_exists_check(qualified_table: str) -> str:
    """information_schema / adapter.is_table_exists 使用的裸表名（无 schema 前缀）。"""
    s = qualified_table.strip().strip('"')
    if "." in s:
        return s.rsplit(".", 1)[-1].strip('"')
    return s


def _count_rows_in_table(db, qualified_table: str) -> int:
    """
    目标表尚不存在时返回 0，且不对其发 COUNT（避免适配器对「表不存在」打 ERROR 日志）。
    """
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


class DemoDataInstaller:
    """
    Demo 安装：解压 zip → 按表归档 import_data → 默认写入带前缀的目标表（不碰原表）。
    """

    def __init__(
        self,
        data_dir: Optional[Path] = None,
        *,
        table_prefix: str = DEFAULT_TABLE_PREFIX,
    ) -> None:
        self.data_dir = Path(data_dir) if data_dir is not None else default_demo_data_dir()
        self.table_prefix = table_prefix.rstrip("_") + "_" if table_prefix else ""

    def _extract_zips(self, extract_root: Path) -> List[Path]:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        zips = sorted(self.data_dir.glob("*.zip"))
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
            logger.info("已解压: %s -> %s", z.name, dest)
        return zips

    def _build_plan_rows(self, dm, plan: dict) -> List[Dict[str, Any]]:
        """每张表一行：逻辑名、目标名、当前行数、是否将导入、归档摘要。"""
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

    @staticmethod
    def _require_install_confirmation(
        confirmed: bool,
        *,
        has_nonempty_targets: bool,
        nonempty_rows: List[Dict[str, Any]],
    ) -> None:
        """
        展示计划之后、开始逐表 import 之前调用一次。

        - 交互终端：输入 YES 即确认计划；若 has_nonempty_targets，该 YES 同时表示同意覆盖已有数据。
        - 非交互：须 confirmed=True（非交互且存在非空表时需在 run() 入口已要求 --yes）。
        """
        if confirmed:
            return

        interactive = sys.stdin.isatty() and sys.stdout.isatty()
        if interactive:
            print("", flush=True)
            if has_nonempty_targets:
                print(
                    "——————————————————————————————————————————————————————————————————————",
                    "以下目标表内已有数据，导入前将执行 DELETE 再 INSERT：",
                    flush=True,
                )
                for r in nonempty_rows:
                    print(
                        f"  - {r['target']}: 当前 {r['existing_rows']} 行",
                        flush=True,
                    )
                print(
                    "输入大写 YES 表示：确认上述安装计划，并同意清空这些表中的已有数据后写入 Demo。",
                    flush=True,
                )
            else:
                print(
                    "输入大写 YES 以确认按上述计划安装 Demo 数据。",
                    flush=True,
                )
            print("——————————————————————————————————————————————————————————————————————", flush=True)
            try:
                line = input("> ")
            except EOFError:
                print("已取消（无输入）。", file=sys.stderr)
                sys.exit(1)
            if line.strip() != "YES":
                print("已取消（须输入大写 YES）。", file=sys.stderr)
                sys.exit(1)
            return

        print(
            "错误: 非交互模式须传入 --confirm（表示已阅读计划并同意执行）。",
            file=sys.stderr,
        )
        sys.exit(2)

    def run(
        self,
        *,
        confirmed: bool = False,
        confirm_nonempty: bool = False,
        remove_extract: bool = True,
    ) -> None:
        from core.modules.data_manager import DataManager

        data_dir = self.data_dir
        extract_root = data_dir / EXTRACT_SUBDIR

        if not data_dir.is_dir():
            raise FileNotFoundError(f"Demo 数据目录不存在: {data_dir}")

        self._extract_zips(extract_root)

        plan = collect_table_archives(extract_root)
        if not plan:
            raise RuntimeError(
                f"解压后未找到任何 .tar.gz/.zip 数据归档，请检查 zip 内容: {extract_root}"
            )

        dm = DataManager(is_verbose=False)
        dm.initialize()
        db = dm.db
        if not db:
            raise RuntimeError("数据库不可用")

        rows = self._build_plan_rows(dm, plan)
        plan_text = format_demo_install_plan_text(
            rows,
            data_dir=data_dir,
            table_prefix=self.table_prefix,
        )
        print(plan_text, flush=True)

        if not any(r["will_import"] for r in rows):
            raise RuntimeError(
                "没有可导入的表（均在框架中未注册 model）。请检查表名与 core/tables 是否一致。"
            )

        nonempty = [r for r in rows if r["will_import"] and r["existing_rows"] > 0]
        has_nonempty = bool(nonempty)

        interactive = sys.stdin.isatty() and sys.stdout.isatty()
        # 非交互且存在非空目标表且未传 --yes：直接退出（无 traceback）
        if not interactive and has_nonempty and not confirm_nonempty:
            print(
                "错误: 目标表中已有数据。非交互请使用: "
                "python -m setup.demo_data_handler --yes --confirm",
                file=sys.stderr,
            )
            sys.exit(2)

        self._require_install_confirmation(
            confirmed,
            has_nonempty_targets=has_nonempty,
            nonempty_rows=nonempty,
        )

        errors: List[Tuple[str, str]] = []
        for r in rows:
            if not r["will_import"]:
                logger.warning("跳过未注册的表（无 model）: %s", r["logical"])
                continue
            logical = r["logical"]
            paths = r["archives"]
            target = r["target"]
            model = dm.get_table(logical)
            assert model is not None
            try:
                model.import_data(paths, target_table=target)
            except Exception as e:
                logger.exception("导入失败: %s -> %s", logical, target)
                errors.append((logical, str(e)))

        if remove_extract and not errors:
            shutil.rmtree(extract_root, ignore_errors=True)
            logger.info("已删除临时解压目录: %s", extract_root)
        elif errors:
            logger.warning("存在失败项，保留解压目录便于排查: %s", extract_root)

        if errors:
            raise RuntimeError(f"部分表导入失败: {errors}")
