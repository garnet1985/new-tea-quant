"""Slice-based调度文件夹

基于日期切片调度回测的模式。

特点：
- 读算分离（Reader多进程 + Compute单进程）
- 逐日期切片推进
- Strategy calendar_sliced默认模式
"""