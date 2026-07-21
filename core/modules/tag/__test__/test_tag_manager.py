"""TagManager 单元测试。"""
from pathlib import Path
from unittest.mock import MagicMock, patch


class TestTagManager:
    """TagManager 测试类"""
    
    @patch('core.modules.tag.tag_manager.DataManager')
    @patch('core.modules.tag.tag_manager.get_scenarios_root')
    def test_init(self, mock_get_scenarios_root, mock_data_manager):
        """测试 TagManager 初始化"""
        from core.modules.tag.tag_manager import TagManager
        from pathlib import Path
        
        # Mock scenarios root
        mock_root = Path("/test/scenarios")
        mock_get_scenarios_root.return_value = mock_root
        
        # Mock DataManager
        mock_data_mgr = MagicMock()
        mock_tag_service = MagicMock()
        mock_tag_service.save_batch.side_effect = lambda rows: len(rows)
        mock_data_mgr.stock.tags = mock_tag_service
        mock_data_manager.return_value = mock_data_mgr
        
        # Mock scenario discovery
        with patch.object(TagManager, '_discover_scenarios_from_folder') as mock_discover:
            manager = TagManager(is_verbose=False)
            
            assert manager.is_verbose is False
            assert manager.data_mgr == mock_data_mgr
            assert manager.tag_data_service == mock_tag_service
            assert manager.scenario_cache == {}
            assert manager.entity_list_cache == {}
            mock_discover.assert_called_once()
    
    @patch('core.modules.tag.tag_manager.DataManager')
    @patch('core.modules.tag.tag_manager.get_scenarios_root')
    def test_refresh_scenario(self, mock_get_scenarios_root, mock_data_manager):
        """测试 refresh_scenario"""
        from core.modules.tag.tag_manager import TagManager
        
        mock_get_scenarios_root.return_value = Path("/test/scenarios")
        mock_data_mgr = MagicMock()
        mock_data_mgr.stock.tags = MagicMock()
        mock_data_manager.return_value = mock_data_mgr
        
        with patch.object(TagManager, '_discover_scenarios_from_folder') as mock_discover, \
             patch.object(TagManager, '_clear_cache') as mock_clear_cache:
            
            manager = TagManager(is_verbose=False)
            # 重置 mock 调用计数（因为 __init__ 中已经调用了一次）
            mock_discover.reset_mock()
            manager.scenario_cache = {"test": "cache"}
            manager.entity_list_cache = {"test": "cache"}
            
            manager.refresh_scenario()
            
            mock_clear_cache.assert_called_once()
            mock_discover.assert_called_once()
    
    @patch('core.modules.tag.tag_manager.DataManager')
    @patch('core.modules.tag.tag_manager.get_scenarios_root')
    def test_execute_with_scenario_name(self, mock_get_scenarios_root, mock_data_manager):
        """测试 execute（指定 scenario_name）"""
        from core.modules.tag.tag_manager import TagManager
        
        mock_get_scenarios_root.return_value = Path("/test/scenarios")
        mock_data_mgr = MagicMock()
        mock_data_mgr.stock.tags = MagicMock()
        mock_data_manager.return_value = mock_data_mgr
        
        with patch.object(TagManager, '_discover_scenarios_from_folder'), \
             patch.object(TagManager, '_execute_named') as mock_execute_named:
            
            manager = TagManager(is_verbose=False)
            manager.execute(scenario_name="test_scenario")
            
            mock_execute_named.assert_called_once_with("test_scenario")
    
    @patch('core.modules.tag.tag_manager.DataManager')
    @patch('core.modules.tag.tag_manager.get_scenarios_root')
    def test_execute_with_settings(self, mock_get_scenarios_root, mock_data_manager):
        """测试 execute（指定 settings）"""
        from core.modules.tag.tag_manager import TagManager
        
        mock_get_scenarios_root.return_value = Path("/test/scenarios")
        mock_data_mgr = MagicMock()
        mock_data_mgr.stock.tags = MagicMock()
        mock_data_manager.return_value = mock_data_mgr
        
        settings = {
            "is_enabled": True,
            "meta": {"display_name": "test"},
            "calculation": {"update_mode": "incremental"},
            "data": {
                "base_required_data": {
                    "data_id": "stock.kline.daily",
                    "params": {"adjust": "qfq"},
                },
                "min_required_records": 10,
            },
            "tags": [{"name": "tag1"}],
        }
        
        with patch.object(TagManager, '_discover_scenarios_from_folder'), \
             patch.object(TagManager, '_run_scenario') as mock_run_scenario:
            
            manager = TagManager(is_verbose=False)
            manager.execute(scenario_name="test_scenario", settings=settings)
            
            mock_run_scenario.assert_called_once()
    
    @patch('core.modules.tag.tag_manager.DataManager')
    @patch('core.modules.tag.tag_manager.get_scenarios_root')
    def test_execute_all(self, mock_get_scenarios_root, mock_data_manager):
        """测试 execute（执行所有 scenarios）"""
        from core.modules.tag.tag_manager import TagManager
        
        mock_get_scenarios_root.return_value = Path("/test/scenarios")
        mock_data_mgr = MagicMock()
        mock_data_mgr.stock.tags = MagicMock()
        mock_data_manager.return_value = mock_data_mgr
        
        with patch.object(TagManager, '_discover_scenarios_from_folder'), \
             patch.object(TagManager, '_execute_named') as mock_execute_named:
            
            manager = TagManager(is_verbose=False)
            manager.scenario_cache = {
                "scenario1": {},
                "scenario2": {}
            }
            
            manager.execute()
            
            assert mock_execute_named.call_count == 2
            mock_execute_named.assert_any_call("scenario1")
            mock_execute_named.assert_any_call("scenario2")
    
    @patch('core.modules.tag.tag_manager.DataManager')
    @patch('core.modules.tag.tag_manager.get_scenarios_root')
    def test_discover_scenarios_from_folder_not_exists(self, mock_get_scenarios_root, mock_data_manager):
        """测试 _discover_scenarios_from_folder（目录不存在）"""
        from core.modules.tag.tag_manager import TagManager
        
        mock_root = Path("/test/scenarios")
        mock_get_scenarios_root.return_value = mock_root
        
        mock_data_mgr = MagicMock()
        mock_data_mgr.stock.tags = MagicMock()
        mock_data_manager.return_value = mock_data_mgr
        
        with patch.object(Path, 'exists', return_value=False):
            manager = TagManager(is_verbose=False)
            
            assert manager.scenario_cache == {}
    
    @patch('core.modules.tag.tag_manager.DataManager')
    @patch('core.modules.tag.tag_manager.get_scenarios_root')
    def test_scenario_cache_lookup(self, mock_get_scenarios_root, mock_data_manager):
        """scenario_cache 按名称读取配置。"""
        from core.modules.tag.tag_manager import TagManager
        
        mock_get_scenarios_root.return_value = Path("/test/scenarios")
        mock_data_mgr = MagicMock()
        mock_data_mgr.stock.tags = MagicMock()
        mock_data_manager.return_value = mock_data_mgr
        
        with patch.object(TagManager, '_discover_scenarios_from_folder'):
            manager = TagManager(is_verbose=False)
            manager.scenario_cache = {
                "test_scenario": {
                    "settings": {"name": "test_scenario"},
                    "worker_class": None
                }
            }
            
            result = manager.scenario_cache.get("test_scenario")
            
            assert result is not None
            assert result["settings"]["name"] == "test_scenario"

    @patch('core.modules.tag.tag_manager.DataManager')
    @patch('core.modules.tag.tag_manager.get_scenarios_root')
    def test_scenario_cache_miss(self, mock_get_scenarios_root, mock_data_manager):
        from core.modules.tag.tag_manager import TagManager
        
        mock_get_scenarios_root.return_value = Path("/test/scenarios")
        mock_data_mgr = MagicMock()
        mock_data_mgr.stock.tags = MagicMock()
        mock_data_manager.return_value = mock_data_mgr
        
        with patch.object(TagManager, '_discover_scenarios_from_folder'):
            manager = TagManager(is_verbose=False)
            manager.scenario_cache = {}
            
            assert manager.scenario_cache.get("test_scenario") is None

    @patch('core.modules.tag.tag_manager.DataManager')
    @patch('core.modules.tag.tag_manager.get_scenarios_root')
    def test_run_scenario_general_uses_general_owner(self, mock_get_scenarios_root, mock_data_manager):
        """测试 general 模式固定使用 __general__ owner"""
        from core.modules.tag.enums import TagExecutionMode
        from core.modules.tag.tag_manager import TagManager

        mock_get_scenarios_root.return_value = Path("/test/scenarios")
        mock_data_mgr = MagicMock()
        mock_data_mgr.stock.tags = MagicMock()
        mock_data_manager.return_value = mock_data_mgr

        with patch.object(TagManager, "_discover_scenarios_from_folder"), \
             patch.object(TagManager, "_get_worker_class", return_value=MagicMock()), \
             patch("core.modules.tag.tag_manager.run_timeline_pipeline") as mock_run:
            manager = TagManager(is_verbose=False)
            scenario_model = MagicMock()
            scenario_model.is_enabled.return_value = True
            scenario_model.get_name.return_value = "macro_general"
            scenario_model.get_execution_mode.return_value = TagExecutionMode.ENTITY_TIMELINE
            scenario_model.get_settings.return_value = {
                "name": "macro_general",
                "tag_target_type": "general",
                "performance": {
                    "update_mode": "incremental",
                    "entities_per_job": 100,
                },
                "data": {
                    "required": [{"data_id": "macro.gdp", "params": {}}],
                    "tag_time_axis_based_on": "macro.gdp",
                },
                "tags": [{"name": "macro_tag"}],
            }
            manager._run_scenario(scenario_model, tag_key="macro_general")

            _, kwargs = mock_run.call_args
            assert kwargs["entity_list"] == ["__general__"]

    @patch("core.modules.backtest_engine.BacktestEngine.entity_based.run")
    @patch("core.modules.tag.tag_manager.DataManager")
    @patch("core.modules.tag.tag_manager.get_scenarios_root")
    def test_run_tag_timeline_saves_on_engine_result(
        self,
        mock_get_scenarios_root,
        mock_data_manager,
        mock_timeline_run,
    ):
        """Worker 返回 tag_values，主进程 on_result 调用 save_batch。"""
        from core.modules.backtest_engine.contracts import JobReport, RunProgress
        from core.modules.tag.services.execution.tag_job_pipeline import (
            run_tag_timeline_via_backtest_engine,
        )

        mock_get_scenarios_root.return_value = Path("/test/scenarios")
        mock_data_mgr = MagicMock()
        mock_tag_service = MagicMock()
        mock_tag_service.save_batch.side_effect = lambda rows: len(rows)
        mock_data_mgr.stock.tags = mock_tag_service
        mock_data_mgr.db = MagicMock()
        mock_data_manager.return_value = mock_data_mgr

        def fake_timeline_run(jobs, **kwargs):
            callbacks = kwargs["callbacks"]
            assert callbacks is not None
            assert kwargs.get("timeline_hooks_factory") is not None
            callbacks.on_task_result(
                JobReport(
                    job_id="job1",
                    success=True,
                    data={"tag_values": [{"entity_id": "000001", "json_value": "1"}]},
                ),
                RunProgress(finished=1, total=1, ok=1, fail=0),
            )
            return type(
                "RunResult",
                (),
                {
                    "job_results": [],
                    "success": True,
                    "total_jobs": 1,
                    "completed_jobs": 1,
                    "failed_jobs": 0,
                    "elapsed_seconds": 0.0,
                    "mode": "entity_based",
                    "plan": None,
                    "monitor_stats": None,
                },
            )()

        mock_timeline_run.side_effect = fake_timeline_run

        with patch(
            "core.modules.tag.services.execution.tag_job_pipeline._make_tag_save_fn",
            lambda _name: mock_tag_service.save_batch,
        ):
            result = run_tag_timeline_via_backtest_engine(
                timeline_jobs=[{"job_id": "job1", "entity_id": "000001"}],
                settings={
                    "scenario_name": "test_scenario",
                    "run_options": {"save_batch_size": 500},
                },
                duckdb_data_mgr=mock_data_mgr,
            )

        mock_tag_service.save_batch.assert_called_once_with(
            [{"entity_id": "000001", "json_value": "1"}]
        )
        assert result["completed_jobs"] == 1
        assert result["saved_tag_values"] == 1

    @patch("core.modules.backtest_engine.BacktestEngine.entity_based.run")
    @patch("core.modules.tag.tag_manager.DataManager")
    @patch("core.modules.tag.tag_manager.get_scenarios_root")
    def test_run_tag_timeline_batches_save_on_engine_result(
        self,
        mock_get_scenarios_root,
        mock_data_manager,
        mock_timeline_run,
    ):
        """多个 job 的 tag_values 按 save_batch_size 合并 upsert。"""
        from core.modules.backtest_engine.contracts import JobReport, RunProgress
        from core.modules.tag.services.execution.tag_job_pipeline import (
            run_tag_timeline_via_backtest_engine,
        )

        mock_get_scenarios_root.return_value = Path("/test/scenarios")
        mock_data_mgr = MagicMock()
        mock_tag_service = MagicMock()
        mock_tag_service.save_batch.side_effect = lambda rows: len(rows)
        mock_data_mgr.stock.tags = mock_tag_service
        mock_data_mgr.db = MagicMock()
        mock_data_manager.return_value = mock_data_mgr

        def fake_timeline_run(jobs, **kwargs):
            on_task_result = kwargs["callbacks"].on_task_result
            for i in range(3):
                on_task_result(
                    JobReport(
                        job_id=f"job{i}",
                        success=True,
                        data={"tag_values": [{"entity_id": f"00000{i}", "json_value": "1"}]},
                    ),
                    RunProgress(finished=i + 1, total=3, ok=i + 1, fail=0),
                )
            return type(
                "RunResult",
                (),
                {
                    "job_results": [],
                    "success": True,
                    "total_jobs": 3,
                    "completed_jobs": 3,
                    "failed_jobs": 0,
                    "elapsed_seconds": 0.0,
                    "mode": "entity_based",
                    "plan": None,
                    "monitor_stats": None,
                },
            )()

        mock_timeline_run.side_effect = fake_timeline_run

        with patch(
            "core.modules.tag.services.execution.tag_job_pipeline._make_tag_save_fn",
            lambda _name: mock_tag_service.save_batch,
        ):
            result = run_tag_timeline_via_backtest_engine(
                timeline_jobs=[{"job_id": f"job{i}"} for i in range(3)],
                settings={
                    "scenario_name": "test_scenario",
                    "run_options": {
                        "save_batch_size": 2,
                    },
                },
                duckdb_data_mgr=mock_data_mgr,
            )

        assert mock_tag_service.save_batch.call_count == 2
        assert mock_tag_service.save_batch.call_args_list[0].args[0] == [
            {"entity_id": "000000", "json_value": "1"},
            {"entity_id": "000001", "json_value": "1"},
        ]
        assert mock_tag_service.save_batch.call_args_list[1].args[0] == [
            {"entity_id": "000002", "json_value": "1"},
        ]
        assert result["saved_tag_values"] == 3
