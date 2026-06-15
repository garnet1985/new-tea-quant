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
    "version": "0.4.1",
    "release_date": "2026-06-15",
    "description": "版本发布",
    "python": {"minimum": [3, 9]},
        "new_features": [
        "重大更新：增加策略回测report里的单股K线的点击界面，能够打开单个股票查询详细机会和交易回测点位",
        "重大更新：重建回测的UI，将三层回测变成三个单独页面而不再集中在一页上，提升了用户体验并且减小了UI渲染压力",
        "重大更新：新增加了3组共9个层层递进的演示策略来帮助理解框架和概念（注意：回测结果仅供参考，不是任何投资建议）",
        "(破坏性改动)将策略 settings 的一些信息字段收入meta中, 顶层只留is enabled字段；",
        "(破坏性改动)改动了data.json, 重命名了数据截断日期为 as of latest completed date",
        "(破坏性改动)所有k线的最高最低价从highest和lowest变成high和low",
        "(破坏性改动)对公司财务表加入了披露日期的列",
        "(破坏性改动)将K线的数据契约从一个按照周期分成了3个，补上了STOCK_INDICATORS_DAILY的数据契约",
        "新增加了个股资金流向数据表",
        "让复权因子可以根据data.json的配置先行导入可用的数据，大大降低了更新的时间",
        "重新定义了复权因子的存储结构和计算方式，使复权因子能够累加而不是刷新式更新。增加了复权因子链式检查以确保实效性。",
        "策略 settings 加入display name作为展示名称",
        "新增加命令行和UI的策略导入和导出功能",
        "修复了UI上的回测缓存有的时候会取错的bug",
        "修复了UI上有的时候回测报告会显示无效数据的bug",
        "修复了回测进度完成后会马上返回一份report然后又被另一个专门拿report的API覆盖的bug",
        "修复了回测进度只管回测股票进度的bug，现在整个回测进度由加载数据，分发任务，执行计算和总结结果4个部分构成",
        "修复了market profile忘了加入T+1交易的逻辑",
        "修复了价格回测在遇到跌停无法卖出导致交易最终无法平仓的bug",
        "修复策略报告 K 线 tooltip 将 dataIndex 误显示为开盘价的问题",
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
