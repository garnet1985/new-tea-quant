"""
生成 camelCase 到 snake_case 的转换计划
"""
import json
import os
import re

def camel_to_snake(name):
    """将 camelCase 转换为 snake_case"""
    # 在大写字母前插入下划线
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    # 处理连续大写字母
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

def is_camel_case(name):
    """检查是否为驼峰命名"""
    return bool(re.search(r'[A-Z]', name))

def analyze_table(schema_path):
    """分析单个表并生成转换计划"""
    with open(schema_path, 'r', encoding='utf-8') as f:
        schema = json.load(f)
    
    table_name = schema['name']
    fields = schema.get('fields', [])
    
    conversions = []
    for field in fields:
        field_name = field['name']
        if is_camel_case(field_name):
            snake_name = camel_to_snake(field_name)
            conversions.append({
                'original': field_name,
                'converted': snake_name,
                'type': field.get('type', ''),
                'description': field.get('description', '')
            })
    
    return table_name, conversions

def main():
    tables_dir = 'utils/db/tables'
    all_conversions = {}
    
    # 遍历所有表
    for table_dir in sorted(os.listdir(tables_dir)):
        table_path = os.path.join(tables_dir, table_dir)
        schema_file = os.path.join(table_path, 'schema.json')
        
        if os.path.isdir(table_path) and os.path.exists(schema_file):
            table_name, conversions = analyze_table(schema_file)
            if conversions:
                all_conversions[table_name] = conversions
    
    # 输出转换计划
    print("=" * 100)
    print("数据库字段命名规范统一计划：camelCase → snake_case")
    print("=" * 100)
    print()
    
    total_fields = sum(len(convs) for convs in all_conversions.values())
    print(f"📊 总计需要转换: {total_fields} 个字段，{len(all_conversions)} 个表\n")
    
    for table_name, conversions in all_conversions.items():
        print(f"{'='*100}")
        print(f"表: {table_name}")
        print(f"{'='*100}")
        print(f"需要转换 {len(conversions)} 个字段:\n")
        
        for i, conv in enumerate(conversions, 1):
            print(f"  {i:2d}. {conv['original']:30s} → {conv['converted']:30s}")
            if conv['description']:
                print(f"      描述: {conv['description']}")
        print()
    
    print("=" * 100)
    print("🔧 执行步骤:")
    print("=" * 100)
    print("1. 修改所有 schema.json 文件中的字段名")
    print("2. 执行数据库迁移 SQL（ALTER TABLE ... CHANGE COLUMN ...）")
    print("3. 更新所有 Python 代码中的字段引用")
    print("   - model.py 文件")
    print("   - renewer.py 文件")
    print("   - config.py 文件（field mapping）")
    print("   - storage.py 文件")
    print("   - 其他业务代码")
    print("4. 运行测试确保无遗漏")
    print()
    
    # 生成 SQL 迁移脚本
    print("=" * 100)
    print("📝 SQL 迁移脚本预览（部分）:")
    print("=" * 100)
    for table_name, conversions in list(all_conversions.items())[:2]:  # 只显示前2个表作为示例
        print(f"\n-- 表: {table_name}")
        for conv in conversions:
            # 简化的 SQL，实际需要根据字段类型调整
            print(f"ALTER TABLE {table_name} CHANGE COLUMN `{conv['original']}` `{conv['converted']}` {conv['type'].upper()};")
    print("\n... (其他表类似) ...\n")

if __name__ == '__main__':
    main()

