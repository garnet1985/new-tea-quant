# 测试用例 — `infra.progress`

**模块：** `infra.progress`  
**版本：** `0.2.1`  
**本文件位置：** `__test__/`

---

## Scope

公开门面：创建树、更新叶子、结束节点、读取、清理；频道化 job 快照。

## 边界

**负责**

- `Progress.start`、`tick`、`finish`、`fail`、`cancel`、`pause`、`resume`、`clear`、`read`、`latest`
- `Progress.channel.path` / `write` / `read` / `clear`
- 有子节点时按 weight 汇总 ratio
- 包根只导出 `Progress`

**不负责**

- 业务模块何时调用、业务 channel 命名
- 界面怎么摆文字

**允许的测试类型（本目录）：** `api`

## 用例

| 用例 | 类型 | 入口 |
|------|------|------|
| 门面导出与方法存在 | api | `test_api.py` |
| 频道快照 write / read / clear | api | `test_api.py` |
| 频道拒绝非法 channel | api | `test_api.py` |
| 叶子计数写入 ratio，并打印 detail | api | `test_api.py` |
| tick 可以不打印日志 | api | `test_api.py` |
| 按子节点 id 更新，父节点按 weight 汇总 | api | `test_api.py` |
| 子节点失败不改变根的 status | api | `test_api.py` |
| 暂停和取消保持 ratio | api | `test_api.py` |
| 缺少节点、对父节点 tick、非法 id | api | `test_api.py` |
| latest 与 clear | api | `test_api.py` |
| 清理过期的已结束文件，保留运行中的文件 | api | `test_api.py` |
| 延迟写盘时 read 仍返回最新 ratio | api | `test_api.py` |
