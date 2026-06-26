"""
完整批量重构 - 更新所有使用 DiscoveryManager、ConfigManager、FileManager 的文件

策略：
- 将所有内部Manager的导入改为 ProjectContextManager
- 添加模块级别实例：ctx = ProjectContextManager()
- 替换所有方法调用为 ctx 实例方法
- 处理特殊导入（merge_market_profile_dicts 等辅助函数）
"""
import re
from pathlib import Path


def full_refactor_file(file_path: Path) -> bool:
    """完整重构单个文件"""
    try:
        content = file_path.read_text(encoding='utf-8')
        original_content = content

        # 1. 处理特殊导入（辅助函数和常量）
        # 这些需要保留，不从 project_context 导入
        special_imports = {
            'merge_market_profile_dicts': 'from core.infra.project_context.config_merge_policies import merge_market_profile_dicts',
            'EXTENSIONS_MODULE_PREFIX': None,  # 删除，已经不暴露
            'extensions_module': None,  # 删除，已经改为 PathManager.get_extensions_module
        }

        # 2. 处理复合导入语句
        import_replacements = [
            # DiscoveryManager
            ('from core.infra.project_context import DiscoveryManager',
             'from core.infra.project_context import ProjectContextManager'),
            ('from core.infra.project_context import DiscoveryManager, PathManager',
             'from core.infra.project_context import ProjectContextManager'),
            ('from core.infra.project_context import PathManager, DiscoveryManager',
             'from core.infra.project_context import ProjectContextManager'),

            # ConfigManager
            ('from core.infra.project_context import ConfigManager',
             'from core.infra.project_context import ProjectContextManager'),
            ('from core.infra.project_context import ConfigManager, PathManager',
             'from core.infra.project_context import ProjectContextManager'),
            ('from core.infra.project_context import PathManager, ConfigManager',
             'from core.infra.project_context import ProjectContextManager'),
            ('from core.infra.project_context import DiscoveryManager, ConfigManager',
             'from core.infra.project_context import ProjectContextManager'),

            # FileManager
            ('from core.infra.project_context import FileManager',
             'from core.infra.project_context import ProjectContextManager'),
            ('from core.infra.project_context import FileManager, PathManager',
             'from core.infra.project_context import ProjectContextManager'),
            ('from core.infra.project_context import PathManager, FileManager',
             'from core.infra.project_context import ProjectContextManager'),

            # 三个Manager
            ('from core.infra.project_context import DiscoveryManager, ConfigManager, PathManager',
             'from core.infra.project_context import ProjectContextManager'),
            ('from core.infra.project_context import PathManager, ConfigManager, FileManager',
             'from core.infra.project_context import ProjectContextManager'),

            # 特殊情况：同时导入辅助函数
            ('from core.infra.project_context import DiscoveryManager, merge_market_profile_dicts',
             'from core.infra.project_context import ProjectContextManager\nfrom core.infra.project_context.config_merge_policies import merge_market_profile_dicts'),
            ('from core.infra.project_context import merge_market_profile_dicts, DiscoveryManager',
             'from core.infra.project_context import ProjectContextManager\nfrom core.infra.project_context.config_merge_policies import merge_market_profile_dicts'),
        ]

        for old_import, new_import in import_replacements:
            content = content.replace(old_import, new_import)

        # 3. 检查文件中是否有 Manager 的使用，添加实例
        needs_instance = any([
            'DiscoveryManager.' in content,
            'ConfigManager.' in content,
            'FileManager.' in content,
            'PathManager.' in content,
        ])

        if needs_instance:
            # 在导入语句后添加实例创建
            lines = content.split('\n')
            insert_pos = 0

            # 找到导入语句结束的位置
            for i, line in enumerate(lines):
                if line.startswith('from core.infra.project_context'):
                    insert_pos = i + 1

            # 添加实例（如果还没有）
            if not any('ctx = ProjectContextManager()' in line for line in lines):
                instance_line = '\nctx = ProjectContextManager()  # module-level instance\n'
                if insert_pos > 0:
                    lines.insert(insert_pos, instance_line)
                    content = '\n'.join(lines)

            # 4. 替换所有方法调用
            content = re.sub(r'DiscoveryManager\.(\w+)\(', r'ctx.\1(', content)
            content = re.sub(r'ConfigManager\.(\w+)\(', r'ctx.\1(', content)
            content = re.sub(r'FileManager\.(\w+)\(', r'ctx.\1(', content)
            content = re.sub(r'PathManager\.(\w+)\(', r'ctx.\1(', content)

        # 5. 删除废弃的导入
        if 'EXTENSIONS_MODULE_PREFIX' in content:
            content = re.sub(r'from core\.infra\.project_context import.*EXTENSIONS_MODULE_PREFIX.*\n', '', content)
        if 'extensions_module' in content and 'from core.infra.project_context import' in content:
            content = re.sub(r'from core\.infra\.project_context import.*extensions_module.*\n', '', content)

        if content != original_content:
            file_path.write_text(content, encoding='utf-8')
            print(f"✅ Refactored: {file_path}")
            return True
        else:
            return False

    except Exception as e:
        print(f"❌ Error refactoring {file_path}: {e}")
        return False


def batch_refactor_all_files():
    """批量重构所有需要更新的文件"""
    files_to_refactor = [
        "setup/steps/db_connection/install.py",
        "core/tables/stock/adj_factor_events/model.py",
        "devtools/quick_tools/renew_core_stock_data.py",
        "core/modules/data_manager/data_manager.py",
        "core/modules/data_source/data_source_manager.py",
        "core/utils/date/date_utils.py",
        "core/modules/tag/models/scenario_model.py",
        "core/infra/devcli/handlers.py",
        "core/modules/tag/services/discovery/discovery.py",
        "core/modules/tag/engines/shared/helper/tag_helper.py",
        "core/modules/tag/engines/shared/helper/job_helper.py",
        "core/modules/tag/engines/shared/backend.py",
        "core/modules/strategy/engines/simulator/enumerator/calendar_sliced/runtime/planner.py",
        "core/modules/data_source/service/sample_stock_list.py",
        "core/modules/data_source/service/renew/renew_common_helper.py",
        "core/modules/data_source/service/handler_helper.py",
        "core/modules/data_source/service/date_range/date_range_helper.py",
        "core/modules/data_source/catalog/freshness_probe.py",
        "core/modules/strategy/launcher/workbench_catalog.py",
        "core/modules/data_manager/data_services/calendar/calendar_service.py",
        "core/infra/db/db_manager.py",
        "core/modules/strategy/engines/shared/data_classes/strategy_settings/market_profile_settings.py",
        "core/infra/db/engines/duckdb/process_pool_scope.py",
        "core/modules/market_profile/market_profile_manager.py",
        "core/modules/market_profile/__test__/test_profile.py",
    ]

    project_root = Path("/Users/garnet/Desktop/new-tea-quant")
    refactored_count = 0

    for file_path_str in files_to_refactor:
        file_path = project_root / file_path_str
        if file_path.exists():
            if full_refactor_file(file_path):
                refactored_count += 1

    print(f"\n✅ Total refactored: {refactored_count} files")
    print(f"❌ Failed or no changes: {len(files_to_refactor) - refactored_count} files")


if __name__ == "__main__":
    batch_refactor_all_files()