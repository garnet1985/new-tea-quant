"""
Tag 系统：场景化标签计算与落库。

根契约：
- ``tag.py`` — Facade
- ``api.yaml`` / ``contracts.py`` / ``glossary.yaml`` / ``module_info.yaml``

UI：``core.bff.support.tag``（``TagCatalog`` / ``TagRunLauncher``）→ BFF ``tag_stack``。

场景目录：``userspace/extensions/tags/<path>/``，需 ``settings.py`` + ``tag.py``（``TagHooks``）。
"""
