"""Tag engines 共用层（跨 per_entity / global / non_time_series）。

本包:
- tag_settings / hooks / data_class: 契约与配置
- services: tag_value flush / report buffer
- calc_window / prior_values: 计算窗与增量暖启动

仅 entity_based↔slice_based 共用的 BE 编排（job_payload / pipeline_hooks）
留在 ``engines/per_entity/shared``。
"""
