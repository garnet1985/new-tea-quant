"""
批量重构 project_context 调用方文件

将 PathManager 等内部类的调用改为使用 ProjectContextManager
"""
import re
from pathlib import Path
from typing import List


def refactor_file(file_path: Path) -> bool:
    """重构单个文件"""
    try:
        content = file_path.read_text(encoding='utf-8')
        original_content = content

        # 1. 更新导入语句
        # 将 PathManager 导入改为 ProjectContextManager
        import_patterns = [
            (r'from core\.infra\.project_context import PathManager',
             'from core.infra.project_context import ProjectContextManager'), 
            (r'from core\.infra\.project_context import ConfigManager, PathManager',
             'from core.infra.project_context import ProjectContextManager'), 
            (r'from core\.infra\.project_context import PathManager, FileManager',
             'from core.infra.project_context import ProjectContextManager'), 
            (r'from core\.infra\.project_context import PathManager, ConfigManager, FileManager',
             'from core.infra.project_context import ProjectContextManager'), 
        ]

        for pattern, replacement in import_patterns:
            content = re.sub(pattern, replacement, content)

        # 2. 更新方法调用（静态方法 → 实例方法）
        # 策略：在每个文件开头创建一个模块级别的实例
        # 或者在使用的地方创建实例

        # 检查文件是否有 PathManager 的调用
        if 'PathManager.' in content:
            # 在文件开头添加实例创建（如果还没有）
            # 找到第一个函数/类定义之前的位置
            lines = content.split('\n')
            insert_pos = 0
            found_imports = False

            for i, line in enumerate(lines):
                if line.startswith('import ') or line.startswith('from '):
                    insert_pos = i + 1
                    found_imports = True
                elif found_imports and (line.startswith('def ') or line.startswith('class ') or line.startswith('@')):
                    break

            # 检查是否已经有 ctx 实例
            if not any('# ProjectContextManager instance' in line for line in lines):
                # 添加模块级别实例
                instance_code = '\n# ProjectContextManager instance (模块级别)\n_ctx = ProjectContextManager()\n'
                lines.insert(insert_pos, instance_code)
                content = '\n'.join(lines)

            # 3. 替换方法调用
            method_mapping = {
                'PathManager.get_project_root()': '_ProjectContextManager.get_project_root()',
                'PathManager.get_core_root()': '_ProjectContextManager.get_core_root()',
                'PathManager.get_userspace_root()': '_ProjectContextManager.get_userspace_root()',
                'PathManager.clear_userspace_cache()': '_ProjectContextManager.clear_userspace_cache()',
                'PathManager.get_strategies_root()': '_ProjectContextManager.get_userspace_root() / "strategies"',
                'PathManager.get_extensions_root()': '_ProjectContextManager.get_userspace_root() / "extensions"',
                'PathManager.get_system_root()': '_ProjectContextManager.get_userspace_root() / "system"',
                'PathManager.get_default_config_root()': '_ProjectContextManager.get_core_root() / "default_config"',
                'PathManager.get_user_config_root()': '_ProjectContextManager.get_userspace_root() / "system" / "config"',
                'PathManager.get_system_db_directory()': '_ProjectContextManager.get_userspace_root() / "system" / "db"',
                'PathManager.get_backup_directory()': '_ProjectContextManager.get_userspace_root() / "system" / "backup"',
                'PathManager.get_strategy_directory': '_ctx.get_strategy_directory',
                'PathManager.get_strategy_settings_path': '_ctx.get_strategy_directory',
                'PathManager.get_strategy_results_directory': '_ctx.get_strategy_directory',
                'PathManager.get_tags_root()': '_ProjectContextManager.get_userspace_root() / "extensions" / "tags"',
                'PathManager.get_tag_scenario_directory': '_ctx.get_tag_directory',
                'PathManager.get_data_source_root()': '_ProjectContextManager.get_userspace_root() / "extensions" / "data_source"',
                'PathManager.get_data_contract_root()': '_ProjectContextManager.get_userspace_root() / "extensions" / "data_contract"',
            }

            for old_call, new_call in method_mapping.items():
                content = content.replace(old_call, new_call)

        if content != original_content:
            file_path.write_text(content, encoding='utf-8')
            print(f"✅ Refactored: {file_path}")
            return True
        else:
            return False

    except Exception as e:
        print(f"❌ Error refactoring {file_path}: {e}")
        return False


def batch_refactor_files():
    """批量重构所有调用方文件"""
    files_to_refactor = [
        "core/modules/strategy/services/package/resolver.py",
        "core/modules/strategy/services/package/__test__/test_strategy_bundle.py",
        "core/modules/strategy/services/package/__test__/test_single_entity.py",
        "core/modules/strategy/engines/analyzer/helpers/ml.py",
        "core/modules/strategy/services/package/single.py",
        "core/modules/strategy/services/package/bundle.py",
        "core/modules/strategy/engines/scanner/helpers/cache_manager.py",
        "core/modules/strategy/services/data/output/simulation_output_retention.py",
        "core/modules/strategy/services/data/output/version_manager.py",
        "devtools/automation/table_exporting/export_table.py",
        "core/modules/strategy/services/discovery/__test__/test_discovery.py",
        "core/modules/strategy/engines/simulator/enumerator/shared/report.py",
        "core/modules/strategy/services/discovery/discovery.py",
        "core/modules/strategy/engines/simulator/enumerator/shared/services.py",
        "core/modules/strategy/strategy_manager.py",
        "core/modules/strategy/services/cache/simulator_res_db_cache/finger_print/env_resolver.py",
        "core/infra/system_actions/shortcuts/create_new_strategy/scaffold.py",
        "core/infra/db/migration/runner.py",
        "core/infra/db/schema_manager.py",
        "core/infra/system_actions/shortcuts/create_new_tag/scaffold.py",
    ]

    project_root = Path("/Users/garnet/Desktop/new-tea-quant")
    refactored_count = 0

    for file_path_str in files_to_refactor:
        file_path = project_root / file_path_str
        if file_path.exists():
            if refactor_file(file_path):
                refactored_count += 1

    print(f"\n✅ Total refactored: {refactored_count} files")
    print(f"❌ Failed or no changes: {len(files_to_refactor) - refactored_count} files")


if __name__ == "__main__":
    batch_refactor_files()