"""DatabaseManager：engine 路径不 eager 构造 ConnectionManager。"""
from unittest.mock import patch

from core.infra.db import DatabaseManager


def test_engine_path_skips_eager_connection_manager():
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
    with patch(
        "core.infra.db.connection_management.connection_manager.ConnectionManager"
    ) as mock_cm_cls:
        db = DatabaseManager(config=config)
        assert db.uses_engine_path
        assert db._connection_manager is None
        mock_cm_cls.assert_not_called()
