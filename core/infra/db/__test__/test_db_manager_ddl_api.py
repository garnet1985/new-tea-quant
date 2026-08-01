"""DatabaseManager.create_table / drop_table 委托 engine。"""
from unittest.mock import MagicMock, patch

from core.infra.db import DatabaseManager


def test_create_table_delegates_to_engine():
    config = {
        "database_type": "postgresql",
        "postgresql": {
            "host": "127.0.0.1",
            "port": 5432,
            "user": "u",
            "password": "p",
            "database": "db",
        },
    }
    schema = {"name": "sys_test", "storage_domain": "data", "fields": []}
    with patch("core.infra.db.core.db_manager.create_engine") as mock_create:
        eng = MagicMock()
        mock_create.return_value = eng
        eng.schema_manager = MagicMock()
        db = DatabaseManager(config=config)
        db.initialize()
        db.create_table(schema)
        eng.create_table.assert_called_once_with(schema)


def test_drop_table_delegates_to_engine():
    config = {
        "database_type": "mysql",
        "mysql": {
            "host": "127.0.0.1",
            "port": 3306,
            "user": "u",
            "password": "p",
            "database": "db",
        },
    }
    with patch("core.infra.db.core.db_manager.create_engine") as mock_create:
        eng = MagicMock()
        mock_create.return_value = eng
        eng.schema_manager = MagicMock()
        db = DatabaseManager(config=config)
        db.initialize()
        db.drop_table("sys_test")
        eng.drop_table.assert_called_once_with("sys_test")
