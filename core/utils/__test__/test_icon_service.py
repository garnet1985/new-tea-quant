"""
icon_service.py 单元测试
"""
try:
    import pytest
except ImportError:
    pytest = None

from core.utils.icon.icon_service import IconService, i


class TestIconService:
    """IconService 测试类"""
    
    def test_get_success(self):
        """测试获取成功图标"""
        assert IconService.get("success") == "✅"
        assert IconService.get("check") == "✅"
        assert IconService.get("ok") == "✅"
    
    def test_get_error(self):
        """测试获取错误图标"""
        assert IconService.get("error") == "❌"
        assert IconService.get("failed") == "❌"
        assert IconService.get("err") == "❌"
    
    def test_get_warning(self):
        """测试获取警告图标"""
        assert IconService.get("warning") == "⚠️"
        assert IconService.get("exclamation") == "⚠️"
    
    def test_get_info(self):
        """测试获取信息图标"""
        assert IconService.get("info") == "ℹ️"
        assert IconService.get("information") == "ℹ️"
    
    def test_get_dot_icons(self):
        """测试获取点状图标"""
        assert IconService.get("green_dot") == "🟢"
        assert IconService.get("red_dot") == "🔴"
        assert IconService.get("blue_dot") == "🔵"
        assert IconService.get("yellow_dot") == "🟡"
        assert IconService.get("orange_dot") == "🟠"
    
    def test_get_functional_icons(self):
        """测试获取功能图标"""
        assert IconService.get("search") == "🔍"
        assert IconService.get("calendar") == "📅"
        assert IconService.get("bar_chart") == "📊"
        assert IconService.get("line_chart") == "📈"
        assert IconService.get("money") == "💰"
        assert IconService.get("rocket") == "🚀"
        assert IconService.get("gear") == "🔧"
        assert IconService.get("clock") == "🕙"
        assert IconService.get("target") == "🎯"
        assert IconService.get("ongoing") == "🔄"
    
    def test_case_insensitive(self):
        """测试大小写不敏感"""
        assert IconService.get("SUCCESS") == "✅"
        assert IconService.get("Success") == "✅"
        assert IconService.get("GREEN_DOT") == "🟢"
    
    def test_unknown_icon(self):
        """测试未知图标"""
        result = IconService.get("unknown_icon")
        assert result == ""  # 返回空字符串
    
    def test_simplified_api_i(self):
        """测试简化 API i()"""
        assert i("success") == "✅"
        assert i("error") == "❌"
        assert i("green_dot") == "🟢"
        assert i("unknown") == ""  # 未知图标返回空字符串
