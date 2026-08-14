# 性能测试报告 — {{:mode_label}} · N{{:sample_size}} · {{:engine_dir}}

## 环境
- 跑测时间: {{:run_at}}
- 回测引擎 (BE): {{:be_version}}
- core: {{:core_version}}
- 相关模块: {{:dependencies}}
- 操作系统: {{:os}}
- CPU: {{:cpu}}
- 内存: {{:memory}}
- Python: {{:python}}
- 数据库类型: {{:engine_dir}} ({{:engine}})
- 数据库名称: {{:db_name}}

## 结果
- 运行模式: {{:mode_label}}
- 样本档: {{:sample_label}}
- 总执行时间（秒）: {{:wall_time}}
- 股票数: {{:entities}}
- 交易日数: {{:days}}
- 数据量（行）: {{:data_rows}}
- 处理速度（股票×交易日 / 秒）: {{:throughput}}
- 是否成功: {{:success_label}}

## 调度情况
{{:schedule_section}}

## 时间花在哪
{{:time_section}}

## 并行效果
- 并行效果: {{:parallelism}}
- 并行效率: {{:parallelism_efficiency}}
{{:notes_section}}
