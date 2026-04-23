# 页面文档：`settings.html`

## 这个页面是干什么的？
全局运行配置中心（当前仅开放 DB Config section）。

## 页面目的与用户价值
- 把高频且必要的全局配置放到可视化入口，减少手改配置文件。
- 为 setup 完成后的日常维护提供稳定入口。

## 页面功能描述
- section 化页面结构（为后续扩展预留）。
- 当前已实现 DB Config：
  - 数据库类型
  - Host
  - Port
  - Database Name
  - User
  - Password
  - 测试连接按钮（占位）
  - 保存配置按钮（占位）
- 其他 section 以 placeholder 形式保留信息架构。

## 页面假设与 Placeholder
- 纯前端原型，不调用 BFF/API。
- 测试连接与保存不落后端，仅演示交互。
- 配置合法性校验仅做基础占位，真实规则待 API 设计阶段定义。
