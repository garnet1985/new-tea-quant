"""VersionMetaStore：根 registry 与 {vid}/effective_settings.json。"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.modules.strategy.core.enums import SimulateKind
from core.modules.strategy.core.services.artifacts.consts import (
    EFFECTIVE_SETTINGS_FILE,
    RUNTIME_ENV_FILE,
)
from core.modules.strategy.core.services.artifacts.version_meta import VersionMetaStore

pytestmark = pytest.mark.force_run


def test_registry_flat_fingerprints(tmp_path: Path) -> None:
    root = tmp_path / "simulations"
    VersionMetaStore.register_version(
        root, "2", settings_fp="sfp", env_fp="efp"
    )
    entry = VersionMetaStore.get_registry_entry(root, "2")
    assert entry is not None
    assert entry["settings_fp"] == "sfp"
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
                    "settings_fp": "sfp",
                    "env_fp": "efp",
                }
            },
        },
    )
    assert (
        VersionMetaStore.find_version_by_fingerprints(root, "sfp", "efp") == "2"
    )


def test_vid_and_fingerprint_lookup_are_equivalent(tmp_path: Path) -> None:
    root = tmp_path / "simulations"
    VersionMetaStore.register_version(
        root, "5", settings_fp="aa", env_fp="bb"
    )
    by_fp = VersionMetaStore.find_version_by_fingerprints(root, "aa", "bb")
    by_vid = VersionMetaStore.get_registry_entry(root, "5")
    assert by_fp == "5"
    assert by_vid is not None
    assert by_vid["settings_fp"] == "aa"
    assert by_vid["env_fp"] == "bb"


def test_effective_settings_lives_under_vid(tmp_path: Path) -> None:
    root = tmp_path / "simulations"
    VersionMetaStore.write_effective_settings(
        root,
        "1",
        settings={"core": {"n": 1}},
        entity_ids=["000001.SZ"],
    )
    path = root / "1" / EFFECTIVE_SETTINGS_FILE
    assert path.is_file()
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["core"] == {"n": 1}
    assert payload["entity_ids"] == ["000001.SZ"]


def test_step_status_from_disk(tmp_path: Path) -> None:
    root = tmp_path / "simulations"
    enum_dir = root / "1" / "enum"
    enum_dir.mkdir(parents=True)
    (enum_dir / RUNTIME_ENV_FILE).write_text("{}", encoding="utf-8")
    assert (
        VersionMetaStore.step_status(root, "1", SimulateKind.ENUMERATE) == "ok"
    )


def test_prune_syncs_registry(tmp_path: Path) -> None:
    root = tmp_path / "simulations"
    (root / "1").mkdir(parents=True)
    VersionMetaStore.register_version(root, "1", settings_fp="s", env_fp="e")
    VersionMetaStore.remove_version_from_registry(root, "1")
    assert VersionMetaStore.get_registry_entry(root, "1") is None


def test_is_env_invalid_when_fingerprints_differ(tmp_path: Path) -> None:
    entry = {"env_fp": "old-env"}
    assert VersionMetaStore.is_env_invalid(entry, "new-env") is True
    assert VersionMetaStore.is_env_invalid(entry, "old-env") is False
    assert VersionMetaStore.is_env_invalid(entry, "") is False


def test_find_version_by_settings_fp(tmp_path: Path) -> None:
    root = tmp_path / "simulations"
    VersionMetaStore.register_version(root, "2", settings_fp="sfp", env_fp="efp-old")
    assert VersionMetaStore.find_version_by_settings_fp(root, "sfp") == "2"
    assert VersionMetaStore.find_version_by_settings_fp(root, "other") is None

