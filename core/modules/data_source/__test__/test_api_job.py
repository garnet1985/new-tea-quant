"""
ApiJob 和 DataSourceTask 单元测试
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

try:
    import pytest
    HAS_PYTEST = True
except ImportError:
    HAS_PYTEST = False


class TestApiJob:
    """ApiJob 测试类"""
    
    def test_init(self):
        """测试 ApiJob 初始化"""
        from core.modules.data_source.data_classes import ApiJob
        
        job = ApiJob(
            provider_name="tushare",
            method="get_stock_list",
            params={"fields": "ts_code,name"}
        )
        
        assert job.provider_name == "tushare"
        assert job.method == "get_stock_list"
        assert job.params == {"fields": "ts_code,name"}
        assert job.api_name == "get_stock_list"  # 自动设置
        assert job.depends_on == []
        assert job.priority == 0
    
    def test_post_init_api_name(self):
        """测试 api_name 自动设置"""
        from core.modules.data_source.data_classes import ApiJob
        
        # 不指定 api_name，应该使用 method
        job1 = ApiJob(
            provider_name="tushare",
            method="get_stock_list",
            params={}
        )
        assert job1.api_name == "get_stock_list"
        
        # 指定 api_name，应该使用指定的值
        job2 = ApiJob(
            provider_name="tushare",
            method="get_stock_list",
            params={},
            api_name="custom_api_name"
        )
        assert job2.api_name == "custom_api_name"
    
    def test_depends_on(self):
        """测试依赖关系"""
        from core.modules.data_source.data_classes import ApiJob
        
        job = ApiJob(
            provider_name="tushare",
            method="get_daily_kline",
            params={},
            depends_on=["job1", "job2"]
        )
        
        assert job.depends_on == ["job1", "job2"]


class TestDataSourceTask:
    """DataSourceTask 测试类"""
    
    def test_init(self):
        """测试 DataSourceTask 初始化"""
        from core.modules.data_source.data_classes import ApiJob, DataSourceTask
        
        job1 = ApiJob(provider_name="tushare", method="get_stock_list", params={})
        job2 = ApiJob(provider_name="akshare", method="get_kline", params={})
        
        task = DataSourceTask(
            task_id="test_task",
            api_jobs=[job1, job2]
        )
        
        assert task.task_id == "test_task"
        assert len(task.api_jobs) == 2
        assert task.api_jobs[0].job_id == "test_task_job_0"
        assert task.api_jobs[1].job_id == "test_task_job_1"
    
    def test_post_init_job_id(self):
        """测试 job_id 自动生成"""
        from core.modules.data_source.data_classes import ApiJob, DataSourceTask
        
        # 不指定 job_id，应该自动生成
        job1 = ApiJob(provider_name="tushare", method="get_stock_list", params={})
        job2 = ApiJob(provider_name="tushare", method="get_kline", params={}, job_id="custom_job_id")
        
        task = DataSourceTask(
            task_id="test_task",
            api_jobs=[job1, job2]
        )
        
        assert task.api_jobs[0].job_id == "test_task_job_0"
        assert task.api_jobs[1].job_id == "custom_job_id"  # 已指定，不覆盖


if __name__ == "__main__":
    if HAS_PYTEST:
        pytest.main([__file__])
    else:
        # 简单测试运行
        print("运行 ApiJob 测试...")
        test_api_job = TestApiJob()
        try:
            test_api_job.test_init()
            print("✅ test_init 通过")
        except Exception as e:
            print(f"❌ test_init 失败: {e}")
        
        try:
            test_api_job.test_post_init_api_name()
            print("✅ test_post_init_api_name 通过")
        except Exception as e:
            print(f"❌ test_post_init_api_name 失败: {e}")
        
        print("\n运行 DataSourceTask 测试...")
        test_task = TestDataSourceTask()
        try:
            test_task.test_init()
            print("✅ test_init 通过")
        except Exception as e:
            print(f"❌ test_init 失败: {e}")
        
        try:
            test_task.test_post_init_job_id()
            print("✅ test_post_init_job_id 通过")
        except Exception as e:
            print(f"❌ test_post_init_job_id 失败: {e}")
