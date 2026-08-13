"""
批量更新 PathManager 方法名

将所有旧方法名替换为新方法名
"""
from core.infra.cmd_layout import i

import re
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


# 方法名映射表（旧名 → 新名）
METHOD_MAPPING = {
    # 核心路径方法
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

    # 系统目录方法
    'PathManager.system_db()': 'PathManager.get_system_db_directory()',
    'PathManager.backup()': 'PathManager.get_backup_directory()',
    'PathManager.backup_data()': 'PathManager.get_backup_data_directory()',
    'PathManager.updater()': 'PathManager.get_updater_directory()',
    'PathManager.userspace_ntq()': 'PathManager.get_userspace_ntq_directory()',
    'PathManager.userspace_tmp()': 'PathManager.get_userspace_tmp_directory()',

    # 策略相关方法
    'PathManager.strategy': 'PathManager.get_strategy_directory',
    'PathManager.strategy_settings': 'PathManager.get_strategy_settings_path',
    'PathManager.strategy_results': 'PathManager.get_strategy_results_directory',
    'PathManager.strategy_simulation_enum': 'PathManager.get_strategy_simulation_enum_directory',
    'PathManager.strategy_simulation_price': 'PathManager.get_strategy_simulation_price_directory',
    'PathManager.strategy_simulation_portfolio': 'PathManager.get_strategy_simulation_portfolio_directory',
    'PathManager.strategy_scan_results': 'PathManager.get_strategy_scan_results_directory',

    # Tag 相关方法
    'PathManager.tags()': 'PathManager.get_tags_root()',
    'PathManager.tag_scenario': 'PathManager.get_tag_scenario_directory',
    'PathManager.tag_scenario_settings': 'PathManager.get_tag_scenario_settings_path',
    'PathManager.tag_scenario_worker': 'PathManager.get_tag_scenario_worker_path',

    # Data Source 相关方法
    'PathManager.data_source()': 'PathManager.get_data_source_root()',
    'PathManager.data_source_mapping()': 'PathManager.get_data_source_mapping_path()',
    'PathManager.data_source_handlers()': 'PathManager.get_data_source_handlers_directory()',
    'PathManager.data_source_handler': 'PathManager.get_data_source_handler_directory',
    'PathManager.data_source_providers()': 'PathManager.get_data_source_providers_directory()',
    'PathManager.data_source_provider': 'PathManager.get_data_source_provider_directory',

    # Data Contract 相关方法
    'PathManager.data_contract()': 'PathManager.get_data_contract_root()',
    'PathManager.data_contract_mapping()': 'PathManager.get_data_contract_mapping_path()',
    'PathManager.data_contract_loaders()': 'PathManager.get_data_contract_loaders_directory()',

    # Tables / Adapters 相关方法
    'PathManager.extensions_tables()': 'PathManager.get_extensions_tables_directory()',
    'PathManager.adapters()': 'PathManager.get_adapters_directory()',
}


def update_file(file_path: Path) -> bool:
    """更新单个文件"""
    try:
        content = file_path.read_text(encoding='utf-8')
        original_content = content

        # 按照映射表进行替换
        for old_name, new_name in METHOD_MAPPING.items():
            # 特殊处理：带参数的方法（如 PathManager.strategy(name)）
            # 使用正则表达式匹配，保留参数部分
            if old_name.endswith('(') and new_name.endswith('('):
                # 匹配带参数的调用
                pattern = re.escape(old_name.rstrip('(')) + r'\(([^)]*)\)'
                replacement = new_name.rstrip('(') + r'(\1)'
                content = re.sub(pattern, replacement, content)
            elif not old_name.endswith('()') and not new_name.endswith('()'):
                # 方法名作为属性访问（如 PathManager.strategy_simulation_enum）
                # 可能作为函数引用，不带参数
                # 例如：return PathManager.strategy_simulation_enum
                pattern = re.escape(old_name)
                replacement = new_name
                content = re.sub(pattern, replacement, content)
            else:
                # 无参数的方法调用
                content = content.replace(old_name, new_name)

        if content != original_content:
            file_path.write_text(content, encoding='utf-8')
            logger.info(f"{i('success')} Updated: {file_path}")
            return True
        else:
            return False

    except Exception as e:
        logger.error(f"{i('error')} Error updating {file_path}: {e}")
        return False


def batch_update_files():
    """批量更新所有文件"""
    # 需要更新的文件列表（从grep结果中提取）
    files_to_update = [
        "core/infra/project_context/config_manager.py",
        "core/modules/strategy/services/cache/simulator_res_db_cache/cache_service.py",
        "core/modules/strategy/launcher/workbench.py",
        "core/modules/strategy/engines/simulator/enumerator/shared/services.py",
        "core/modules/tag/engines/shared/runner.py",
        "core/bff/APIs/strategy/routes/report/stock_detail.py",
        "devtools/quick_tools/stock_pool_ops.py",
        "core/bff/APIs/settings/routes.py",
        "core/modules/strategy/strategy_manager.py",
        "core/modules/strategy/services/progress/progress_recorder.py",
        "core/modules/strategy/launcher/scanner_run.py",
        "core/modules/strategy/engines/simulator/enumerator/shared/report.py",
        "core/modules/data_source/data_source_manager.py",
        "core/modules/data_source/catalog/provider_probe.py",
        "core/modules/data_manager/data_manager.py",
        "core/infra/system_actions/shortcuts/create_new_tag/scaffold.py",
        "core/infra/system_actions/shortcuts/create_new_strategy/scaffold.py",
        "core/infra/system_actions/core/pipeline_lease/pipeline_lease.py",
        "core/infra/cli/dev/scripts/temp_cleanup/temp_cleanup.py",
        "core/infra/cli/dev/scripts/temp_cleanup/__test__/test_temp_cleanup.py",
        "setup/install_runtime.py",
        "devtools/quick_tools/renew_core_stock_data.py",
        "core/tables/stock/adj_factor_events/model.py",
        "core/modules/strategy/services/package/single.py",
        "core/modules/strategy/services/package/resolver.py",
        "core/modules/strategy/services/package/bundle.py",
        "core/modules/strategy/services/discovery/discovery.py",
        "core/modules/strategy/services/data/output/version_manager.py",
        "core/modules/strategy/services/conftest.py",
        "core/modules/strategy/services/cache/simulator_res_db_cache/report_slot_disk_hydrate.py",
        "core/modules/strategy/services/cache/simulator_res_db_cache/finger_print/env_resolver.py",
        "core/modules/strategy/launcher/package_cli.py",
        "core/modules/strategy/execution_manager/workbench_resolve.py",
        "core/modules/strategy/engines/shared/helpers/strategy_runtime.py",
        "core/infra/project_context/__test__/test_config_manager.py",
        "core/infra/setup/core/steps/db_connection/install.py",
        "core/bff/APIs/setup/runtime.py",
        "core/bff/APIs/setup/service.py",
        "core/modules/strategy/services/data/output/simulation_output_retention.py",
        "core/modules/data_source/base_class/base_provider.py",
        "core/modules/strategy/engines/shared/helpers/stock_sampling.py",
        "core/infra/db/migration/runner.py",
        "core/infra/db/core/schema_manager.py",
        "core/modules/data_source/service/manager_helper.py",
        "core/modules/strategy/engines/scanner/helpers/cache_manager.py",
        "core/modules/strategy/engines/analyzer/helpers/ml.py",
        "core/infra/db/core/engines/duckdb/paths.py",
        "devtools/automation/table_exporting/export_table.py",
    ]

    project_root = Path("/Users/garnet/Desktop/new-tea-quant")
    updated_count = 0

    for file_path_str in files_to_update:
        file_path = project_root / file_path_str
        if file_path.exists():
            if update_file(file_path):
                updated_count += 1

    logger.info(f"\n{i('success')} Total updated: {updated_count} files")
    logger.info(f"{i('error')} Failed or no changes: {len(files_to_update) - updated_count} files")


if __name__ == "__main__":
    batch_update_files()