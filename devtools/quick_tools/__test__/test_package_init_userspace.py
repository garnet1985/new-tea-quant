#!/usr/bin/env python3
import json
from pathlib import Path

from devtools.quick_tools.package_init_userspace import (
    _copy_ignore,
    _is_data_source_handler_csv,
    _is_runtime_path_in_tree,
    _is_user_config_json,
    _sanitize_init_userspace,
    _sync_updater_from_setup,
)


def _write(p: Path, content: str = "x") -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


def test_is_user_config_json():
    assert _is_user_config_json(Path("system/config/database/common.json"))
    assert _is_user_config_json(Path("system/config/data.json"))
    assert not _is_user_config_json(Path("system/config/data.example.json"))
    assert not _is_user_config_json(Path("system/config/database/mysql.example.json"))


def test_sanitize_removes_secrets_and_cache(tmp_path: Path):
    root = tmp_path / "userspace"
    _write(root / ".ntq/duckdb_write_ipc.json", "{}")
    _write(root / "system/.ntq/tmp/a.json")
    _write(root / "system/config/database/mysql.json", '{"user":"u","password":"p"}')
    _write(root / "system/config/database/mysql.example.json", "{}")
    _write(root / "system/config/data.json", "{}")
    _write(root / "extensions/data_source/providers/tushare/auth_token.txt", "secret")
    _write(root / "extensions/data_source/providers/tushare/auth_token.txt.example", "template")
    _write(root / "extensions/data_source/config.py", "TOKEN='x'")
    _write(root / "strategies/demo/results/simulations/price/1/a.csv")
    _write(root / "system/db/data.duckdb", "db")
    _write(root / "extensions/data_source/handlers/adj_factor_event/adj_factor_events_2025Q4.csv", "a,b")
    _write(root / "strategies/demo/strategy_worker.py", "pass")

    notes = _sanitize_init_userspace(root)

    assert not (root / "system/.ntq").exists()
    assert not (root / ".ntq").exists()
    assert not (root / "system/config/database/mysql.json").exists()
    assert (root / "system/config/database/mysql.example.json").is_file()
    assert not (root / "system/config/data.json").exists()
    assert not (root / "extensions/data_source/providers/tushare/auth_token.txt").exists()
    assert (root / "extensions/data_source/providers/tushare/auth_token.txt.example").is_file()
    assert not (root / "extensions/data_source/config.py").exists()
    assert not (root / "strategies/demo/results").exists()
    assert not (
        root / "extensions/data_source/handlers/adj_factor_event/adj_factor_events_2025Q4.csv"
    ).exists()
    assert not (root / "system/db/data.duckdb").exists()
    assert any("auth_token" in n for n in notes)


def test_copy_ignore_skips_ntq_and_strategy_results(tmp_path: Path):
    strategies = tmp_path / "userspace" / "strategies" / "demo"
    strategies.mkdir(parents=True)
    ignored = _copy_ignore(str(strategies), ["results", "settings.py", ".ntq"])
    assert "results" in ignored
    assert ".ntq" in ignored
    assert "settings.py" not in ignored


def test_zip_filter_skips_handler_csv(tmp_path: Path):
    tree = tmp_path / "userspace"
    csv_file = tree / "extensions" / "data_source" / "handlers" / "adj_factor_event" / "x.csv"
    csv_file.parent.mkdir(parents=True)
    csv_file.write_text("a,b", encoding="utf-8")
    assert _is_data_source_handler_csv(tree, csv_file)


def test_copy_ignore_skips_handler_csv(tmp_path: Path):
    handlers = tmp_path / "userspace" / "extensions" / "data_source" / "handlers" / "adj"
    handlers.mkdir(parents=True)
    ignored = _copy_ignore(str(handlers), ["handler.py", "adj_factor_events_2025Q4.csv"])
    assert "adj_factor_events_2025Q4.csv" in ignored
    assert "handler.py" not in ignored


def test_zip_filter_skips_runtime_paths(tmp_path: Path):
    tree = tmp_path / "userspace"
    ntq_file = tree / ".ntq" / "x.json"
    result_file = tree / "strategies" / "demo" / "results" / "a.csv"
    ntq_file.parent.mkdir(parents=True)
    result_file.parent.mkdir(parents=True)
    ntq_file.write_text("{}", encoding="utf-8")
    result_file.write_text("x", encoding="utf-8")
    keeper = tree / "strategies" / "demo" / "settings.py"
    keeper.parent.mkdir(parents=True, exist_ok=True)
    keeper.write_text("x", encoding="utf-8")

    assert _is_runtime_path_in_tree(tree, ntq_file)
    assert _is_runtime_path_in_tree(tree, result_file)
    assert not _is_runtime_path_in_tree(tree, keeper)


def test_write_userspace_meta(tmp_path: Path, monkeypatch):
    from devtools.quick_tools import package_init_userspace as mod

    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "core").mkdir()
    (repo / "core" / "system.json").write_text(
        json.dumps({"version": "0.4.1"}),
        encoding="utf-8",
    )
    init_dir = repo / "setup" / "init_userspace"
    init_dir.mkdir(parents=True)
    zip_path = init_dir / "userspace.zip"
    zip_path.write_bytes(b"fake")

    monkeypatch.setattr(mod, "REPO_ROOT", repo)
    monkeypatch.setattr(mod, "META_PATH", init_dir / "userspace.meta.json")
    monkeypatch.setattr(mod, "ZIP_PATH", zip_path)
    monkeypatch.setattr(mod, "SYSTEM_JSON", repo / "core" / "system.json")

    mod._write_userspace_meta(repo_root=repo, zip_path=zip_path)

    meta = json.loads((init_dir / "userspace.meta.json").read_text(encoding="utf-8"))
    assert meta["core_version"] == "v0.4.1"
    assert meta["fit_version"] == ">= 0.4.1"
    assert meta["zip_file"] == "userspace.zip"
    assert meta["zip_size_bytes"] == 4
    assert meta["source"] == "userspace/"


def test_sync_updater_from_setup(tmp_path: Path, monkeypatch):
    from devtools.quick_tools import package_init_userspace as mod

    updater_src = tmp_path / "setup" / "updater"
    _write(updater_src / "pipeline.py", "# pipeline")
    _write(updater_src / "helper.py", "# helper")
    monkeypatch.setattr(mod, "UPDATER_SRC", updater_src)

    tree = tmp_path / "init" / "userspace"
    tree.mkdir(parents=True)
    notes = _sync_updater_from_setup(tree)

    assert (tree / "system" / "updater" / "pipeline.py").read_text(encoding="utf-8") == "# pipeline"
    assert notes
