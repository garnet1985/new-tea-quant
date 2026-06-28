"""ModuleDiscovery 单元测试。"""
from core.infra.discovery.core.module_discovery import ModuleDiscovery
from core.infra.project_context.core.path_manager import PathManager



def test_discover_objects():
    discovery = ModuleDiscovery()
    schemas = discovery.discover_objects(
        base_module_path="userspace.extensions.data_source.handlers",
        object_name="SCHEMA",
        module_pattern="userspace.extensions.data_source.handlers.{name}.schema",
    )
    assert isinstance(schemas, dict)
    for schema in schemas.values():
        if hasattr(schema, "name"):
            assert isinstance(schema.name, str)


def test_discover_modules_by_path():
    discovery = ModuleDiscovery()
    handlers_path = PathManager.get_data_source_handlers_directory()
    modules = discovery.discover_modules_by_path(
        base_path=handlers_path,
        module_pattern="userspace.extensions.data_source.handlers.{name}",
        object_name=None,
    )
    assert isinstance(modules, dict)
