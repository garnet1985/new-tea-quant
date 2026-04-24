# UI/BFF TODO

## 待办事项

- [ ] 实现 NTQ 升级机制（基于 `upgrade-design-draft.md`）
  - [ ] 统一升级状态落盘到 `userspace/.ntq`
  - [ ] 增加版本检查与升级任务 API（start/status/retry）
  - [ ] 引入双层 updater（Bootstrap + Versioned）
  - [ ] UI 增加“发现新版本/立即升级/升级进度”交互
  - [ ] 定义升级策略（auto/guided/reinit）并与 setup 协同

