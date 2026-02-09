"""
Core package marker.

存在目的：
- 让 `core` 作为顶层包可以被 `import core...` 正常导入；
- 便于 pytest / 运行时在项目根目录下直接通过绝对导入使用 core 下各模块。
"""

