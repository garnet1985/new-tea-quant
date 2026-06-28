"""
Discovery Module - 文件和类发现工具

使用方式：
    from core.infra.discovery import Discovery
    
    # 文件操作（静态方法）
    path = Discovery.file.find_file(directory, filename)
    data = Discovery.file.load_json(path)
    
    # 批量发现（静态方法）
    files = Discovery.discover.files(directory, pattern)
    classes = Discovery.discover.subclasses(base_class, module_path)
"""

from .core.namespaces import FileNamespace, DiscoverNamespace, ClassDiscoveryNamespace


class Discovery:
    """Discovery模块统一入口"""
    
    # namespace实例（静态属性）
    file = FileNamespace()
    discover = DiscoverNamespace()
    class_discovery = ClassDiscoveryNamespace()