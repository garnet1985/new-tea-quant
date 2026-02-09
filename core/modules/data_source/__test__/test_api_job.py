"""
ApiJob 单元测试

注意：DataSourceTask 已被 ApiJobBatch 取代，相关测试已移除。
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
        from core.modules.data_source.data_class.api_job import ApiJob

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
        assert job.rate_limit == 0
    
    def test_post_init_api_name(self):
        """测试 api_name 自动设置"""
        from core.modules.data_source.data_class.api_job import ApiJob

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
        from core.modules.data_source.data_class.api_job import ApiJob

        job = ApiJob(
            provider_name="tushare",
            method="get_daily_kline",
            params={},
            depends_on=["job1", "job2"]
        )
        
        assert job.depends_on == ["job1", "job2"]




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
