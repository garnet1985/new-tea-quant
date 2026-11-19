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


def _boolean(description: str) -> Dict[str, str]:
    return {"type": "boolean", "description": description}


def _integer(description: str) -> Dict[str, str]:
    return {"type": "integer", "description": description}


def _array(item_schema: Dict[str, Any], description: str = "") -> Dict[str, Any]:
    out: Dict[str, Any] = {"type": "array", "items": item_schema}
    if description:
        out["description"] = description
    return out


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
            "缺同指纹机会盘点产物时会先补跑机会盘点。区间用 settings，不要传年数或股票数量。"
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
            "启动机会盘点层归因，并立刻返回。须已有该层主 version；"
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
            "价格层摘要含分位点/收益桶/配置快照；总结时 present 可套 scenario=backtest_price。"
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
    ToolSpec(
        name="create_tag",
        description=(
            "从空模板新建一个标签场景。先检查目录名和是否已存在，再复制模板、启用并写入 meta.key。"
            "目录已存在时不要覆盖。成功后仍是空模板，打标逻辑要另写。"
        ),
        parameters=_object(
            {
                "key": _string(
                    "标签相对路径，同时作为目录名；meta.key 写叶名。"
                    "每一段以字母开头，只含字母、数字、下划线。例如 market_cap_tier 或 demo/rsi_band。"
                )
            },
            ["key"],
        ),
        implemented=True,
    ),
    ToolSpec(
        name="write_tag_files",
        description=(
            "覆盖已有标签的 tag.py 或 settings.py。"
            "目录必须已经存在；至少提供一个文件正文。改完后调用 validate_tag。"
        ),
        parameters=_object(
            {
                "key": _string("已存在的标签相对路径，例如 market_cap_tier"),
                "tag_py": _string(
                    "tag.py 全文。公开类继承 TagHooks，并实现 calculate_tag。可省略。"
                ),
                "settings_py": _string(
                    "settings.py 全文。必须有 settings 字典，含 meta.key、tag_definitions，"
                    "is_enabled 为 True。可省略。"
                ),
            },
            ["key"],
        ),
        implemented=True,
    ),
    ToolSpec(
        name="validate_tag",
        description=(
            "加载 tag.py 和 settings.py。检查语法、meta.key、is_enabled、"
            "tag_definitions、公开类继承 TagHooks 并实现 calculate_tag。"
            "未通过则不要启动打标。"
        ),
        parameters=_object(
            {"key": _string("标签 meta.key 或相对路径，例如 market_cap_tier")},
            ["key"],
        ),
        implemented=True,
    ),
    ToolSpec(
        name="start_tag",
        description=(
            "对已启用且通过校验的标签启动计算，并立刻返回。不要等待跑完。"
            "区间与更新模式用 settings（默认 incremental）。任务完成前不要给出写入条数。"
        ),
        parameters=_object(
            {"key": _string("已存在的标签相对路径或 meta.key")},
            ["key"],
        ),
        implemented=True,
    ),
    ToolSpec(
        name="list_tag_summaries",
        description=(
            "列出本机标签及最新性能报告摘要。"
            "用于客观陈述已算好的标签；不要据此给投资建议。"
        ),
        parameters=_object({}, []),
        implemented=True,
    ),
    ToolSpec(
        name="read_tag_report",
        description=(
            "读取标签性能报告摘要。version_id 可省略，省略时读最新版本。"
            "不要编造摘要里没有的数字。"
        ),
        parameters=_object(
            {
                "key": _string("标签 meta.key 或相对路径"),
                "version_id": _string("版本号，例如 3。省略则读最新"),
            },
            ["key"],
        ),
        implemented=True,
    ),
    # --- data 底层工具链（少用；供其它工具/建扩展表探查）---
    ToolSpec(
        name="list_data_tables",
        description=(
            "列出已注册逻辑表名。owner=all|sys|cust。"
            "只读；写系统表结构前须警告用户并确认，且不要改 core/tables。"
        ),
        parameters=_object(
            {"owner": _string("过滤：all（默认）/ sys / cust")},
            [],
        ),
        implemented=True,
    ),
    ToolSpec(
        name="describe_data_table",
        description=(
            "只读描述一张已注册表的字段摘要。"
            "对 sys_* 仅可查看；结构性变更须警告+确认，且不得写入 core/tables。"
        ),
        parameters=_object(
            {"table_name": _string("逻辑表名，例如 sys_data_stock_list 或 cust_data_my_signals")},
            ["table_name"],
        ),
        implemented=True,
    ),
    ToolSpec(
        name="list_data_contract_keys",
        description="列出可用 data_key，供策略/标签 settings.data.base 选用。只读。",
        parameters=_object({}, []),
        implemented=True,
    ),
    ToolSpec(
        name="list_data_sources",
        description="列出已启用数据源及其绑定表（renew 目标）。只读。",
        parameters=_object({}, []),
        implemented=True,
    ),
    ToolSpec(
        name="check_data_freshness",
        description="读取本机数据结束日/新鲜度摘要。只读；不要编造日期。",
        parameters=_object({}, []),
        implemented=True,
    ),
    ToolSpec(
        name="create_table",
        description=(
            "在 userspace/extensions/tables 从空模板新建用户表骨架。"
            "表名须 cust_{kind}_主题；禁止写入 core/tables 或使用 sys_。"
            "目录已存在时不要覆盖。"
        ),
        parameters=_object(
            {
                "key": _string(
                    "表目录相对路径，例如 my_signals 或 demo/signals。"
                    "每段以字母开头，只含字母、数字、下划线。"
                ),
                "kind": _string("表种类：data（默认）/ map / cache / tmp / meta"),
                "table_name": _string(
                    "可选。schema.name，须 cust_{kind}_主题；省略则按目录叶名生成"
                ),
            },
            ["key"],
        ),
        implemented=True,
    ),
    ToolSpec(
        name="write_table_files",
        description=(
            "覆盖已有 userspace 表的 schema.py 或 model.py。"
            "name 必须是 cust_*；改完后调用 validate_table。"
        ),
        parameters=_object(
            {
                "key": _string("已存在的表目录相对路径"),
                "schema_py": _string("schema.py 全文。须含 schema 字典。可省略。"),
                "model_py": _string("model.py 全文。公开类继承 DbBaseModel。可省略。"),
            },
            ["key"],
        ),
        implemented=True,
    ),
    ToolSpec(
        name="validate_table",
        description=(
            "校验 userspace 表的 schema/model，并尝试注册到 DataManager。"
            "未通过则不要 ensure_physical_table。"
        ),
        parameters=_object(
            {"key": _string("表目录相对路径，例如 my_signals")},
            ["key"],
        ),
        implemented=True,
    ),
    ToolSpec(
        name="ensure_physical_table",
        description=(
            "对已通过校验的 cust_* 用户表调用 create_table() 确保物理表存在。"
            "系统表（sys_* / core/tables）一律拒绝。"
        ),
        parameters=_object(
            {"key": _string("表目录相对路径")},
            ["key"],
        ),
        implemented=True,
    ),
    ToolSpec(
        name="create_data_source",
        description=(
            "在 userspace/extensions/data_source/handlers 从空模板新建 handler 骨架。"
            "目录已存在时不要覆盖；不会自动改 mapping.py。"
        ),
        parameters=_object(
            {
                "key": _string(
                    "handler 目录相对路径，例如 my_src 或 demo/my_src。"
                    "每段以字母开头，只含字母、数字、下划线。"
                ),
                "hooks_class_name": _string(
                    "可选。DataSourceHooks 子类名；省略则按目录叶名生成 XxxHooks"
                ),
            },
            ["key"],
        ),
        implemented=True,
    ),
    ToolSpec(
        name="write_data_source_files",
        description=(
            "覆盖已有 userspace handler 的 handler.py 或 settings.py。"
            "settings 须定义 settings={...}；改完后 register_data_source（若未登记）再 validate_data_source。"
        ),
        parameters=_object(
            {
                "key": _string("已存在的 handler 目录相对路径"),
                "handler_py": _string("handler.py 全文。须继承 DataSourceHooks。可省略。"),
                "settings_py": _string("settings.py 全文。须含 settings 字典。可省略。"),
            },
            ["key"],
        ),
        implemented=True,
    ),
    ToolSpec(
        name="register_data_source",
        description=(
            "把数据源写入 mapping.py 的 DATA_SOURCES（扁平 key）。"
            "handler 形如 my_src.MySrcHooks；嵌套目录用点分路径。"
        ),
        parameters=_object(
            {
                "key": _string("mapping 扁平 key，例如 my_src（不要斜杠）"),
                "handler": _string("模块.类名，例如 my_src.MySrcHooks"),
                "is_enabled": _boolean("是否启用，默认 true"),
                "depends_on": _array(
                    _string("依赖的 mapping key 或保留字"),
                    "依赖列表，可为其他数据源 key 或 latest_completed_trading_date",
                ),
                "weight": _integer("越大越先执行；可省略"),
            },
            ["key", "handler"],
        ),
        implemented=True,
    ),
    ToolSpec(
        name="validate_data_source",
        description=(
            "按 mapping key 校验 settings、handler 类与绑定表是否已注册。"
            "不执行 renew；未通过则不要拉取。"
        ),
        parameters=_object(
            {"key": _string("mapping 扁平 key，例如 my_src")},
            ["key"],
        ),
        implemented=True,
    ),
)


def _builtin_names() -> frozenset[str]:
    return frozenset(spec.name for spec in _TOOLS)


class ToolCatalog:
    """已登记工具的只读清单（内置 + userspace 新增）。"""

    def list_tools(self) -> List[ToolSpec]:
        from core.modules.agent.core.code.userspace.tools import list_userspace_tool_specs

        extra = list_userspace_tool_specs(builtin_names=_builtin_names())
        return list(_TOOLS) + extra

    def get(self, name: str) -> ToolSpec | None:
        key = str(name or "").strip()
        for spec in _TOOLS:
            if spec.name == key:
                return spec
        from core.modules.agent.core.code.userspace.tools import list_userspace_tool_specs

        for spec in list_userspace_tool_specs(builtin_names=_builtin_names()):
            if spec.name == key:
                return spec
        return None

    def builtin_names(self) -> frozenset[str]:
        return _builtin_names()
