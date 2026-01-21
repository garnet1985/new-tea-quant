from typing import Any, Dict, List

from loguru import logger

from core.modules.data_source.data_class.api_job import ApiJob


class DataSourceHandlerHelper:
    """
    DataSource Handler 侧的辅助方法
    """

    @staticmethod
    def build_api_jobs(apis: Dict[str, Any]) -> List[ApiJob]:
        """
        将 config 中的 apis 定义转换为 ApiJob 列表。

        约定（保持宽松，主要由 userspace config 决定）：
        - apis: {
            "<api_name>": {
                "provider_name": "tushare",
                "method": "get_xxx",
                "max_per_minute": 200,                      # 可选，限流信息（每分钟最大请求数）
                "depends_on": ["other_api1", "other_api2"], # 可选，字符串或字符串列表
                "params": {...},                            # 可选，请求参数
                "field_mapping": {...},                     # 可选，字段映射
                ... 其他自定义字段 ...
            },
            ...
          }

        封装规则（不做过多业务理解，只做统一包装）：
        - ApiJob.api_name        = key 名（即 api_name）
        - ApiJob.provider_name   = provider_name
        - ApiJob.method          = method
        - ApiJob.params          = params（默认为 {}）
        - ApiJob.depends_on      = 归一化后的依赖列表（List[str]）
        - ApiJob.rate_limit      = max_per_minute（缺省为一个安全默认值）
        - ApiJob.api_params      = 整个 api 定义（dict，保留原始配置）
        - ApiJob.job_id          = api_name（后续如需可扩展为更复杂规则）
        """
        jobs: List[ApiJob] = []
        default_rate_limit = 50

        if not apis:
            logger.warning(f"apis 为空，返回空列表: {apis}")
            return jobs

        if not isinstance(apis, dict):
            logger.warning(f"apis 应为 dict，当前类型为: {type(apis)}")
            return jobs

        for api_name, api_conf in apis.items():
            if not isinstance(api_conf, dict):
                logger.warning(f"api 配置必须是 dict，当前 {api_name} 类型为: {type(api_conf)}，已跳过")
                continue

            # 依赖关系
            depends_on = api_conf.get("depends_on", [])
            if isinstance(depends_on, str):
                depends_on = [depends_on]
            elif not isinstance(depends_on, list):
                depends_on = []

            # 限流信息：从 max_per_minute 读取
            max_per_minute = api_conf.get("max_per_minute")
            if max_per_minute is None:
                max_per_minute = default_rate_limit
            try:
                max_per_minute_int = int(max_per_minute)
            except (TypeError, ValueError):
                logger.warning(f"max_per_minute 非法，使用默认值 {default_rate_limit}，当前值: {max_per_minute}")
                max_per_minute_int = default_rate_limit

            # 请求参数
            params = api_conf.get("params") or {}
            if not isinstance(params, dict):
                logger.warning(f"params 应为 dict，当前 {api_name} 类型为: {type(params)}，使用空字典")
                params = {}

            # 构造 ApiJob 实例：一次性通过构造函数注入所有字段，便于检查与对比
            job = ApiJob(
                api_name=api_name,
                provider_name=api_conf.get("provider_name"),
                method=api_conf.get("method"),
                params=params,
                api_params=api_conf,
                depends_on=depends_on,
                rate_limit=max_per_minute_int,
                job_id=api_name,
            )

            jobs.append(job)

        return jobs