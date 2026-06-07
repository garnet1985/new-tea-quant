"""DataManager 并发构造时只 initialize 一次 DatabaseManager。"""
from __future__ import annotations

import threading
from unittest.mock import MagicMock, patch

from core.infra.db import DatabaseManager
from core.modules.data_manager.data_manager import DataManager


def test_concurrent_data_manager_construct_initializes_db_once():
    DataManager.reset_instance()
    init_count = {"n": 0}
    barrier = threading.Barrier(8)

    def counting_initialize(self):
        init_count["n"] += 1

    errors: list[BaseException] = []

    def worker():
        try:
            barrier.wait(timeout=5)
            DataManager()
        except BaseException as exc:
            errors.append(exc)

    with patch.object(DatabaseManager, "__init__", return_value=None):
        with patch.object(
            DatabaseManager, "initialize", autospec=True, side_effect=counting_initialize
        ):
            with patch.object(DatabaseManager, "set_default"):
                with patch.object(DatabaseManager, "create_all_base_tables"):
                    with patch.object(DataManager, "_discover_tables"):
                        with patch(
                            "core.modules.data_manager.data_services.DataService"
                        ) as ds_cls:
                            ds_cls.return_value.index.sync_list_from_config = MagicMock()
                            threads = [threading.Thread(target=worker) for _ in range(8)]
                            for t in threads:
                                t.start()
                            for t in threads:
                                t.join(timeout=30)

    assert not errors
    assert init_count["n"] == 1
    DataManager.reset_instance()
