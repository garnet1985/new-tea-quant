"""Installation id: memory / staging first, then userspace."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.infra.trace.core.services.identity_service import TraceIdentityService

pytestmark = pytest.mark.force_run


@pytest.fixture()
def identity_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    TraceIdentityService.reset_cache()
    staging = tmp_path / "repo" / ".ntq" / "trace" / "installation_id"
    userspace_root = tmp_path / "userspace"

    def _staging() -> Path:
        staging.parent.mkdir(parents=True, exist_ok=True)
        return staging

    def _userspace() -> Path | None:
        if not userspace_root.is_dir():
            return None
        root = userspace_root / ".ntq" / "trace"
        root.mkdir(parents=True, exist_ok=True)
        return root / "installation_id"

    monkeypatch.setattr(TraceIdentityService, "_staging_path", staticmethod(_staging))
    monkeypatch.setattr(TraceIdentityService, "_userspace_path", staticmethod(_userspace))
    yield staging, userspace_root
    TraceIdentityService.reset_cache()


def test_creates_staging_before_userspace(identity_paths) -> None:
    staging, userspace_root = identity_paths
    install_id = TraceIdentityService.get_or_create()
    assert install_id is not None
    assert install_id.startswith("ntq_i_")
    assert staging.read_text(encoding="utf-8").strip() == install_id
    assert not userspace_root.exists()


def test_memory_id_written_when_userspace_appears(identity_paths) -> None:
    staging, userspace_root = identity_paths
    first = TraceIdentityService.get_or_create()
    userspace_root.mkdir()
    second = TraceIdentityService.get_or_create()
    assert second == first
    dest = userspace_root / ".ntq" / "trace" / "installation_id"
    assert dest.read_text(encoding="utf-8").strip() == first
    assert staging.read_text(encoding="utf-8").strip() == first


def test_staging_survives_process_until_userspace(identity_paths) -> None:
    staging, userspace_root = identity_paths
    first = TraceIdentityService.get_or_create()
    userspace_root.mkdir()
    TraceIdentityService.reset_cache()
    second = TraceIdentityService.get_or_create()
    assert second == first
    dest = userspace_root / ".ntq" / "trace" / "installation_id"
    assert dest.read_text(encoding="utf-8").strip() == first


def test_existing_userspace_id_wins(identity_paths) -> None:
    staging, userspace_root = identity_paths
    userspace_root.mkdir()
    dest = userspace_root / ".ntq" / "trace"
    dest.mkdir(parents=True)
    kept = "ntq_i_" + "b" * 32
    (dest / "installation_id").write_text(kept + "\n", encoding="utf-8")
    staging.parent.mkdir(parents=True, exist_ok=True)
    staging.write_text("ntq_i_" + "a" * 32 + "\n", encoding="utf-8")
    got = TraceIdentityService.get_or_create()
    assert got == kept
    assert staging.read_text(encoding="utf-8").strip() == kept
