"""
简单批量重构 - 将 PathManager 调用改为 ProjectContextManager

策略：
- 添加模块级别实例：ctx = ProjectContextManager()
- 替换所有 PathManager.xxx 调用为 ctx.xxx
"""
import re
from pathlib import Path


def simple_refactor_file(file_path: Path) -> bool:
    """简单重构单个文件"""
    try:
        content = file_path.read_text(encoding='utf-8')
        original_content = content

        # 1. 替换导入语句
        import_replacements = [
            ('from core.infra.project_context import PathManager',
             'from core.infra.project_context import ProjectContextManager'),
            ('from core.infra.project_context import ConfigManager, PathManager',
             'from core.infra.project_context import ProjectContextManager'),
            ('from core.infra.project_context import PathManager, ConfigManager',
             'from core.infra.project_context import ProjectContextManager'),
            ('from core.infra.project_context import PathManager, FileManager',
             'from core.infra.project_context import ProjectContextManager'),
            ('from core.infra.project_context import PathManager, ConfigManager, FileManager',
             'from core.infra.project_context import ProjectContextManager'),
        ]

        for old_import, new_import in import_replacements:
            content = content.replace(old_import, new_import)

        # 2. 如果文件中使用了 PathManager，添加模块级别实例
        if 'PathManager.' in content or 'PathManager(' in content:
            # 在导入语句后添加实例创建
            lines = content.split('\n')
            insert_pos = 0

            # 找到导入语句结束的位置
            for i, line in enumerate(lines):
                if line.startswith('from core.infra.project_context import'):
                    insert_pos = i + 1

            # 添加实例
            instance_line = '\nctx = ProjectContextManager()  # module-level instance\n'
            if insert_pos > 0:
                lines.insert(insert_pos, instance_line)
                content = '\n'.join(lines)

            # 3. 替换所有 PathManager 方法调用
            # 注意：PathManager 的方法都是静态方法，所以直接替换为 ctx 实例方法调用
            content = re.sub(r'PathManager\.(\w+)\(', r'ctx.\1(', content)

        # 4. 替换 ConfigManager 调用（如果存在）
        if 'ConfigManager.' in content:
            content = re.sub(r'ConfigManager\.(\w+)\(', r'ctx.\1(', content)

        # 5. 替换 FileManager 调用（如果存在）
        if 'FileManager.' in content:
            content = re.sub(r'FileManager\.(\w+)\(', r'ctx.\1(', content)

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
            if simple_refactor_file(file_path):
                refactored_count += 1

    print(f"\n✅ Total refactored: {refactored_count} files")
    print(f"❌ Failed or no changes: {len(files_to_refactor) - refactored_count} files")


if __name__ == "__main__":
    batch_refactor_files()