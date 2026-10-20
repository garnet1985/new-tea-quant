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
            "覆盖已有策略的 strategy.py、settings.py 或 attribution.py。"
            "目录必须已经存在；至少提供一个文件正文。改了 strategy/settings 后调用 validate_strategy；"
            "只改 attribution 后可直接重跑归因。"
        ),
        parameters=_object(
            {
                "key": _string("已存在的策略目录名，例如 macd_cross"),
                "strategy_py": _string(
                    "strategy.py 全文。公开类继承 StrategyHooks，并实现 is_opportunity。可省略。"
                ),
                "settings_py": _string(
                    "settings.py 全文。必须有 settings 字典，meta.key 等于目录名，is_enabled 为 True。可省略。"
                ),
                "attribution_py": _string(
                    "attribution.py 全文。须含 attribution = { ... }。可省略。"
                ),
            },
            ["key"],
        ),
        implemented=True,
    ),
    ToolSpec(
        name="validate_strategy",
        description=(
            "加载 strategy.py 和 settings.py。检查语法、meta.key 能否标识本策略"
            "（等于目录名/叶名，或经发现解析到同一文件夹）、is_enabled 为 True、"
            "公开类继承 StrategyHooks 并实现 is_opportunity。未通过则不要启动回测。不检查行情数据。"
        ),
        parameters=_object(
            {"key": _string("策略 meta.key 或相对路径，例如 rsi_v1 或 demo/regression/rsi/rsi_v1_baseline")},
            ["key"],
        ),
        implemented=True,
    ),
    ToolSpec(
        name="start_enumerate",
        description=(
            "对已启用且通过校验的策略启动枚举，并立刻返回。不要等待跑完。"
            "回测区间用 settings 里的 start_date / end_date，不要在参数里传年数或股票数量。"
            "任务完成前不要给出机会数。"
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
            "任务完成前不要给出收益数字。"
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
            "区间用 settings，不要传年数或股票数量。任务完成前不要给出收益数字。"
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
            "区间用 settings，不要传年数或股票数量。任务完成前不要给出结果数字。"
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
            "启动枚举层归因，并立刻返回。须已有该层主 version；"
            "归因参数配置在该策略目录的 attribution.py 中，此处只需传当前策略的 key。"
            "任务完成前不要给出归因结论。"
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
            "启动价格层归因，并立刻返回。须已有该层主 version；"
            "归因参数配置在该策略目录的 attribution.py 中，此处只需传当前策略的 key。"
            "任务完成前不要给出归因结论。"
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
            "启动资金层归因，并立刻返回。须已有该层主 version；"
            "归因参数配置在该策略目录的 attribution.py 中，此处只需传当前策略的 key。"
            "任务完成前不要给出归因结论。"
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
            "按策略目录里的 rolling.py 启动滚动对照，并立刻返回。任务完成前不要给出对照结论。"
        ),
        parameters=_object(
            {"key": _string("已存在的策略目录名，例如 macd_cross")},
            ["key"],
        ),
        implemented=True,
    ),
    ToolSpec(
        name="start_scan",
        description=(
            "扫描该策略在当前交易日的机会，并立刻返回。任务完成前不要给出股票名单。"
        ),
        parameters=_object(
            {"key": _string("已存在的策略目录名，例如 macd_cross")},
            ["key"],
        ),
        implemented=True,
    ),
    ToolSpec(
        name="read_progress",
        description="按任务 id 读取进度摘要。任务状态不是 completed 时不要给出结果数字。",
        parameters=_object(
            {"task_id": _string("启动类工具返回的任务 id")},
            ["task_id"],
        ),
        implemented=True,
    ),
    ToolSpec(
        name="list_strategy_summaries",
        description=(
            "列出本机策略及最新执行报告摘要（默认资金层 portfolio）。"
            "用于客观陈述已有回测结果；禁止据此给投资建议或推荐「能赚钱」的策略。"
            "layer 可省略，为 enum、price 或 portfolio。"
        ),
        parameters=_object(
            {"layer": _string("enum、price 或 portfolio；省略则 portfolio")},
            [],
        ),
        implemented=True,
    ),
    ToolSpec(
        name="read_execution_report",
        description=(
            "读取枚举、价格或资金层的执行报告摘要。layer 为 enum、price 或 portfolio。"
            "version_id 可省略，省略时读该层最新的主版本。"
            "价格层摘要含分位点/收益桶/配置快照，总结时按 summarize_backtest_report 模板写。"
            "不要编造摘要里没有的数字。"
        ),
        parameters=_object(
            {
                "key": _string("策略 meta.key 或相对路径，例如 rsi_v1"),
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
    ToolSpec(
        name="read_scan_report",
        description=(
            "读取一次扫描的摘要和前几条机会。date 可省略，省略时读最新一天。"
            "不要补充名单里没有的股票。"
        ),
        parameters=_object(
            {
                "key": _string("策略目录名，例如 macd_cross"),
                "date": _string("扫描日，例如 20260101。省略则读最新一天"),
            },
            ["key"],
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
