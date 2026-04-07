"""
Data Source Handler `config.py` 配置模板（示例）
=================================================

本文件用于说明 `userspace/data_source/handlers/<name>/config.py` 中 `CONFIG` 字典的
**所有可配置项**、**可用值**、以及常见组合方式。

注意：
- 这里是“配置结构”的示例，不是框架自动加载的配置入口；真正生效的是每个 handler 目录下的 `config.py`。
- 具体字段名（如 date_format 的常量）在项目里一般引用 `core.utils.date.DateUtils`。

核心对象：
- `DataSourceConfig.from_dict()` 负责解析顶层字段（table/save_mode/renew/apis/...）
- `RenewConfig.from_dict()` 负责解析 renew 段（type/rolling/last_update_info/...）
- `ApiConfig.from_dict()` 负责解析 apis 段（provider_name/method/max_per_minute/...）
- `JobExecutionConfig.from_dict()` 负责解析 job_execution 段（list/key/keys/terms/...）

可用值（强校验）：
- save_mode: "unified" | "immediate" | "batch"
- renew.type: "incremental" | "rolling" | "refresh"
"""

from core.utils.date import DateUtils


CONFIG = {
    # =========================
    # 1) 必填：绑定表名
    # =========================
    # 该 handler 最终要写入的表名（通常是 core/tables/* 的 schema.name 对应的表）。
    "table": "sys_xxx",

    # =========================
    # 2) 必填：保存模式（写库时机）
    # =========================
    # "unified"  : 默认。执行完全部 bundles 后，在框架的统一保存阶段写库一次。
    # "immediate": 每个 bundle 完成后触发一次保存（需要 handler 在钩子里保存，并返回空 normalized_data 避免重复写）。
    # "batch"    : 累计 save_batch_size 个 bundle 后触发一次批量保存（同样需要 handler 钩子配合）。
    #
    # 经验：
    # - 全局数据（无 entity 维度，如 CPI/GDP/SHIBOR/LPR 等）→ 推荐 "unified"
    # - per-entity 且单次获取很重、且不希望一个慢任务阻塞整批 → 可用 "immediate"
    # - per-entity 且希望吞吐更高 → 常用 "batch" + save_batch_size
    "save_mode": "unified",  # unified | immediate | batch

    # save_mode = "batch" 或 "immediate" 时常配；框架会校验必须是 >0 的整数。
    # 默认值：50
    "save_batch_size": 100,

    # =========================
    # 3) 可选：忽略字段
    # =========================
    # ignore_fields 是“写入前的字段白名单/黑名单策略”中的黑名单部分：
    # - 用于在 schema 校验/写入时跳过某些字段（例如由 handler 注入、或不希望写入主表的维度字段）。
    # - 必须是 list[str]；未配置时默认为 []。
    #
    # 示例：
    # - index_klines: ["id","term"]（由 handler 注入）
    # - stock_list : ["is_active","last_update"]
    "ignore_fields": [],

    # =========================
    # 4) 必填：renew 段（更新策略）
    # =========================
    "renew": {
        # renew.type 必填：决定更新模式（强校验）
        #
        # - "refresh"     : 刷新模式（通常用于全量/条件刷新）；可选配 renew_if_over_days 做“过期才刷新”
        # - "incremental" : 增量模式（需要 last_update_info 用于定位增量边界）
        # - "rolling"     : 滚动窗口模式（需要 last_update_info + rolling）
        "type": "rolling",  # incremental | rolling | refresh

        # last_update_info：
        # - incremental / rolling 时必填
        # - refresh 时仅在配了 renew_if_over_days 时建议提供（用于 gate 查询 date_field）
        "last_update_info": {
            # 用于判断“最新更新到哪一天/哪月/哪季度”的字段名（表字段）
            "date_field": "date",

            # date_format：用于解释 date_field 的粒度。
            # 框架会把 day/month/quarter 归一化到内部 TermType：
            # - DateUtils.PERIOD_DAY     (或写 "day"/"date")
            # - DateUtils.PERIOD_MONTH   (或写 "month")
            # - DateUtils.PERIOD_QUARTER (或写 "quarter")
            # 也支持更细的 TermType 值（weekly/yearly 等），但需与你的数据结构一致。
            "date_format": DateUtils.PERIOD_DAY,
        },

        # rolling：仅 rolling 模式必填
        "rolling": {
            # unit 同 last_update_info.date_format（通常 day/month/quarter）
            "unit": DateUtils.PERIOD_MONTH,
            # length：窗口长度（>0 int），例如 12 表示滚动取近 12 个月
            "length": 12,
        },

        # renew_if_over_days（可选）：
        # - 仅当“距离上次更新超过 N 天”才刷新（常用于 refresh/incremental 限流）
        # - value: >0 int
        # - counting_field: 可选，用于指定“按哪个字段计算上次更新时间”（不配则按默认 gate 逻辑）
        "renew_if_over_days": {
            "value": 30,
            # "counting_field": "last_update",
        },

        # job_execution（可选，但决定是否 per-entity 执行）：
        # - 不配 job_execution：全局数据模式（通常 fetched_data 会落在 "_unified" bucket）
        # - 配 job_execution：per-entity 模式（例如按股票/指数列表分 bundle）
        "job_execution": {
            # list：实体列表来源（一般来自 dependencies/mapping 中的某个 key）
            # 例如 stock_klines 用 "stock_list"，index_klines 用 "index_list"
            "list": "stock_list",

            # key / keys 二选一（互斥，强校验）
            # key：单字段分组（常见：按 "id"）
            # keys：多字段分组（常见：按 ["id","term"]）
            #
            # key 示例：
            # "key": "id",
            #
            # keys 示例（配置 keys 时，terms 必填，不允许运行时推断）：
            "keys": ["id", "term"],
            "terms": ["daily", "weekly", "monthly"],

            # merge（可选）：多 key 分组时的“跨 term 合并”提示（例如 (id,term) 的任务最终合并到同一 id）
            "merge": {
                "by": "id",
            },
        },

        # data_merging（可选）：
        # 用于 normalize 阶段的合并策略（例如跨 API 合并时的 merge_by_key）。
        # 注意：实际使用时多在 handler / normalization_helper 里读取该字典。
        # 顶层也可以配置 merge_by_key（见顶层 merge_by_key），两处会做 fallback。
        "data_merging": {
            # "merge_by_key": "id",
        },

        # extra（可选）：透传给 handler 的自定义配置（框架不解释）
        "extra": {
            # "some_flag": True,
        },
    },

    # =========================
    # 5) 必填：apis 段（一个 handler 可配置多个 API）
    # =========================
    # apis 是 dict[api_name -> api_config]。
    # api_name（例如 "daily_basic" / "cpi_data"）是你定义的逻辑名，必须唯一、建议稳定可读。
    "apis": {
        "api_name_1": {
            # provider_name/method/max_per_minute 必填（强校验）
            "provider_name": "tushare",   # 如 tushare / akshare / eastmoney ...
            "method": "get_xxx",          # provider 内的方法名（由 provider 实现提供）
            "max_per_minute": 200,        # >0 int：限流（每分钟最大调用次数）

            # params_mapping（可选 dict[str,str]）：
            # - key：API 参数名（即 ApiJob.params 里的 key）
            # - value：实体字段名（来自 job_execution 的实体记录字段），用于把 entity_id 注入 API 参数
            #
            # 常见：{"ts_code": "id"}、{"index_code": "id"}、{"ts_code": "id", "term": "term"}
            "params_mapping": {
                "ts_code": "id",
            },

            # result_mapping（可选 dict[str,str]）：
            # - key：写入表/规范化后的字段名（通常与表 schema 字段一致）
            # - value：API 返回中的字段名（原始字段）
            "result_mapping": {
                "id": "ts_code",
                "date": "trade_date",
            },

            # params（可选 dict）：静态 API 参数（不随实体变化），会合并进 ApiJob.params
            # 例如 tushare 的 fields 字段筛选
            "params": {
                # "fields": "ts_code,trade_date,close",
            },
        },

        # 你可以再加更多 API；多 API 时，normalize 阶段通常需要合并/去重逻辑。
        "api_name_2": {
            "provider_name": "akshare",
            "method": "get_yyy",
            "max_per_minute": 80,
            "params_mapping": {
                "symbol": "id",
            },
            # result_mapping / params 可省略（默认空字典）
        },
    },

    # =========================
    # 6) 可选：顶层合并与运行参数
    # =========================
    # merge_by_key（可选 str）：顶层合并键（normalize 阶段可能会 fallback 到这里）
    "merge_by_key": None,

    # default_date_range（可选）：当调用方未提供 start_date/end_date 时，框架按该范围补全（仅做“合理默认”，不访问 DB）
    # 支持结构：{"years": N}，N<=0 会 fallback 到 1。
    "default_date_range": {
        "years": 1,
    },

    # is_dry_run（可选 bool）：仅用于框架/handler 逻辑分支（例如不写库、只打印），默认 False。
    "is_dry_run": False,

    # needs_stock_grouping（可选 bool）：一些 handler 会用它决定是否需要按股票分组处理；框架仅透传，默认 None。
    "needs_stock_grouping": None,
}

