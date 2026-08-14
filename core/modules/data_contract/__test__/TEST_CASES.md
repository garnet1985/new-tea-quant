# 测试用例 — `modules.data_contract`

**模块：** `modules.data_contract`  
**覆盖版本：** `0.6.0`

## Scope

验证门面 `ContractIssuer` 公开逻辑（对齐 `API.md`）。

| 文件 | 说明 |
|------|------|
| `test_api.py` | 公开 API：`ContractIssuer.issue`、包根仅导出 Issuer（`force_run`） |

## 实现测（不纳入公开索引）

| 文件 | 说明 |
|------|------|
| `../core/discovery/__test__/test_contract_issuer.py` | discover / get_contract / register |
| `../core/base/__test__/test_base_contract.py` | fill_in_data / until / to_df / clear 等 |
