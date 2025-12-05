#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
DataCoordinator - 数据协调器

职责：
1. 解析依赖关系，构建依赖图
2. 计算执行顺序（拓扑排序）
3. 确保依赖满足后再执行
4. 构建执行上下文（传递依赖数据）
5. 处理失败和降级
"""

from typing import List, Dict, Any, Optional
from loguru import logger

from .provider_registry import ProviderRegistry
from .base_provider import ExecutionContext, Dependency


class DependencyGraph:
    """依赖图（用于拓扑排序）"""
    
    def __init__(self):
        self.nodes = {}  # {name: metadata}
        self.edges = {}  # {from: [to, ...]}
    
    def add_node(self, name: str, metadata):
        """添加节点"""
        self.nodes[name] = metadata
        if name not in self.edges:
            self.edges[name] = []
    
    def add_edge(self, from_node: str, to_node: str):
        """添加边（依赖关系）"""
        if from_node not in self.edges:
            self.edges[from_node] = []
        self.edges[from_node].append(to_node)
    
    def topological_sort(self) -> List[str]:
        """
        拓扑排序（计算执行顺序）
        
        Returns:
            Provider名称列表，按依赖顺序排列
        
        Raises:
            ValueError: 如果存在循环依赖
        """
        # Kahn算法
        in_degree = {node: 0 for node in self.nodes}
        
        for from_node, to_nodes in self.edges.items():
            for to_node in to_nodes:
                if to_node in in_degree:
                    in_degree[to_node] += 1
        
        # 入度为0的节点
        queue = [node for node, degree in in_degree.items() if degree == 0]
        result = []
        
        while queue:
            node = queue.pop(0)
            result.append(node)
            
            for neighbor in self.edges.get(node, []):
                if neighbor in in_degree:
                    in_degree[neighbor] -= 1
                    if in_degree[neighbor] == 0:
                        queue.append(neighbor)
        
        # 检查循环依赖
        if len(result) != len(self.nodes):
            raise ValueError("检测到循环依赖")
        
        return result


class DataCoordinator:
    """
    数据协调器
    
    职责：
    1. 解析依赖关系，构建依赖图
    2. 计算执行顺序（拓扑排序）
    3. 确保依赖满足后再执行
    4. 构建执行上下文（传递依赖数据）
    5. 处理失败和降级
    """
    
    def __init__(self, registry: ProviderRegistry, data_manager):
        """
        初始化协调器
        
        Args:
            registry: Provider注册表
            data_manager: DataManager实例
        """
        self.registry = registry
        self.data_manager = data_manager
        self._dependency_graph = None
        self._execution_order = None
    
    def build_dependency_graph(self) -> DependencyGraph:
        """
        构建依赖图
        
        Returns:
            DependencyGraph: 依赖图
        """
        graph = DependencyGraph()
        
        # 添加所有Provider节点
        for provider_name in self.registry.list_providers():
            metadata = self.registry.get_metadata(provider_name)
            graph.add_node(provider_name, metadata)
        
        # 添加依赖边
        for provider_name in self.registry.list_providers():
            metadata = self.registry.get_metadata(provider_name)
            
            for dep in metadata.dependencies:
                # from依赖Provider → to当前Provider
                graph.add_edge(dep.provider, provider_name)
        
        return graph
    
    def resolve_execution_order(self) -> List[str]:
        """
        计算执行顺序（拓扑排序）
        
        Returns:
            Provider名称列表，按依赖顺序排列
        """
        if not self._execution_order:
            self._dependency_graph = self.build_dependency_graph()
            self._execution_order = self._dependency_graph.topological_sort()
            
            logger.info(f"📋 Provider执行顺序: {' → '.join(self._execution_order)}")
        
        return self._execution_order
    
    async def renew_all_providers(self, end_date: str):
        """
        更新所有Provider（按依赖顺序）
        
        Args:
            end_date: 截止日期（YYYYMMDD）
        """
        order = self.resolve_execution_order()
        
        logger.info(f"🔄 开始更新所有Provider，截止日期: {end_date}")
        
        for provider_name in order:
            provider = self.registry.get(provider_name)
            
            if not provider:
                logger.warning(f"⚠️  Provider '{provider_name}' 未找到，跳过")
                continue
            
            # 构建执行上下文
            context = await self._build_context(provider_name, end_date)
            
            # 执行更新
            try:
                logger.info(f"▶️  更新 {provider_name}...")
                await provider.renew_all(end_date, context)
                logger.info(f"✅ {provider_name} 更新完成")
            except Exception as e:
                logger.error(f"❌ {provider_name} 更新失败: {e}")
                # TODO: 根据配置决定是否继续
                raise
    
    async def coordinate_update(self, data_type: str, end_date: str):
        """
        协调某个数据类型的更新
        
        自动处理依赖：
        1. 找到负责此数据类型的Provider
        2. 检查依赖是否满足
        3. 递归更新依赖（如果不满足）
        4. 构建执行上下文
        5. 执行更新
        
        Args:
            data_type: 数据类型（如 'adj_factor'）
            end_date: 截止日期
        """
        logger.info(f"🎯 请求更新数据类型: {data_type}")
        
        # 1. 找到负责的Provider
        providers = self.registry.get_providers_for(data_type)
        if not providers:
            raise ValueError(f"❌ 没有Provider支持数据类型: {data_type}")
        
        provider_name = providers[0]  # 使用第一个（主Provider）
        provider = self.registry.get(provider_name)
        
        # 2. 获取依赖
        metadata = self.registry.get_metadata(provider_name)
        
        # 3. 确保依赖满足
        for dep in metadata.dependencies:
            if dep.when == "before_renew":
                for dep_data_type in dep.data_types:
                    # 检查依赖数据是否可用
                    if not await self._is_data_available(dep_data_type, end_date):
                        logger.info(f"🔗 依赖数据 {dep_data_type} 不可用，先更新...")
                        # 递归更新依赖
                        await self.coordinate_update(dep_data_type, end_date)
        
        # 4. 构建执行上下文
        context = await self._build_context(provider_name, end_date)
        
        # 5. 执行更新
        try:
            logger.info(f"▶️  更新 {provider_name}.{data_type}")
            await provider.renew_data_type(data_type, end_date, context)
            logger.info(f"✅ {data_type} 更新完成")
        except Exception as e:
            logger.error(f"❌ {data_type} 更新失败: {e}")
            raise
    
    async def _build_context(
        self, 
        provider_name: str, 
        end_date: str
    ) -> ExecutionContext:
        """
        构建执行上下文
        
        Args:
            provider_name: Provider名称
            end_date: 截止日期
        
        Returns:
            ExecutionContext: 执行上下文
        """
        metadata = self.registry.get_metadata(provider_name)
        context = ExecutionContext(end_date=end_date)
        
        # 准备股票列表（如果需要）
        needs_stock_list = any(
            'stock_list' in dep.data_types or 'stock_kline' in dep.data_types
            for dep in metadata.dependencies
        )
        
        if needs_stock_list:
            # 从Tushare获取股票列表
            tushare = self.registry.get('tushare')
            if tushare:
                # TODO: 实现load_filtered_stock_list方法
                # stock_list = tushare.load_filtered_stock_list()
                # context.stock_list = stock_list
                pass
        
        # 传递依赖数据（如果需要）
        dependencies_data = {}
        for dep in metadata.dependencies:
            if dep.pass_data:
                # 从数据库加载依赖数据
                for data_type in dep.data_types:
                    data = await self._fetch_dependency_data(data_type, end_date)
                    if data:
                        dependencies_data[data_type] = data
        
        context.dependencies = dependencies_data if dependencies_data else None
        
        return context
    
    async def _is_data_available(self, data_type: str, end_date: str) -> bool:
        """
        检查数据是否可用（在数据库中）
        
        Args:
            data_type: 数据类型
            end_date: 截止日期
        
        Returns:
            bool: 数据是否可用
        """
        # TODO: 根据data_type映射到table_name
        # TODO: 查询数据库最新记录
        # TODO: 检查是否已更新到end_date
        
        # 简化实现：检查表是否有数据
        # 这里需要根据实际的数据类型映射来实现
        logger.debug(f"检查数据可用性: {data_type} (截止: {end_date})")
        
        # 暂时返回False，强制更新
        # 实际实现需要查询数据库
        return False
    
    async def _fetch_dependency_data(self, data_type: str, end_date: str) -> Any:
        """
        获取依赖数据
        
        Args:
            data_type: 数据类型
            end_date: 截止日期
        
        Returns:
            依赖数据
        """
        # TODO: 使用DataService查询
        # 这里需要根据实际的数据类型来实现
        logger.debug(f"获取依赖数据: {data_type} (截止: {end_date})")
        return None
    
    # ===== 查询API（可发现性）=====
    
    def list_all_data_types(self) -> List[str]:
        """
        列出所有支持的data_type
        
        Returns:
            List[str]: data_type列表
        """
        return self.registry.list_all_data_types()
    
    def list_all_providers(self) -> List[str]:
        """
        列出所有Provider
        
        Returns:
            List[str]: Provider名称列表
        """
        return self.registry.list_providers()
    
    def get_provider_capabilities(self, provider_name: str) -> Optional[Dict]:
        """
        查询Provider的能力
        
        Args:
            provider_name: Provider名称
        
        Returns:
            Dict: Provider能力信息
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
    
    def get_data_type_info(self, data_type: str) -> Optional[Dict]:
        """
        查询data_type的详细信息
        
        Args:
            data_type: 数据类型名称
        
        Returns:
            Dict: data_type信息
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
    
    def print_summary(self):
        """打印系统摘要（用于调试和文档）"""
        print("\n" + "="*60)
        print("📊 Data Provider 系统摘要")
        print("="*60)
        
        # 打印所有Provider
        print("\n🔌 已注册的 Providers:")
        for provider_name in self.list_all_providers():
            caps = self.get_provider_capabilities(provider_name)
            if caps:
                print(f"\n  {provider_name}:")
                print(f"    版本: {caps['version']}")
                print(f"    提供: {', '.join(caps['provides'])}")
                if caps['dependencies']:
                    print(f"    依赖: {len(caps['dependencies'])} 个")
        
        # 打印所有data_type
        print("\n📋 支持的 Data Types:")
        for data_type in sorted(self.list_all_data_types()):
            info = self.get_data_type_info(data_type)
            if info:
                providers = [p['name'] for p in info['providers']]
                print(f"  • {data_type:30s} → {', '.join(providers)}")
        
        print("\n" + "="*60 + "\n")

