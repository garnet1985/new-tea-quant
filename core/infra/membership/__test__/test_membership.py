from pathlib import Path

from core.infra.membership.membership import Membership
from core.infra.project_context.core.path_manager import PathManager


def test_save_read_clear(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(
        PathManager,
        "get_membership_token_file",
        staticmethod(lambda: tmp_path / "membership_token.txt"),
    )

    assert Membership.status()["configured"] is False
    assert Membership.read() is None

    err = Membership.save("not-a-token")
    assert err
    assert Membership.read() is None

    token = "ntq_" + ("ab" * 24)
    assert Membership.save(token) is None
    assert Membership.read() == token
    status = Membership.status()
    assert status["configured"] is True
    assert status["invalid"] is False
    assert status["path"].endswith("membership_token.txt")

    Membership.clear()
    assert Membership.read() is None
    assert Membership.status()["configured"] is False


def test_dropped_file_and_invalid_contents(tmp_path: Path, monkeypatch):
    path = tmp_path / "membership_token.txt"
    monkeypatch.setattr(PathManager, "get_membership_token_file", staticmethod(lambda: path))

    path.write_text("# comment\n\nntq_" + "cd" * 24 + "\n", encoding="utf-8")
    assert Membership.read() == "ntq_" + "cd" * 24

    path.write_text("sk-vendor-key\n", encoding="utf-8")
    status = Membership.status()
    assert status["configured"] is False
    assert status["invalid"] is True
    assert Membership.read() is None
