"""
Core 版本与运行环境元信息。

**单一事实来源**：与本文件同目录的 ``system.json``（便于脚本/Updater 直接读取比对，无需 import Python）。
``SystemMeta`` 在运行时从该 JSON 加载；若文件缺失或损坏则回退到内置默认值并 ``warnings.warn``。
"""
from __future__ import annotations

import json
import warnings
from pathlib import Path
from typing import Any, Dict, List, Tuple

_DATA_PATH = Path(__file__).resolve().with_name("system.json")

_FALLBACK: Dict[str, Any] = {
    "version": "0.4.4",
    "release_date": "2026-08-12",
    "description": "版本发布",
    "python": {
        "minimum": [3, 9]
    },
            "new_features": [
        "标准化模块：所有模块统一格式，根目录下是同名模块入口层，另外还有contract（接口契约）来提供额外可能对外的API",
        "标准化模块：所有模块统一文档，一个api，一个readme，与原有的module info合并成完整的使用文档",
        "代码清理：删除logging（日志）模块 (技术债)",
        "代码清理：定义代码规范，并产出code style（代码风格）文档在根目录",
        "代码清理：所有模块之前穿透contract或API的引用都已经清理，现在模块间的引用都只在contract和API里暴露",
        "代码清理：将工具类模块（Utils）模块迁入infra下",
        "代码清理：将BFF和（用户界面）UI独立放入core的根目录下，不再是modules里的一部分",
        "代码清理：淘汰了老的job pipeline模块，职责分配到原来的业务模块中",
        "模块重构：重构BFF，取消了原来在模块中的launcher，将BFF专有逻辑迁移到BFF中。",
        "模块重构：将data cursor（数据游标）重置入data contract (数据契约)模块，并将时间推进功能从strategy（策略模块）挪入data contract（数据契约）模块",
        "模块重构：抽取了tag（标签模块）和strategy（策略模块）公共底层模块，独立成backtest engine（回测引擎）模块",
        "新模块：回测引擎（Backtest Engine或BE）新的回测调度执行器，是tag和strategy模块的基础，负责根据可用系统资源重组，执行，监控回测执行。Strategy和Tag模块的功能精简为提供任务，提供用户执行逻辑。",
        "为新的回测引擎加入一套完成性能测试基准和devcli的入口。",
        "新模块：加入trace模块，记录用户使用方式反馈，以便提供更好的服务（需用户同意），并且在UI上放置了随时开启或关闭trace的开关",
        "新模块：单机能力（machine capacity）模块，用来随时探测一些本机基础CPU和最大/可用内存的工具类",
        "策略模块（strategy）：暴露了新的on_pick_portfolio_member接口, 可以通过代码选择投资的机会了",
        "策略模块（strategy）：新的报告模式，兼容windows，UI和后端统一",
        "策略模块（strategy）：更新了第三层回测的名字，从capital allocation（资金分配）变成了portfolio（投资组合）",
        "策略模块（strategy）：将用户自定义钩子函数挂在了新的hooks基类上，这样用户的钩子函数不但可以参与底层子进程任务，也可以通过钩子参与主进程工作",
        "标签模块（tag）：新引入tag计算的进度表，可以让tag支持更好的增量计算",
        "标签模块（tag）：修改tag的其他三张表，去掉了一些冗余字段",
        "标签模块（tag）：将用户自定义钩子函数挂在了新的hooks基类上，这样用户的钩子函数不但可以参与底层子进程任务，也可以通过钩子参与主进程工作",
        "标签模块（tag）：现在支持全局标签模式，完全支持给无时序（比如股票分类），或者全局时序（比如GDP）目标动态添加标签",
        "在策略UI上增加策略文件快捷链接",
        "在策略UI上增加版本清除功能",
        "修复了requirements发生变化会强制安装和重新import数据的危险bug",
        "修复了UI界面上扫描页面的策略表里的调试策略链接到了旧页面的问题",
        "修复了UI界面上扫描页面如果扫描出的机会是0个会重置扫描状态的bug",
        "修复了UI界面上扫描页面如果严格模式并且不符合要求的时候仍然能执行扫描的bug",
        "修复了UI策略和标签进度显示和后端不一致的问题",
    ],
}


def _load_payload() -> Dict[str, Any]:
    if not _DATA_PATH.is_file():
        warnings.warn(f"缺少 {_DATA_PATH.name}，使用内置回退版本信息", UserWarning, stacklevel=2)
        return dict(_FALLBACK)
    try:
        raw = json.loads(_DATA_PATH.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - defensive
        warnings.warn(f"无法解析 {_DATA_PATH}: {exc}；使用内置回退", UserWarning, stacklevel=2)
        return dict(_FALLBACK)
    if not isinstance(raw, dict) or not isinstance(raw.get("version"), str):
        warnings.warn(f"{_DATA_PATH.name} 结构无效；使用内置回退", UserWarning, stacklevel=2)
        return dict(_FALLBACK)
    return raw


class SystemMeta:
    def __init__(self) -> None:
        data = _load_payload()
        self._version = str(data.get("version", _FALLBACK["version"]))
        self._release_date = str(data.get("release_date", _FALLBACK["release_date"]))
        self._description = str(data.get("description", _FALLBACK["description"]))

        py = data.get("python") if isinstance(data.get("python"), dict) else {}
        lo = py.get("minimum")
        if isinstance(lo, list) and len(lo) >= 2:
            self.python = {"minimum": [int(lo[0]), int(lo[1])]}
        else:
            self.python = dict(_FALLBACK["python"])

        nf = data.get("new_features")
        if isinstance(nf, list) and all(isinstance(x, str) for x in nf):
            self.new_features: List[str] = list(nf)
        else:
            self.new_features = list(_FALLBACK["new_features"])

        plan = data.get("update_plan") if isinstance(data.get("update_plan"), dict) else {}
        ms = plan.get("managed_scope")
        if not (isinstance(ms, list) and all(isinstance(x, str) for x in ms)):
            ms = data.get("managed_scope")
        if isinstance(ms, list) and all(isinstance(x, str) for x in ms):
            self.managed_scope: List[str] = list(ms)
        else:
            self.managed_scope = []

        ig = plan.get("update_ignored_paths")
        if not (isinstance(ig, list) and all(isinstance(x, str) for x in ig)):
            ig = data.get("update_ignored_paths")
        if isinstance(ig, list) and all(isinstance(x, str) for x in ig):
            self.update_ignored_paths: List[str] = list(ig)
        else:
            self.update_ignored_paths = []

    @property
    def version(self) -> str:
        return self._version

    @property
    def release_date(self) -> str:
        return self._release_date

    @property
    def description(self) -> str:
        return self._description

    def is_python_compatible(self, python_version: Tuple[int, int]) -> bool:
        lo = self.python["minimum"]
        return python_version >= (int(lo[0]), int(lo[1]))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self._version,
            "release_date": self._release_date,
            "description": self._description,
            "python": {"minimum": list(self.python["minimum"])},
            "new_features": list(self.new_features),
            "update_plan": {
                "managed_scope": list(self.managed_scope),
                "update_ignored_paths": list(self.update_ignored_paths),
            },
        }


# 模块级单例（避免各处重复构造）
system_meta = SystemMeta()


def get_version() -> str:
    return system_meta.version


def python_minimum() -> Tuple[int, int]:
    lo = system_meta.python["minimum"]
    return int(lo[0]), int(lo[1])
