## empty_reply
上一条回复无效：reply 不能为空，也不能用示例占位。请根据工具结果用中文回答用户，只输出 {"reply":"..."}。

## no_permission
不要只描述计划或征求许可。立刻调用 write_strategy_files 修改文件，再启动任务并读取报告，最后用结论 reply。

## zero_opportunity
机会数为 0：现在禁止向用户 reply，也不要问「要不要改」。立刻读取 strategy.py 与 settings.py，核对 indicators 与 hooks 字段：禁止 ma_ma20 这类臆造名；有 alias 只读 alias；无 alias 时 length=20 读 ma20；参数用 length 不用 window。修正后先 validate_strategy，再启动回测/扫描并读取报告，然后才能 reply。
