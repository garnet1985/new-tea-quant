"""VersionMetaStore：根 registry 与 {vid}/ 身份归档。"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.modules.strategy.core.enums import SimulateKind
from core.modules.strategy.core.services.artifacts.consts import (
    EFFECTIVE_SETTINGS_FILE,
    RUNTIME_ENV_FILE,
    SCOPE_FILE,
    SETTINGS_FILE,
)
from core.modules.strategy.core.services.artifacts.version_meta import VersionMetaStore

pytestmark = pytest.mark.force_run


def test_registry_flat_fingerprints(tmp_path: Path) -> None:
    root = tmp_path / "simulations"
    VersionMetaStore.register_version(
        root, "2", execute_fp="sfp", env_fp="efp"
    )
    entry = VersionMetaStore.get_registry_entry(root, "2")
    assert entry is not None
    assert entry["execute_fp"] == "sfp"
    assert entry["env_fp"] == "efp"
    assert "fingerprints" not in entry
    meta = VersionMetaStore.read_root_meta(root)
    assert "fingerprint_index" not in meta


def test_find_version_by_fingerprints_scans_registry(tmp_path: Path) -> None:
    root = tmp_path / "simulations"
    VersionMetaStore.write_root_meta(
        root,
        {
            "next_version_id": 3,
            "registry": {
                "2": {
                    "created_at": "t",
                    "execute_fp": "sfp",
                    "env_fp": "efp",
                }
            },
        },
    )
    assert (
        VersionMetaStore.find_version_by_fingerprints(root, "sfp", "efp") == "2"
    )


def test_find_version_by_fingerprints_returns_newest_duplicate(tmp_path: Path) -> None:
    """旧 force 可能留下同指纹多号；复写必须命中最新号，不能写回更早的 v4。"""
    root = tmp_path / "simulations"
    VersionMetaStore.register_version(root, "4", execute_fp="sfp", env_fp="efp")
    VersionMetaStore.register_version(root, "6", execute_fp="sfp", env_fp="efp")
    assert (
        VersionMetaStore.find_version_by_fingerprints(root, "sfp", "efp") == "6"
    )


def test_vid_and_fingerprint_lookup_are_equivalent(tmp_path: Path) -> None:
    root = tmp_path / "simulations"
    VersionMetaStore.register_version(
        root, "5", execute_fp="aa", env_fp="bb"
    )
    by_fp = VersionMetaStore.find_version_by_fingerprints(root, "aa", "bb")
    by_vid = VersionMetaStore.get_registry_entry(root, "5")
    assert by_fp == "5"
    assert by_vid is not None
    assert by_vid["execute_fp"] == "aa"
    assert by_vid["env_fp"] == "bb"


def test_effective_settings_lives_under_vid(tmp_path: Path) -> None:
    root = tmp_path / "simulations"
    VersionMetaStore.write_effective_settings(
        root,
        "1",
        {"core": {"n": 1}, "entity_ids": ["000001.SZ"]},
    )
    path = root / "1" / EFFECTIVE_SETTINGS_FILE
    assert path.is_file()
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["core"] == {"n": 1}
    assert "entity_ids" not in payload


def test_write_version_archive_splits_settings_and_scope(tmp_path: Path) -> None:
    root = tmp_path / "simulations"
    VersionMetaStore.register_version(root, "2", execute_fp="sfp", env_fp="efp")
    VersionMetaStore.write_version_archive(
        root,
        "2",
        full_settings={"meta": {"key": "demo"}, "core": {"n": 1}, "analysis": {"enabled": True}},
        effective_settings={"core": {"n": 1}},
        entity_ids=["000002.SZ", "000001.SZ"],
        start_date="20240102",
        end_date="20240110",
    )
    VersionMetaStore.mark_step_complete(root, "2", SimulateKind.ENUMERATE)

    settings = json.loads((root / "2" / SETTINGS_FILE).read_text(encoding="utf-8"))
    effective = json.loads((root / "2" / EFFECTIVE_SETTINGS_FILE).read_text(encoding="utf-8"))
    scope = json.loads((root / "2" / SCOPE_FILE).read_text(encoding="utf-8"))
    assert settings["analysis"]["enabled"] is True
    assert effective == {"core": {"n": 1}}
    assert scope == {
        "entity_ids": ["000001.SZ", "000002.SZ"],
        "start_date": "20240102",
        "end_date": "20240110",
    }

    archive = VersionMetaStore.read_archive_context(root, "2")
    assert archive["execute_fp"] == "sfp"
    assert archive["entity_ids"] == ["000001.SZ", "000002.SZ"]
    assert archive["effective_settings"] == {"core": {"n": 1}}

    entry = VersionMetaStore.get_registry_entry(root, "2")
    assert entry is not None
    assert entry["steps"]["enumerate"] == "ok"


def test_write_version_archive_is_write_once(tmp_path: Path) -> None:
    root = tmp_path / "simulations"
    VersionMetaStore.write_version_archive(
        root,
        "3",
        full_settings={"core": {"n": 1}},
        effective_settings={"core": {"n": 1}},
        entity_ids=["000001.SZ"],
        start_date="20240102",
        end_date="20240110",
    )
    VersionMetaStore.write_version_archive(
        root,
        "3",
        full_settings={"core": {"n": 99}},
        effective_settings={"core": {"n": 99}},
        entity_ids=["000002.SZ"],
        start_date="20250101",
        end_date="20250102",
    )
    settings = json.loads((root / "3" / SETTINGS_FILE).read_text(encoding="utf-8"))
    scope = json.loads((root / "3" / SCOPE_FILE).read_text(encoding="utf-8"))
    assert settings["core"]["n"] == 1
    assert scope["entity_ids"] == ["000001.SZ"]
    assert scope["start_date"] == "20240102"


def test_step_status_from_disk(tmp_path: Path) -> None:
    root = tmp_path / "simulations"
    enum_dir = root / "1" / "enum"
    enum_dir.mkdir(parents=True)
    (enum_dir / RUNTIME_ENV_FILE).write_text("{}", encoding="utf-8")
    assert (
        VersionMetaStore.step_status(root, "1", SimulateKind.ENUMERATE) == "ok"
    )


def test_clear_downstream_steps_deletes_price_and_portfolio(tmp_path: Path) -> None:
    root = tmp_path / "simulations"
    VersionMetaStore.register_version(root, "6", execute_fp="sfp", env_fp="efp")
    for step, kind in (
        ("enum", SimulateKind.ENUMERATE),
        ("price", SimulateKind.PRICE_FACTOR),
        ("portfolio", SimulateKind.PORTFOLIO),
    ):
        step_dir = root / "6" / step
        step_dir.mkdir(parents=True)
        (step_dir / RUNTIME_ENV_FILE).write_text("{}", encoding="utf-8")
        VersionMetaStore.mark_step_complete(root, "6", kind)

    VersionMetaStore.clear_downstream_steps(root, "6", SimulateKind.ENUMERATE)

    assert (root / "6" / "enum" / RUNTIME_ENV_FILE).is_file()
    assert not (root / "6" / "price").exists()
    assert not (root / "6" / "portfolio").exists()
    entry = VersionMetaStore.get_registry_entry(root, "6")
    assert entry is not None
    assert entry["steps"] == {"enumerate": "ok"}
    assert VersionMetaStore.step_status(root, "6", SimulateKind.PRICE_FACTOR) == "missing"
    assert VersionMetaStore.step_status(root, "6", SimulateKind.PORTFOLIO) == "missing"


def test_prune_syncs_registry(tmp_path: Path) -> None:
    root = tmp_path / "simulations"
    (root / "1").mkdir(parents=True)
    VersionMetaStore.register_version(root, "1", execute_fp="s", env_fp="e")
    VersionMetaStore.remove_version_from_registry(root, "1")
    assert VersionMetaStore.get_registry_entry(root, "1") is None


def test_is_env_invalid_when_fingerprints_differ(tmp_path: Path) -> None:
    entry = {"env_fp": "old-env"}
    assert VersionMetaStore.is_env_invalid(entry, "new-env") is True
    assert VersionMetaStore.is_env_invalid(entry, "old-env") is False
    assert VersionMetaStore.is_env_invalid(entry, "") is False


def test_find_version_by_execute_fp(tmp_path: Path) -> None:
    root = tmp_path / "simulations"
    VersionMetaStore.register_version(root, "2", execute_fp="sfp", env_fp="efp-old")
    assert VersionMetaStore.find_version_by_execute_fp(root, "sfp") == "2"
    assert VersionMetaStore.find_version_by_execute_fp(root, "other") is None


def test_pinned_is_root_meta_not_registry(tmp_path: Path) -> None:
    root = tmp_path / "simulations"
    (root / "2").mkdir(parents=True)
    (root / "3").mkdir(parents=True)
    VersionMetaStore.register_version(root, "2", execute_fp="s", env_fp="e")
    VersionMetaStore.register_version(root, "3", execute_fp="s", env_fp="e")
    assert VersionMetaStore.read_pinned_ids(root) == []
    ids = VersionMetaStore.set_version_pinned(root, "2", True)
    assert ids == ["2"]
    meta = VersionMetaStore.read_root_meta(root)
    assert meta["pinned"] == ["2"]
    assert "pinned" not in (VersionMetaStore.get_registry_entry(root, "2") or {})
    VersionMetaStore.set_version_pinned(root, "3", True)
    assert VersionMetaStore.read_pinned_ids(root) == ["2", "3"]
    VersionMetaStore.set_version_pinned(root, "2", False)
    assert VersionMetaStore.read_pinned_ids(root) == ["3"]
    VersionMetaStore.remove_version_from_registry(root, "3")
    assert VersionMetaStore.read_pinned_ids(root) == []
    assert VersionMetaStore.read_root_meta(root).get("pinned") == []
    VersionMetaStore.register_version(root, "2", execute_fp="s", env_fp="e")
    VersionMetaStore.set_version_pinned(root, "v2", True)
    assert VersionMetaStore.read_pinned_ids(root) == ["2"]
    assert VersionMetaStore.set_version_pinned(root, "2", True) == ["2"]
    VersionMetaStore.write_root_meta(
        root,
        {**VersionMetaStore.read_root_meta(root), "pinned": ["2", "99"]},
    )
    assert VersionMetaStore.read_pinned_ids(root) == ["2"]

