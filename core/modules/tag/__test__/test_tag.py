"""Tag facade 单元测试。"""

from pathlib import Path
from unittest.mock import MagicMock, patch

from core.modules.tag.core.services.discovery.data.discovered_tag import DiscoveredTagInfo


def _make_tag_info(
    *,
    relative: str = "demo",
    key: str = "demo",
    enabled: bool = True,
    mode: str = "entity_based",
) -> DiscoveredTagInfo:
    return DiscoveredTagInfo(
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
        },
        hooks_class=MagicMock,
        hooks_module_path="hooks.mod",
        hooks_class_name="Hooks",
        hooks_file_path=Path(f"/tags/{relative}/tag.py"),
    )


class TestTag:
    @patch("core.modules.tag.tag.DiscoveryService.discover_tags", return_value=[])
    @patch("core.modules.tag.tag.DataManager")
    def test_init(self, mock_data_manager, _mock_discover):
        from core.modules.tag import Tag

        mock_data_mgr = MagicMock()
        mock_tag_service = MagicMock()
        mock_data_mgr.stock.tags = mock_tag_service
        mock_data_manager.return_value = mock_data_mgr

        tag = Tag(is_verbose=False)

        assert tag.is_verbose is False
        assert tag.data_mgr == mock_data_mgr
        assert tag.tag_data_service == mock_tag_service
        assert tag.list_ids(enabled_only=False) == []

    @patch("core.modules.tag.tag.DiscoveryService.discover_tags")
    @patch("core.modules.tag.tag.DataManager")
    def test_refresh_and_list(self, mock_data_manager, mock_discover):
        from core.modules.tag import Tag

        mock_data_manager.return_value = MagicMock(stock=MagicMock(tags=MagicMock()))
        mock_discover.return_value = [_make_tag_info()]

        tag = Tag(is_verbose=False)
        assert tag.list_ids() == ["demo"]
        assert tag.find("demo") is not None

        mock_discover.return_value = []
        tag.refresh()
        assert tag.list_ids(enabled_only=False) == []

    @patch("core.modules.tag.tag.Tag._execute_named")
    @patch("core.modules.tag.tag.DiscoveryService.discover_tags", return_value=[])
    @patch("core.modules.tag.tag.DataManager")
    def test_execute_with_scenario_name(
        self, mock_data_manager, _mock_discover, mock_execute_named
    ):
        from core.modules.tag import Tag

        mock_data_manager.return_value = MagicMock(stock=MagicMock(tags=MagicMock()))
        mock_execute_named.return_value = {"ok": 1}

        tag = Tag(is_verbose=False)
        tag.execute(scenario_name="test_scenario")

        mock_execute_named.assert_called_once()
        assert mock_execute_named.call_args.args[0] == "test_scenario"

    @patch("core.modules.tag.tag.Tag._execute_inline_settings")
    @patch("core.modules.tag.tag.DiscoveryService.discover_tags", return_value=[])
    @patch("core.modules.tag.tag.DataManager")
    def test_execute_with_settings(
        self, mock_data_manager, _mock_discover, mock_inline
    ):
        from core.modules.tag import Tag

        mock_data_manager.return_value = MagicMock(stock=MagicMock(tags=MagicMock()))
        mock_inline.return_value = {"ok": 1}
        settings = {"is_enabled": True, "meta": {"key": "demo"}}

        tag = Tag(is_verbose=False)
        tag.execute(scenario_name="demo", settings=settings)

        mock_inline.assert_called_once()
        assert mock_inline.call_args.kwargs["tag_key"] == "demo"
        assert mock_inline.call_args.args[0] == settings

    @patch("core.modules.tag.tag.Tag._execute_tag_info")
    @patch("core.modules.tag.tag.DiscoveryService.get_enabled_tags")
    @patch("core.modules.tag.tag.DiscoveryService.discover_tags")
    @patch("core.modules.tag.tag.DataManager")
    def test_execute_all(
        self,
        mock_data_manager,
        mock_discover,
        mock_get_enabled,
        mock_execute_tag_info,
    ):
        from core.modules.tag import Tag

        mock_data_manager.return_value = MagicMock(stock=MagicMock(tags=MagicMock()))
        t1 = _make_tag_info(relative="a", key="a")
        t2 = _make_tag_info(relative="b", key="b")
        mock_discover.return_value = [t1, t2]
        mock_get_enabled.return_value = [t1, t2]
        mock_execute_tag_info.return_value = {"ok": 1}

        tag = Tag(is_verbose=False)
        tag.execute()

        assert mock_execute_tag_info.call_count == 2

    @patch("core.modules.tag.tag.TagEntityPipeline.run")
    @patch("core.modules.tag.tag.TagEntityListResolver.resolve")
    @patch("core.modules.tag.tag.MetadataEnsureService")
    @patch("core.modules.tag.tag.DiscoveryService.discover_tags")
    @patch("core.modules.tag.tag.DataManager")
    def test_execute_named_entity_based(
        self,
        mock_data_manager,
        mock_discover,
        mock_ensure_cls,
        mock_resolve,
        mock_pipeline_run,
    ):
        from core.modules.tag import Tag

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

        with patch("core.modules.tag.tag.Tag._save_performance_report"):
            tag = Tag(is_verbose=False)
            result = tag.execute(scenario_name="demo")

        assert result["success"] is True
        mock_pipeline_run.assert_called_once()
        assert mock_pipeline_run.call_args.kwargs["entity_ids"] == ["000001.SZ"]

    @patch("core.modules.tag.tag.TagGlobalPipeline.run")
    @patch("core.modules.tag.tag.TagEntityListResolver.resolve")
    @patch("core.modules.tag.tag.MetadataEnsureService")
    @patch("core.modules.tag.tag.DiscoveryService.discover_tags")
    @patch("core.modules.tag.tag.DataManager")
    def test_execute_global_routes_to_global_pipeline(
        self,
        mock_data_manager,
        mock_discover,
        mock_ensure_cls,
        mock_resolve,
        mock_pipeline_run,
    ):
        from core.modules.tag import Tag
        from core.modules.tag.core.engines.global_based import GLOBAL_ENTITY_ID

        mock_data_manager.return_value = MagicMock(stock=MagicMock(tags=MagicMock()))
        info = _make_tag_info(key="macro_rate_stance", relative="demo/macro_rate_stance")
        info.settings["data"] = {
            "base": {"data_key": "macro.lpr", "params": {}},
            "required": [{"data_key": "macro.shibor", "params": {}}],
            "min_required_records": 0,
        }
        info.settings["calculation"] = {
            "update_mode": "incremental",
            "execution": {"start_date": "20240101", "end_date": "20240131"},
        }
        mock_discover.return_value = [info]
        mock_resolve.return_value = [GLOBAL_ENTITY_ID]
        mock_pipeline_run.return_value = {"success": True, "jobs": 1}
        mock_ensure_cls.return_value.ensure = MagicMock()

        with patch("core.modules.tag.tag.Tag._save_performance_report"):
            tag = Tag(is_verbose=False)
            tag.execute(scenario_name="macro_rate_stance")

        mock_resolve.assert_called_once()
        mock_pipeline_run.assert_called_once()
        assert mock_pipeline_run.call_args.kwargs["entity_ids"] == [GLOBAL_ENTITY_ID]
