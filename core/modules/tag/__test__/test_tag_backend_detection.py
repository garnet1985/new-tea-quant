from __future__ import annotations

from unittest.mock import MagicMock, patch

from core.modules.tag.tag_manager import TagManager


def test_configured_database_type_when_db_suspended():
    data_mgr = MagicMock()
    data_mgr.db = None
    with patch(
        "core.infra.project_context.ConfigManager.load_database_config",
        return_value={"database_type": "duckdb"},
    ):
        assert TagManager._configured_database_type(data_mgr) == "duckdb"
        assert TagManager._backend_is_duckdb(data_mgr) is True


def test_configured_database_type_prefers_live_db():
    data_mgr = MagicMock()
    data_mgr.db = MagicMock()
    data_mgr.db.config = {"database_type": "mysql"}
    assert TagManager._configured_database_type(data_mgr) == "mysql"
    assert TagManager._backend_is_duckdb(data_mgr) is False
