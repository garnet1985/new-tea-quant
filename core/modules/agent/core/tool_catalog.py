"""工具清单。执行函数在 core/tools，不放进 ToolSpec。"""

from __future__ import annotations

from typing import Any, Dict, List

from core.modules.agent.contracts import ToolSpec


def _object(properties: Dict[str, Any], required: List[str]) -> Dict[str, Any]:
    return {
        "type": "object",
        "properties": properties,
        "required": required,
        "additionalProperties": False,
    }


def _string(description: str) -> Dict[str, str]:
    return {"type": "string", "description": description}


_TOOLS: tuple[ToolSpec, ...] = (
    ToolSpec(
        name="create_strategy",
        description=(
            "从空模板新建一个策略。先检查目录名和是否已存在，再复制模板、启用并写入 meta.key。"
            "目录已存在时不要覆盖。不检查行情数据是否已下载。成功后仍是空模板，信号逻辑要另写。"
        ),
        parameters=_object(
            {
                "key": _string(
                    "策略目录名，同时写入 meta.key。每一段以字母开头，只含字母、数字、下划线。例如 macd_cross。"
                )
            },
            ["key"],
        ),
        implemented=True,
    ),
    ToolSpec(
        name="write_strategy_files",
        description=(
            "覆盖已有策略的 strategy.py 与 settings.py。目录必须已经存在，不会新建目录，也不写其他文件。"
            "写完后调用 validate_strategy。未通过校验不要回测。"
        ),
        parameters=_object(
            {
                "key": _string("已存在的策略目录名，例如 macd_cross"),
                "strategy_py": _string(
                    "strategy.py 全文。公开类继承 StrategyHooks，并实现 is_opportunity。"
                ),
                "settings_py": _string(
                    "settings.py 全文。必须有 settings 字典，meta.key 等于目录名，is_enabled 为 True。"
                ),
            },
            ["key", "strategy_py", "settings_py"],
        ),
        implemented=True,
    ),
    ToolSpec(
        name="validate_strategy",
        description=(
            "加载 strategy.py 和 settings.py。检查语法、meta.key 与目录名一致、is_enabled 为 True、"
            "公开类继承 StrategyHooks 并实现 is_opportunity。未通过则不要启动回测。不检查行情数据。"
        ),
        parameters=_object({"key": _string("策略目录名，例如 macd_cross")}, ["key"]),
        implemented=True,
    ),
    ToolSpec(
        name="start_enumerate",
        description=(
            "对已启用且通过校验的策略启动枚举，并立刻返回。不要等待跑完。"
            "回测区间用 settings 里的 start_date / end_date，不要在参数里传年数或股票数量。"
            "完成前不要编写机会次数。"
        ),
        parameters=_object(
            {"key": _string("已存在的策略目录名，例如 macd_cross")},
            ["key"],
        ),
        implemented=True,
    ),
    ToolSpec(
        name="start_price_factor",
        description=(
            "对已启用且通过校验的策略启动价格回测，并立刻返回。不要等待跑完。"
            "缺同指纹枚举产物时会先补跑枚举。区间用 settings，不要传年数或股票数量。"
            "完成前不要编写收益数字。"
        ),
        parameters=_object(
            {"key": _string("已存在的策略目录名，例如 macd_cross")},
            ["key"],
        ),
        implemented=True,
    ),
    ToolSpec(
        name="start_portfolio",
        description=(
            "对已启用且通过校验的策略启动资金模拟，并立刻返回。不要等待跑完。"
            "区间用 settings，不要传年数或股票数量。完成前不要编写收益数字。"
        ),
        parameters=_object(
            {"key": _string("已存在的策略目录名，例如 macd_cross")},
            ["key"],
        ),
        implemented=True,
    ),
    ToolSpec(
        name="start_simulate",
        description=(
            "依次启动枚举、价格回测、资金模拟，任一层失败即停，并立刻返回。不要等待跑完。"
            "区间用 settings，不要传年数或股票数量。完成前不要编写结果数字。"
        ),
        parameters=_object(
            {"key": _string("已存在的策略目录名，例如 macd_cross")},
            ["key"],
        ),
        implemented=True,
    ),
    ToolSpec(
        name="start_attribute_enumerate",
        description=(
            "启动枚举层归因，并立刻返回。须已有该层主 version。配置在 attribution.py。"
            "不要传参数以外的策略名。完成前不要编写归因结论。"
        ),
        parameters=_object(
            {"key": _string("已存在的策略目录名，例如 macd_cross")},
            ["key"],
        ),
        implemented=True,
    ),
    ToolSpec(
        name="start_attribute_price",
        description=(
            "启动价格层归因，并立刻返回。须已有该层主 version。配置在 attribution.py。"
            "完成前不要编写归因结论。"
        ),
        parameters=_object(
            {"key": _string("已存在的策略目录名，例如 macd_cross")},
            ["key"],
        ),
        implemented=True,
    ),
    ToolSpec(
        name="start_attribute_portfolio",
        description=(
            "启动资金层归因，并立刻返回。须已有该层主 version。配置在 attribution.py。"
            "完成前不要编写归因结论。"
        ),
        parameters=_object(
            {"key": _string("已存在的策略目录名，例如 macd_cross")},
            ["key"],
        ),
        implemented=True,
    ),
    ToolSpec(
        name="start_rolling",
        description=(
            "按策略目录里的 rolling.py 启动滚动对照，并立刻返回。完成前不要编写对照结论。"
        ),
        parameters=_object(
            {"key": _string("已存在的策略目录名，例如 macd_cross")},
            ["key"],
        ),
        implemented=True,
    ),
    ToolSpec(
        name="read_progress",
        description="按任务 id 读取进度摘要。状态不是 completed 时不要编写结果数字。",
        parameters=_object(
            {"task_id": _string("启动类工具返回的任务 id")},
            ["task_id"],
        ),
        implemented=True,
    ),
    ToolSpec(
        name="read_execution_report",
        description=(
            "读取枚举、价格或资金层的执行报告摘要。layer 为 enum、price 或 portfolio。"
            "version_id 可省略，省略时读该层最新的主版本。不要编造摘要里没有的数字。"
        ),
        parameters=_object(
            {
                "key": _string("策略目录名，例如 macd_cross"),
                "layer": _string("enum、price 或 portfolio"),
                "version_id": _string("版本号，例如 3。省略则读最新主版本"),
            },
            ["key", "layer"],
        ),
        implemented=True,
    ),
    ToolSpec(
        name="read_attribution_report",
        description=(
            "读取一层归因报告的结论和敏感度排名。layer 为 enum、price 或 portfolio。"
            "group_id 可省略，省略时读最新一组。改进时一次只改敏感度最高的一个参数。"
        ),
        parameters=_object(
            {
                "key": _string("策略目录名，例如 macd_cross"),
                "layer": _string("enum、price 或 portfolio"),
                "group_id": _string("归因组号。省略则读最新一组"),
            },
            ["key", "layer"],
        ),
        implemented=True,
    ),
)


class ToolCatalog:
    """已登记工具的只读清单。"""

    def list_tools(self) -> List[ToolSpec]:
        return list(_TOOLS)

    def get(self, name: str) -> ToolSpec | None:
        key = str(name or "").strip()
        for spec in _TOOLS:
            if spec.name == key:
                return spec
        return None
