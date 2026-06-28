"""
批量更新所有使用 PathManager 旧方法名的文件
"""
import re
from pathlib import Path


def update_file(file_path: Path) -> bool:
    """更新单个文件"""
    try:
        content = file_path.read_text(encoding='utf-8')
        original_content = content

        # PathManager 方法名映射
        method_mapping = {
            'PathManager.get_root()': 'PathManager.get_project_root()',
            'PathManager.core()': 'PathManager.get_core_root()',
            'PathManager.userspace()': 'PathManager.get_userspace_root()',
            'PathManager.invalidate_userspace_cache()': 'PathManager.clear_userspace_cache()',
            'PathManager.strategies_root()': 'PathManager.get_strategies_root()',
            'PathManager.extensions_root()': 'PathManager.get_extensions_root()',
            'PathManager.system_root()': 'PathManager.get_system_root()',
            'PathManager.default_config()': 'PathManager.get_default_config_root()',
            'PathManager.user_config()': 'PathManager.get_user_config_root()',
            'PathManager.config()': 'PathManager.get_user_config_root()',
            'PathManager.system_db()': 'PathManager.get_system_db_directory()',
            'PathManager.backup()': 'PathManager.get_backup_directory()',
            'PathManager.backup_data()': 'PathManager.get_backup_data_directory()',
            'PathManager.updater()': 'PathManager.get_updater_directory()',
            'PathManager.userspace_ntq()': 'PathManager.get_userspace_ntq_directory()',
            'PathManager.userspace_tmp()': 'PathManager.get_userspace_tmp_directory()',
            'PathManager.strategy': 'PathManager.get_strategy_directory',
            'PathManager.strategy_settings': 'PathManager.get_strategy_settings_path',
            'PathManager.strategy_results': 'PathManager.get_strategy_results_directory',
            'PathManager.tags()': 'PathManager.get_tags_root()',
            'PathManager.tag_scenario': 'PathManager.get_tag_scenario_directory',
            'PathManager.data_source()': 'PathManager.get_data_source_root()',
            'PathManager.data_contract()': 'PathManager.get_data_contract_root()',
            'PathManager.extensions_tables()': 'PathManager.get_extensions_tables_directory()',
            'PathManager.adapters()': 'PathManager.get_adapters_directory()',
            'ctx.path.get_root()': 'ProjectContextManager.get_project_root()',
        }

        for old_name, new_name in method_mapping.items():
            content = content.replace(old_name, new_name)

        if content != original_content:
            file_path.write_text(content, encoding='utf-8')
            print(f"✅ Updated: {file_path}")
            return True
        else:
            return False

    except Exception as e:
        print(f"❌ Error updating {file_path}: {e}")
        return False


def batch_update_all_files():
    """批量更新所有文件"""
    files_to_update = [
        # 核心文件
        "core/infra/project_context/discovery_manager.py",
        "core/infra/project_context/project_context_manager.py",
        # 测试文件
        "core/infra/project_context/__test__/test_config_manager.py",
        "core/infra/project_context/__test__/test_discovery_manager.py",
        "core/infra/project_context/__test__/test_project_context_manager.py",
    ]

    project_root = Path("/Users/garnet/Desktop/new-tea-quant")
    updated_count = 0

    for file_path_str in files_to_update:
        file_path = project_root / file_path_str
        if file_path.exists():
            if update_file(file_path):
                updated_count += 1

    print(f"\n✅ Total updated: {updated_count} files")


if __name__ == "__main__":
    batch_update_all_files()