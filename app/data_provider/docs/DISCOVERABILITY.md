# Data Type 可发现性设计

## 问题

**用户怎么知道每个Provider有哪些data_type（actions）？**

你说得对，我们需要一个机制让用户能够：
1. 查询所有可用的data_type
2. 查询某个Provider提供什么
3. 查询某个data_type的依赖关系
4. 生成文档

---

## 🎯 解决方案：多层次可发现性

### 方案1：运行时查询 API ⭐ 推荐

```python
# app/data_source/v2/data_coordinator.py

class DataCoordinator:
    """提供丰富的查询API"""
    
    def list_all_data_types(self) -> List[str]:
        """
        列出所有支持的data_type
        
        Returns:
            ['stock_list', 'stock_kline', 'adj_factor', ...]
        """
        return list(self.registry._data_type_index.keys())
    
    def list_all_providers(self) -> List[str]:
        """
        列出所有Provider
        
        Returns:
            ['tushare', 'akshare', 'wind', ...]
        """
        return self.registry.list_providers()
    
    def get_provider_capabilities(self, provider_name: str) -> Dict:
        """
        查询Provider的能力
        
        Args:
            provider_name: Provider名称
        
        Returns:
            {
                'name': 'tushare',
                'provides': ['stock_list', 'stock_kline', ...],
                'dependencies': [...]
            }
        """
        provider = self.registry.get(provider_name)
        if not provider:
            return None
        
        info = provider.get_provider_info()
        return {
            'name': info.name,
            'version': info.version,
            'provides': info.provides,
            'dependencies': [
                {
                    'provider': dep.provider,
                    'data_types': dep.data_types,
                    'required': dep.required,
                    'when': dep.when
                }
                for dep in info.dependencies
            ],
            'requires_auth': info.requires_auth
        }
    
    def get_data_type_info(self, data_type: str) -> Dict:
        """
        查询data_type的详细信息
        
        Args:
            data_type: 数据类型名称
        
        Returns:
            {
                'data_type': 'adj_factor',
                'providers': [
                    {
                        'name': 'akshare',
                        'priority': 1,
                        'dependencies': [...]
                    }
                ],
                'tables': ['adj_factor']
            }
        """
        providers = self.registry.get_providers_for(data_type)
        
        if not providers:
            return None
        
        info = {
            'data_type': data_type,
            'providers': []
        }
        
        for provider_name in providers:
            metadata = self.registry.get_metadata(provider_name)
            info['providers'].append({
                'name': provider_name,
                'dependencies': [
                    {
                        'provider': dep.provider,
                        'data_types': dep.data_types,
                        'required': dep.required
                    }
                    for dep in metadata.dependencies
                ]
            })
        
        return info
    
    def get_dependency_chain(self, data_type: str) -> List[str]:
        """
        查询完整的依赖链
        
        Args:
            data_type: 数据类型
        
        Returns:
            依赖链，从最底层到最顶层
            例如: ['stock_list', 'stock_kline', 'adj_factor']
        """
        chain = []
        visited = set()
        
        def _traverse(dt):
            if dt in visited:
                return
            visited.add(dt)
            
            # 获取依赖
            info = self.get_data_type_info(dt)
            if not info:
                return
            
            for provider_info in info['providers']:
                for dep in provider_info['dependencies']:
                    for dep_dt in dep['data_types']:
                        _traverse(dep_dt)
            
            chain.append(dt)
        
        _traverse(data_type)
        return chain
    
    def print_summary(self):
        """打印系统摘要（用于调试和文档）"""
        print("\n" + "="*60)
        print("📊 Data Source 系统摘要")
        print("="*60)
        
        # 打印所有Provider
        print("\n🔌 已注册的 Providers:")
        for provider_name in self.list_all_providers():
            caps = self.get_provider_capabilities(provider_name)
            print(f"\n  {provider_name}:")
            print(f"    版本: {caps['version']}")
            print(f"    提供: {', '.join(caps['provides'])}")
            if caps['dependencies']:
                print(f"    依赖: {len(caps['dependencies'])} 个")
        
        # 打印所有data_type
        print("\n📋 支持的 Data Types:")
        for data_type in sorted(self.list_all_data_types()):
            info = self.get_data_type_info(data_type)
            providers = [p['name'] for p in info['providers']]
            print(f"  • {data_type:30s} → {', '.join(providers)}")
        
        print("\n" + "="*60 + "\n")
```

---

### 使用示例：运行时查询

```python
# start.py 或 debug 脚本

async def explore_data_source():
    """探索Data Source系统"""
    
    # 初始化
    data_source = DataSourceManager(data_manager)
    coordinator = data_source.coordinator
    
    # ========== 查询1：列出所有Provider ==========
    print("📋 所有Provider:")
    providers = coordinator.list_all_providers()
    print(providers)
    # 输出: ['tushare', 'akshare']
    
    # ========== 查询2：查询Provider能力 ==========
    print("\n🔍 Tushare的能力:")
    caps = coordinator.get_provider_capabilities('tushare')
    print(f"提供: {caps['provides']}")
    print(f"依赖: {caps['dependencies']}")
    
    # ========== 查询3：列出所有data_type ==========
    print("\n📋 所有Data Types:")
    data_types = coordinator.list_all_data_types()
    print(data_types)
    # 输出: ['stock_list', 'stock_kline', 'adj_factor', ...]
    
    # ========== 查询4：查询data_type详情 ==========
    print("\n🔍 adj_factor的详情:")
    info = coordinator.get_data_type_info('adj_factor')
    print(f"Provider: {info['providers'][0]['name']}")
    print(f"依赖: {info['providers'][0]['dependencies']}")
    
    # ========== 查询5：查询依赖链 ==========
    print("\n🔗 adj_factor的依赖链:")
    chain = coordinator.get_dependency_chain('adj_factor')
    print(" → ".join(chain))
    # 输出: stock_list → stock_kline → adj_factor
    
    # ========== 查询6：打印完整摘要 ==========
    coordinator.print_summary()

# 运行
asyncio.run(explore_data_source())
```

---

### 输出示例

```
📋 所有Provider:
['tushare', 'akshare']

🔍 Tushare的能力:
提供: ['stock_list', 'stock_kline', 'corporate_finance', 'gdp', 'price_indexes', 'shibor', 'lpr', 'stock_index_indicator', 'stock_index_indicator_weight', 'industry_capital_flow']
依赖: []

📋 所有Data Types:
['stock_list', 'stock_kline', 'corporate_finance', 'adj_factor', 'gdp', 'price_indexes', 'shibor', 'lpr', 'stock_index_indicator', 'stock_index_indicator_weight', 'industry_capital_flow']

🔍 adj_factor的详情:
Provider: akshare
依赖: [{'provider': 'tushare', 'data_types': ['stock_kline'], 'required': True}]

🔗 adj_factor的依赖链:
stock_list → stock_kline → adj_factor

============================================================
📊 Data Source 系统摘要
============================================================

🔌 已注册的 Providers:

  tushare:
    版本: 1.0.0
    提供: stock_list, stock_kline, corporate_finance, gdp, price_indexes, shibor, lpr, stock_index_indicator, stock_index_indicator_weight, industry_capital_flow
    依赖: 0 个

  akshare:
    版本: 1.0.0
    提供: adj_factor
    依赖: 1 个

📋 支持的 Data Types:
  • adj_factor                       → akshare
  • corporate_finance                → tushare
  • gdp                              → tushare
  • industry_capital_flow            → tushare
  • lpr                              → tushare
  • price_indexes                    → tushare
  • shibor                           → tushare
  • stock_index_indicator            → tushare
  • stock_index_indicator_weight     → tushare
  • stock_kline                      → tushare
  • stock_list                       → tushare

============================================================
```

---

## 🎯 方案2：命令行工具

```python
# start.py 增加命令

import argparse

def parse_args():
    parser = argparse.ArgumentParser()
    
    # ... 其他命令 ...
    
    # 新增：查询命令
    parser.add_argument(
        '--list-providers',
        action='store_true',
        help='列出所有Provider'
    )
    
    parser.add_argument(
        '--list-data-types',
        action='store_true',
        help='列出所有Data Types'
    )
    
    parser.add_argument(
        '--info',
        type=str,
        metavar='DATA_TYPE',
        help='查询指定data_type的详细信息'
    )
    
    parser.add_argument(
        '--provider-info',
        type=str,
        metavar='PROVIDER',
        help='查询指定Provider的能力'
    )
    
    parser.add_argument(
        '--summary',
        action='store_true',
        help='打印系统摘要'
    )
    
    return parser.parse_args()

async def main():
    args = parse_args()
    app = App()
    coordinator = app.data_source.coordinator
    
    # 处理查询命令
    if args.list_providers:
        providers = coordinator.list_all_providers()
        print("📋 已注册的 Providers:")
        for p in providers:
            print(f"  • {p}")
        return
    
    if args.list_data_types:
        data_types = coordinator.list_all_data_types()
        print("📋 支持的 Data Types:")
        for dt in sorted(data_types):
            info = coordinator.get_data_type_info(dt)
            providers = [p['name'] for p in info['providers']]
            print(f"  • {dt:30s} → {', '.join(providers)}")
        return
    
    if args.info:
        info = coordinator.get_data_type_info(args.info)
        if not info:
            print(f"❌ Data Type '{args.info}' 不存在")
            return
        
        print(f"\n📊 Data Type: {info['data_type']}")
        for provider_info in info['providers']:
            print(f"\n  Provider: {provider_info['name']}")
            if provider_info['dependencies']:
                print("  依赖:")
                for dep in provider_info['dependencies']:
                    print(f"    • {dep['provider']}.{', '.join(dep['data_types'])}")
        return
    
    if args.provider_info:
        caps = coordinator.get_provider_capabilities(args.provider_info)
        if not caps:
            print(f"❌ Provider '{args.provider_info}' 不存在")
            return
        
        print(f"\n🔌 Provider: {caps['name']}")
        print(f"版本: {caps['version']}")
        print(f"认证: {'需要' if caps['requires_auth'] else '不需要'}")
        print(f"\n提供的 Data Types:")
        for dt in caps['provides']:
            print(f"  • {dt}")
        
        if caps['dependencies']:
            print(f"\n依赖:")
            for dep in caps['dependencies']:
                print(f"  • {dep['provider']}.{', '.join(dep['data_types'])}")
        return
    
    if args.summary:
        coordinator.print_summary()
        return
    
    # ... 其他命令处理 ...
```

### 使用示例

```bash
# 列出所有Provider
$ python start.py --list-providers
📋 已注册的 Providers:
  • tushare
  • akshare

# 列出所有Data Types
$ python start.py --list-data-types
📋 支持的 Data Types:
  • adj_factor                       → akshare
  • stock_kline                      → tushare
  • gdp                              → tushare
  ...

# 查询某个data_type
$ python start.py --info adj_factor
📊 Data Type: adj_factor
  Provider: akshare
  依赖:
    • tushare.stock_kline

# 查询某个Provider
$ python start.py --provider-info tushare
🔌 Provider: tushare
版本: 1.0.0
认证: 需要
提供的 Data Types:
  • stock_list
  • stock_kline
  • corporate_finance
  ...

# 打印系统摘要
$ python start.py --summary
```

---

## 🎯 方案3：静态文档生成

```python
# tools/generate_data_source_docs.py

class DataSourceDocGenerator:
    """自动生成Data Source文档"""
    
    def __init__(self, coordinator: DataCoordinator):
        self.coordinator = coordinator
    
    def generate_markdown(self) -> str:
        """生成Markdown文档"""
        doc = []
        
        # 标题
        doc.append("# Data Source 使用指南")
        doc.append("")
        doc.append("本文档自动生成，列出所有可用的数据源和数据类型。")
        doc.append("")
        
        # Provider列表
        doc.append("## 📋 Providers")
        doc.append("")
        
        for provider_name in self.coordinator.list_all_providers():
            caps = self.coordinator.get_provider_capabilities(provider_name)
            
            doc.append(f"### {caps['name']}")
            doc.append("")
            doc.append(f"**版本**: {caps['version']}")
            doc.append("")
            doc.append(f"**认证**: {'需要' if caps['requires_auth'] else '不需要'}")
            doc.append("")
            doc.append("**提供的数据类型**:")
            doc.append("")
            for dt in caps['provides']:
                doc.append(f"- `{dt}`")
            doc.append("")
            
            if caps['dependencies']:
                doc.append("**依赖**:")
                doc.append("")
                for dep in caps['dependencies']:
                    data_types_str = ', '.join(dep['data_types'])
                    doc.append(f"- {dep['provider']}: `{data_types_str}`")
                doc.append("")
        
        # Data Type列表
        doc.append("## 📊 Data Types")
        doc.append("")
        doc.append("| Data Type | Provider | 依赖 |")
        doc.append("|-----------|----------|------|")
        
        for data_type in sorted(self.coordinator.list_all_data_types()):
            info = self.coordinator.get_data_type_info(data_type)
            provider = info['providers'][0]['name']
            
            deps = []
            for dep in info['providers'][0]['dependencies']:
                deps.extend(dep['data_types'])
            
            deps_str = ', '.join(deps) if deps else '-'
            doc.append(f"| `{data_type}` | {provider} | {deps_str} |")
        
        doc.append("")
        
        # 使用示例
        doc.append("## 🚀 使用示例")
        doc.append("")
        doc.append("### 更新所有数据")
        doc.append("")
        doc.append("```python")
        doc.append("await data_source.renew_all(end_date='20250101')")
        doc.append("```")
        doc.append("")
        doc.append("### 更新指定数据类型")
        doc.append("")
        doc.append("```python")
        
        # 为每个data_type生成示例
        for data_type in sorted(self.coordinator.list_all_data_types())[:3]:
            doc.append(f"# 更新 {data_type}")
            doc.append(f"await data_source.renew_data_type('{data_type}', '20250101')")
            doc.append("")
        
        doc.append("```")
        doc.append("")
        
        return "\n".join(doc)
    
    def save_to_file(self, output_path: str):
        """保存到文件"""
        content = self.generate_markdown()
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✅ 文档已生成: {output_path}")

# 使用
async def generate_docs():
    app = App()
    coordinator = app.data_source.coordinator
    
    generator = DataSourceDocGenerator(coordinator)
    generator.save_to_file('docs/DATA_SOURCE_GUIDE.md')

# 在CI/CD中运行
asyncio.run(generate_docs())
```

---

## 🎯 方案4：配置文件（可选）

```yaml
# config/data_source_registry.yaml
# 这是一个可选的"注册表"文件，供用户参考

providers:
  tushare:
    description: "Tushare数据源，提供股票、宏观经济等数据"
    website: "https://tushare.pro"
    requires_auth: true
    provides:
      stock_list:
        description: "股票列表（含ST、退市等状态）"
        frequency: "daily"
        table: "stock_list"
      
      stock_kline:
        description: "股票日K线数据（前复权）"
        frequency: "daily"
        table: "stock_kline"
      
      corporate_finance:
        description: "企业财务数据（季报）"
        frequency: "quarterly"
        table: "corporate_finance"
      
      # ... 其他data_type
  
  akshare:
    description: "AKShare数据源，提供复权因子等数据"
    website: "https://www.akshare.xyz"
    requires_auth: false
    provides:
      adj_factor:
        description: "复权因子（用于计算前复权价格）"
        frequency: "daily"
        table: "adj_factor"
        dependencies:
          - provider: tushare
            data_types: [stock_kline]
            reason: "需要K线数据的日期范围"

# 使用方式：供用户查阅参考
# 运行时仍然以代码中的声明为准
```

---

## 🎯 方案5：交互式探索（IPython/Jupyter）

```python
# notebooks/explore_data_source.ipynb

from app.data_source.data_source_manager import DataSourceManager
from app.data_manager.data_manager import DataManager

# 初始化
dm = DataManager()
dm.initialize()
data_source = DataSourceManager(dm)
coordinator = data_source.coordinator

# ========== 交互式查询 ==========

# 列出所有Provider
coordinator.list_all_providers()

# 查询Provider能力
coordinator.get_provider_capabilities('tushare')

# 列出所有data_type
coordinator.list_all_data_types()

# 查询data_type详情
coordinator.get_data_type_info('adj_factor')

# 查询依赖链
coordinator.get_dependency_chain('adj_factor')

# 打印摘要
coordinator.print_summary()

# ========== 可视化依赖图 ==========
import networkx as nx
import matplotlib.pyplot as plt

def visualize_dependencies():
    G = nx.DiGraph()
    
    # 添加节点和边
    for data_type in coordinator.list_all_data_types():
        info = coordinator.get_data_type_info(data_type)
        
        for provider_info in info['providers']:
            for dep in provider_info['dependencies']:
                for dep_dt in dep['data_types']:
                    G.add_edge(dep_dt, data_type)
    
    # 绘制
    plt.figure(figsize=(12, 8))
    pos = nx.spring_layout(G)
    nx.draw(G, pos, with_labels=True, node_color='lightblue', 
            node_size=2000, font_size=10, arrows=True)
    plt.title("Data Type Dependency Graph")
    plt.show()

visualize_dependencies()
```

---

## 🎯 最佳实践：组合使用

### 开发阶段

```python
# 1. 运行时查询（快速探索）
coordinator.print_summary()

# 2. 命令行工具（CI/CD集成）
$ python start.py --summary

# 3. 交互式探索（深入分析）
# Jupyter Notebook
```

### 生产阶段

```python
# 1. 静态文档（用户手册）
docs/DATA_SOURCE_GUIDE.md

# 2. 配置文件（参考）
config/data_source_registry.yaml

# 3. 运行时查询（监控和调试）
coordinator.list_all_data_types()
```

---

## 🎯 总结

### 你的理解完全正确！

1. ✅ **Provider通过`provides`声明能力**
2. ✅ **Coordinator通过`when`等状态自动组合**
3. ✅ **用户需要知道有哪些data_type**

### 解决方案：多层次可发现性

| 方案 | 场景 | 优先级 |
|-----|------|--------|
| **运行时查询API** | 开发、调试、监控 | ⭐⭐⭐⭐⭐ |
| **命令行工具** | CI/CD、快速查看 | ⭐⭐⭐⭐ |
| **静态文档生成** | 用户手册、开源文档 | ⭐⭐⭐⭐ |
| **配置文件** | 参考、IDE提示 | ⭐⭐⭐ |
| **交互式探索** | 深入分析 | ⭐⭐⭐ |

### 推荐实施顺序

1. **Phase 1**: 实现运行时查询API（`list_all_data_types`等）
2. **Phase 2**: 添加命令行工具（`--list-data-types`等）
3. **Phase 3**: 自动生成文档（`generate_docs()`）
4. **Phase 4**: 可选的配置文件和可视化

### 核心思想

```
声明式能力 + 运行时自省 = 完全可发现！

用户无需记忆，随时查询！
```

---

**最后更新**: 2025-12-05  
**维护者**: @garnet

