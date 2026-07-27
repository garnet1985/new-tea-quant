"""TagManager / Tag facade 单元测试。"""

from pathlib import Path
from unittest.mock import MagicMock, patch

from core.modules.tag.core.services.discovery.data.discovered_tag import TagInfo


def _make_tag_info(
    *,
    relative: str = "demo",
    key: str = "demo",
    enabled: bool = True,
    mode: str = "entity_based",
) -> TagInfo:
    return TagInfo(
        unique_relative_path=relative,
        tag_file=Path(f"/tags/{relative}/tag.py"),
        settings_file=Path(f"/tags/{relative}/settings.py"),
        folder=Path(f"/tags/{relative}"),
        key=key,
        display_name=key,
        is_enabled=enabled,
        settings={
            "is_enabled": enabled,
            "meta": {"key": key, "display_name": key},
            "calculation": {
                "execution": {
                    "mode": mode,
                    "start_date": "20200101",
                    "end_date": "20200131",
                },
                "update_mode": "incremental",
            },
            "data": {
                "base": {"data_key": "stock.kline.daily", "params": {}},
                "required": [],
            },
            "tag_definitions": [{"name": "t1"}],
            "tag_target_type": "entity_based",
        },
        hooks_class=MagicMock,
        hooks_module_path="hooks.mod",
        hooks_class_name="Hooks",
        hooks_file_path=Path(f"/tags/{relative}/tag.py"),
    )


class TestTagManager:
    @patch("core.modules.tag.core.tag.DiscoveryService.discover_tags", return_value=[])
    @patch("core.modules.tag.core.tag.DataManager")
    def test_init(self, mock_data_manager, _mock_discover):
        from core.modules.tag.tag_manager import TagManager

        mock_data_mgr = MagicMock()
        mock_tag_service = MagicMock()
        mock_data_mgr.stock.tags = mock_tag_service
        mock_data_manager.return_value = mock_data_mgr

        manager = TagManager(is_verbose=False)

        assert manager.is_verbose is False
        assert manager.data_mgr == mock_data_mgr
        assert manager.tag_data_service == mock_tag_service
        assert manager.scenario_cache == {}

    @patch("core.modules.tag.core.tag.DiscoveryService.discover_tags")
    @patch("core.modules.tag.core.tag.DataManager")
    def test_refresh_scenario(self, mock_data_manager, mock_discover):
        from core.modules.tag.tag_manager import TagManager

        mock_data_manager.return_value = MagicMock(stock=MagicMock(tags=MagicMock()))
        mock_discover.return_value = [_make_tag_info()]

        manager = TagManager(is_verbose=False)
        assert "demo" in manager.scenario_cache

        mock_discover.return_value = []
        manager.refresh_scenario()
        assert manager.scenario_cache == {}

    @patch("core.modules.tag.core.tag.Tag._execute_named")
    @patch("core.modules.tag.core.tag.DiscoveryService.discover_tags", return_value=[])
    @patch("core.modules.tag.core.tag.DataManager")
    def test_execute_with_scenario_name(
        self, mock_data_manager, _mock_discover, mock_execute_named
    ):
        from core.modules.tag.tag_manager import TagManager

        mock_data_manager.return_value = MagicMock(stock=MagicMock(tags=MagicMock()))
        mock_execute_named.return_value = {"ok": 1}

        manager = TagManager(is_verbose=False)
        manager.execute(scenario_name="test_scenario")

        mock_execute_named.assert_called_once()
        assert mock_execute_named.call_args.args[0] == "test_scenario"

    @patch("core.modules.tag.core.tag.Tag._execute_inline_settings")
    @patch("core.modules.tag.core.tag.DiscoveryService.discover_tags", return_value=[])
    @patch("core.modules.tag.core.tag.DataManager")
    def test_execute_with_settings(
        self, mock_data_manager, _mock_discover, mock_inline
    ):
        from core.modules.tag.tag_manager import TagManager

        mock_data_manager.return_value = MagicMock(stock=MagicMock(tags=MagicMock()))
        mock_inline.return_value = {"ok": 1}
        settings = {"is_enabled": True, "meta": {"key": "demo"}}

        manager = TagManager(is_verbose=False)
        manager.execute(scenario_name="demo", settings=settings)

        mock_inline.assert_called_once()
        assert mock_inline.call_args.kwargs["tag_key"] == "demo"
        assert mock_inline.call_args.args[0] == settings

    @patch("core.modules.tag.core.tag.Tag._execute_tag_info")
    @patch("core.modules.tag.core.tag.DiscoveryService.get_enabled_tags")
    @patch("core.modules.tag.core.tag.DiscoveryService.discover_tags")
    @patch("core.modules.tag.core.tag.DataManager")
    def test_execute_all(
        self,
        mock_data_manager,
        mock_discover,
        mock_get_enabled,
        mock_execute_tag_info,
    ):
        from core.modules.tag.tag_manager import TagManager

        mock_data_manager.return_value = MagicMock(stock=MagicMock(tags=MagicMock()))
        t1 = _make_tag_info(relative="a", key="a")
        t2 = _make_tag_info(relative="b", key="b")
        mock_discover.return_value = [t1, t2]
        mock_get_enabled.return_value = [t1, t2]
        mock_execute_tag_info.return_value = {"ok": 1}

        manager = TagManager(is_verbose=False)
        manager.execute()

        assert mock_execute_tag_info.call_count == 2

    @patch("core.modules.tag.core.tag.DiscoveryService.discover_tags", return_value=[])
    @patch("core.modules.tag.core.tag.DataManager")
    def test_scenario_cache_lookup(self, mock_data_manager, mock_discover):
        from core.modules.tag.tag_manager import TagManager

        mock_data_manager.return_value = MagicMock(stock=MagicMock(tags=MagicMock()))
        info = _make_tag_info()
        mock_discover.return_value = [info]

        manager = TagManager(is_verbose=False)
        cached = manager.scenario_cache.get("demo")
        assert cached is not None
        assert cached["key"] == "demo"
        assert cached["settings"]["meta"]["key"] == "demo"

    @patch("core.modules.tag.core.tag.TagEntityPipeline.run")
    @patch("core.modules.tag.core.tag.TagEntityListResolver.resolve")
    @patch("core.modules.tag.core.tag.MetadataEnsureService")
    @patch("core.modules.tag.core.tag.DiscoveryService.discover_tags")
    @patch("core.modules.tag.core.tag.DataManager")
    def test_execute_named_entity_based(
        self,
        mock_data_manager,
        mock_discover,
        mock_ensure_cls,
        mock_resolve,
        mock_pipeline_run,
    ):
        from core.modules.tag.tag_manager import TagManager

        mock_tag_service = MagicMock()
        mock_data_manager.return_value = MagicMock(
            stock=MagicMock(tags=mock_tag_service)
        )
        info = _make_tag_info(mode="entity_based")
        mock_discover.return_value = [info]
        mock_resolve.return_value = ["000001.SZ"]
        mock_pipeline_run.return_value = {
            "success": True,
            "jobs": 1,
            "ok": 1,
            "fail": 0,
            "saved_tag_values": 0,
            "elapsed_seconds": 0.1,
        }
        mock_ensure_cls.return_value.ensure = MagicMock()

        with patch(
            "core.modules.tag.core.tag.Tag._save_performance_report"
        ):
            manager = TagManager(is_verbose=False)
            result = manager.execute(scenario_name="demo")

        assert result["success"] is True
        mock_pipeline_run.assert_called_once()
        assert mock_pipeline_run.call_args.kwargs["entity_ids"] == ["000001.SZ"]

    @patch("core.modules.tag.core.tag.TagEntityPipeline.run")
    @patch("core.modules.tag.core.tag.TagEntityListResolver.resolve")
    @patch("core.modules.tag.core.tag.MetadataEnsureService")
    @patch("core.modules.tag.core.tag.DiscoveryService.discover_tags")
    @patch("core.modules.tag.core.tag.DataManager")
    def test_execute_general_uses_general_owner(
        self,
        mock_data_manager,
        mock_discover,
        mock_ensure_cls,
        mock_resolve,
        mock_pipeline_run,
    ):
        from core.modules.tag.tag_manager import TagManager

        mock_data_manager.return_value = MagicMock(stock=MagicMock(tags=MagicMock()))
        info = _make_tag_info(key="macro_general", relative="macro_general")
        info.settings["tag_target_type"] = "general"
        mock_discover.return_value = [info]
        mock_resolve.return_value = ["__general__"]
        mock_pipeline_run.return_value = {"success": True, "jobs": 1}
        mock_ensure_cls.return_value.ensure = MagicMock()

        with patch(
            "core.modules.tag.core.tag.Tag._save_performance_report"
        ):
            manager = TagManager(is_verbose=False)
            manager.execute(scenario_name="macro_general")

        mock_resolve.assert_called_once()
        assert mock_pipeline_run.call_args.kwargs["entity_ids"] == ["__general__"]
