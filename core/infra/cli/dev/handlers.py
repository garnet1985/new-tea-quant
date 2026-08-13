"""Dev CLI command implementations."""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path
from typing import Iterable, Sequence

from core.infra.project_context import ProjectContext


class DevHandlers:
    """Dev CLI command implementations."""

    @staticmethod
    def _repo_root() -> Path:
        return ProjectContext.path.get_project_root()

    @staticmethod
    def _perf_cmd_dir() -> Path:
        return (
            ProjectContext.path.get_project_root()
            / "core"
            / "modules"
            / "backtest_engine"
            / "__performance__"
            / "scripts"
            / "cmd"
        )

    @staticmethod
    def _pids_listening_on(port: int) -> list[int]:
        try:
            out = subprocess.run(
                ["lsof", "-ti", f":{port}", "-sTCP:LISTEN"],
                capture_output=True,
                text=True,
                check=False,
            )
        except FileNotFoundError:
            print("需要 lsof（macOS / Linux）", file=sys.stderr)
            return []
        return [int(line) for line in out.stdout.splitlines() if line.strip().isdigit()]

    @staticmethod
    def _process_cmdline(pid: int) -> str:
        try:
            out = subprocess.run(
                ["ps", "-p", str(pid), "-o", "command="],
                capture_output=True,
                text=True,
                check=False,
            )
        except FileNotFoundError:
            return ""
        return (out.stdout or "").strip()

    @staticmethod
    def kill_listeners_on_ports(
        ports: Iterable[int],
        *,
        ntq_only: bool = False,
    ) -> int:
        from core.ui.process_cleanup import kill_process_group

        root = DevHandlers._repo_root()
        fed_root = str((root / "core" / "ui" / "fed").resolve())
        repo_s = str(root)
        ntq_markers = (
            "core.bff.app",
            "react-scripts",
            "webpack",
            "webpack-dev-server",
            "launcher.py",
            "devcli.py",
            fed_root,
            repo_s,
        )
        killed = 0
        for port in ports:
            for attempt in range(2):
                pids = DevHandlers._pids_listening_on(port)
                if not pids:
                    break
                for pid in pids:
                    cmd = DevHandlers._process_cmdline(pid)
                    if ntq_only and cmd and not any(m in cmd for m in ntq_markers):
                        print(f"跳过 pid={pid}（非 NTQ UI）: {cmd[:120]}", flush=True)
                        continue
                    print(f"结束 pid={pid}（:{port}） {cmd[:100]}", flush=True)
                    try:
                        kill_process_group(pid, grace_sec=2.0 if attempt == 0 else 0.5)
                        killed += 1
                    except ProcessLookupError:
                        pass
                deadline = time.time() + 8.0
                while time.time() < deadline and DevHandlers._pids_listening_on(port):
                    time.sleep(0.25)
                if not DevHandlers._pids_listening_on(port):
                    break
        return killed

    @staticmethod
    def cmd_ui_kill(args: argparse.Namespace) -> int:
        from core.ui.ports import ALL_UI_PORTS

        ports = tuple(args.port) if args.port else ALL_UI_PORTS
        n = DevHandlers.kill_listeners_on_ports(ports, ntq_only=args.ntq_only)
        if n == 0:
            print(f"端口 {list(ports)} 上无监听进程。", flush=True)
        return 0

    @staticmethod
    def cmd_version(_args: argparse.Namespace) -> int:
        from core.system import system_meta

        print(f"NTQ Core Version: {system_meta.version}")
        print(f"Release Date: {system_meta.release_date}")
        return 0

    @staticmethod
    def cmd_ui(args: argparse.Namespace) -> int:
        launcher = DevHandlers._repo_root() / "launcher.py"
        if not launcher.is_file():
            print(f"缺少 {launcher}", file=sys.stderr)
            return 1
        if args.kill_first:
            from core.ui.ports import ALL_UI_PORTS

            DevHandlers.kill_listeners_on_ports(ALL_UI_PORTS, ntq_only=False)
        cmd = [sys.executable, str(launcher), "-d", *args.forward]
        print("启动: " + " ".join(cmd), flush=True)
        try:
            return subprocess.run(cmd, cwd=str(DevHandlers._repo_root())).returncode
        except KeyboardInterrupt:
            return 130

    @staticmethod
    def cmd_check_import(args: argparse.Namespace) -> int:
        cmd = [sys.executable, "-m", "core.infra.cli.dev.scripts.minimal_import_check", *args.forward]
        return subprocess.run(cmd, cwd=str(DevHandlers._repo_root())).returncode

    @staticmethod
    def cmd_clear_global_cache(_args: argparse.Namespace) -> int:
        from core.infra.cli.dev.scripts.temp_cleanup import TempCleanup

        TempCleanup.clear_userspace_ntq_dir()
        print("userspace/.ntq 已清理。", flush=True)
        return 0

    @staticmethod
    def cmd_clear_strategy_cache(_args: argparse.Namespace) -> int:
        from core.infra.cli.dev.scripts.temp_cleanup import TempCleanup

        TempCleanup.clear_strategy_results_disk()
        TempCleanup.clear_workbench_db_cache()
        print("物理模拟 results/ 与 DB 工作台快照已清理。", flush=True)
        return 0

    @staticmethod
    def cmd_cache_clear_db(_args: argparse.Namespace) -> int:
        from core.infra.cli.dev.scripts.temp_cleanup import TempCleanup

        TempCleanup.clear_workbench_db_cache()
        print("DB 工作台快照已清理。", flush=True)
        return 0

    @staticmethod
    def cmd_cache_clear_disk(_args: argparse.Namespace) -> int:
        from core.infra.cli.dev.scripts.temp_cleanup import TempCleanup

        TempCleanup.clear_strategy_results_disk()
        print("物理模拟 results/ 已清理。", flush=True)
        return 0

    @staticmethod
    def cmd_data_export_init(args: argparse.Namespace) -> int:
        from core.infra.setup import Setup

        return Setup.artifacts.export_demo_data(list(getattr(args, "forward", None) or []))

    @staticmethod
    def cmd_userspace_package(args: argparse.Namespace) -> int:
        return DevHandlers._package_userspace_with_updater(
            write_zip=not getattr(args, "no_zip", False)
        )

    @staticmethod
    def _package_userspace_with_updater(*, write_zip: bool) -> int:
        from core.infra.project_context import ProjectContext
        from core.infra.updater import Updater
        from core.infra.setup import Setup

        dest = ProjectContext.path.get_updater_directory()
        notes = Updater.runtime.sync_orchestrator(dest)
        for line in notes:
            print(f"  · sync updater → {line}", flush=True)
        return Setup.artifacts.package_userspace(write_zip=write_zip)

    @staticmethod
    def cmd_db_checkpoint(args: argparse.Namespace) -> int:
        from core.infra.db.contracts import DatabaseManager
        from core.infra.project_context import ProjectContext

        recover = bool(getattr(args, "recover_corrupt_wal", False))
        config = None
        if recover:
            config = dict(ProjectContext.config.load_database_config())
            duck = dict(config.get("duckdb") or {})
            duck["recover_wal_on_replay_failure"] = True
            config["duckdb"] = duck
            print(
                "已启用 recover_wal_on_replay_failure：损坏的 .wal 将在打开失败时被删除后重试。",
                flush=True,
            )

        db = DatabaseManager(config=config, is_verbose=True)
        try:
            db.initialize()
        except RuntimeError as exc:
            print(f"无法打开数据库: {exc}", flush=True)
            print(
                "若提示 WAL 回放失败，可确认无 renew 进程后执行:\n"
                "  python devcli.py dbc --recover",
                flush=True,
            )
            return 1

        if recover:
            print(
                "数据库已打开。"
                " 若上方出现「WAL 回放失败…将删除…后重试」，表示已自动丢弃损坏 .wal 并成功重连（非最终失败）。",
                flush=True,
            )

        try:
            if str(db.config.get("database_type", "")).lower() != "duckdb":
                print("当前 database_type 不是 duckdb，跳过。", flush=True)
                return 1
            from core.infra.db import Db

            eng = db.engine
            settings = getattr(eng, "_duckdb_settings", None)
            paths = {}
            if settings is not None:
                paths = {d: cfg.db_path for d, cfg in settings.domains.items()}
            results = db.checkpoint_duckdb()
            print(f"CHECKPOINT 目标: {paths}", flush=True)
            for domain, ok in sorted(results.items()):
                print(f"  {domain}: {'ok' if ok else 'failed'}", flush=True)
            db_dir = None
            if settings is not None:
                for cfg in settings.domains.values():
                    if cfg.db_path:
                        db_dir = Path(Db.duckdb.resolve_db_path(cfg.db_path)).parent
                        break
            remaining = sorted(db_dir.glob("*.duckdb.wal")) if db_dir and db_dir.is_dir() else []
            if remaining:
                print("仍存在的 WAL 文件:", flush=True)
                for p in remaining:
                    print(f"  {p}", flush=True)
            else:
                print("未发现残留 .wal 文件。", flush=True)
            return 0 if results and all(results.values()) else (1 if results else 0)
        finally:
            db.close()

    @staticmethod
    def cmd_sample_stock_pool(args: argparse.Namespace) -> int:
        from core.infra.cli.dev.scripts.sample_stock_list import SampleStockList

        verbose = bool(getattr(args, "verbose", False))
        return SampleStockList.activate(int(args.count), verbose=verbose)

    @staticmethod
    def cmd_pool_clear(_args: argparse.Namespace) -> int:
        from core.infra.cli.dev.scripts.sample_stock_list import SampleStockList

        return SampleStockList.deactivate()

    @staticmethod
    def cmd_pack(args: argparse.Namespace) -> int:
        from core.infra.cli.dev.scripts.publish_prep import PublishPrepOptions, run_publish_prep

        return run_publish_prep(
            PublishPrepOptions(
                version=args.version,
                check_only=args.check_only,
                skip_tests=args.skip_tests,
                skip_ic=args.skip_ic,
                skip_fed_build=args.skip_fed_build,
                skip_py39=args.skip_py39,
                package_userspace=getattr(args, "package_userspace", False),
                skip_dep_check=getattr(args, "skip_dep_check", False),
                skip_icon_check=getattr(args, "skip_icon_check", False),
            )
        )

    @staticmethod
    def cmd_check_deps(args: argparse.Namespace) -> int:
        """依赖风险检测命令（可独立运行）"""
        from core.infra.cli.dev.scripts.dependency_risk import run_dependency_check

        verbose = getattr(args, 'verbose', False)
        return run_dependency_check(verbose=verbose)

    @staticmethod
    def _normalize_be_perf_db(raw: str) -> str:
        key = str(raw or "duckdb").strip().lower()
        if key == "pgsql":
            return "postgresql"
        if key in {"duckdb", "mysql", "postgresql"}:
            return key
        raise SystemExit(f"未知 --db {raw!r}")

    @staticmethod
    def _import_be_perf_cmd():
        cmd_dir = str(DevHandlers._perf_cmd_dir().resolve())
        if cmd_dir not in sys.path:
            sys.path.insert(0, cmd_dir)
        import clean_up as clean_mod
        import db_creation as db_mod
        import run as run_mod

        return db_mod, run_mod, clean_mod

    @staticmethod
    def _be_perf_prepare(db: str, *, mode: str) -> tuple:
        if db not in {"duckdb", "mysql", "postgresql"}:
            print(f"--db {db} 不支持（可选 duckdb / mysql / postgresql）。", flush=True)
            return 2, None
        db_mod, run_mod, _clean_mod = DevHandlers._import_be_perf_cmd()
        label = "entity" if mode == "entity_based" else "slice"
        print(
            f"be_perf_{label}: db={db} mode={mode}\n"
            f"  阶段: [1/2] 注入临时库（{db}）→ [2/2] 分档跑基准（25%/50%/100%）\n"
            "  长时间无输出时看子阶段进度行（[db_creation]/[test]）",
            flush=True,
        )
        print(
            f"[be_perf 1/2] seed {db}（--reuse；数据规模不一致则重建）…",
            flush=True,
        )
        if db == "duckdb":
            db_mod.create_duckdb(reuse=True)
        elif db == "mysql":
            db_mod.create_mysql(reuse=True)
        else:
            db_mod.create_postgresql(reuse=True)
        print(f"[be_perf 2/2] 跑基准策略分档（{mode}）…", flush=True)
        return 0, run_mod

    @staticmethod
    def cmd_be_perf_entity(args: argparse.Namespace) -> int:
        """BE entity_based 性能基准（固定策略 test_strategies/entity_based）。"""
        db = DevHandlers._normalize_be_perf_db(getattr(args, "db", "duckdb"))
        rc, run_mod = DevHandlers._be_perf_prepare(db, mode="entity_based")
        if rc != 0 or run_mod is None:
            return int(rc)
        return int(run_mod.main(["entity_based", "--db", db]))

    @staticmethod
    def cmd_be_perf_slice(args: argparse.Namespace) -> int:
        """BE slice_based 性能基准（固定策略 test_strategies/slice_based）。"""
        db = DevHandlers._normalize_be_perf_db(getattr(args, "db", "duckdb"))
        rc, run_mod = DevHandlers._be_perf_prepare(db, mode="slice_based")
        if rc != 0 or run_mod is None:
            return int(rc)
        return int(run_mod.main(["slice_based", "--db", db]))

    @staticmethod
    def cmd_be_perf_clear(args: argparse.Namespace) -> int:
        """Remove BE __performance__ generated artifacts."""
        _ = args
        _db_mod, _run_mod, clean_mod = DevHandlers._import_be_perf_cmd()
        print("be_perf_clear: cleaning BE __performance__ (--all)", flush=True)
        return int(clean_mod.main(["--all"]))

    @staticmethod
    def normalize_forward(rest: Sequence[str]) -> list[str]:
        rest = list(rest)
        if rest[:1] == ["--"]:
            return rest[1:]
        return rest

