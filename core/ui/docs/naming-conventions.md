# 前端源文件与符号命名约定（FED / React）

## 1. 文件与目录

- **目录、`.js` / `.jsx` / `.scss` 等源文件**：一律 **小写开头的驼峰**（`camelCase`），例如 `strategyListPage.js`、`appNavigation.js`、`mainLayout.js`。
- **不要用** 帕斯卡式文件名（`StrategyListPage.js`、`MainLayout.js`），避免与下述「类型/组件符号」混用。

### 1.1 用点号串联子类型（同一条业务线下的「角色」）

同一功能下可拆为多个文件时，用 **`.` 连接** 表达职责，**文件主体名仍为小写驼峰**：

- `strategy.js` — 主文件或聚合入口
- `strategy.test.js` — 测试
- `strategy.helper.js` — 与 `helper` 相关（亦常见 `setup.helpers.js` 这类「目录内共享」形式）
- `strategyWorkbench.js` — 子模块（如策略工作台单页，整词为驼峰的一段）

> 点号左侧优先表示 **业务/域**；右侧表示 **子角色**（`test`、`helper`、`config` 等），可按团队习惯在「单词」与「短词」间统一（例如 `strategyList.page.js` 与 `strategyListPage.js` 二选一，本仓库以 **合并成单一驼峰词** 的页面主文件为默认：`strategyListPage.js`）。

## 2. 源码中的标识符

- **类、TypeScript 接口/类型、枚举**：**PascalCase**（如 `class UserService`、`type StrategyRow`）。
- **React 函数组件的组件名**（在 `<Xxx />` 中使用）：**PascalCase**（如 `function StrategyListPage() { ... }`），与生态及 JSX 规则一致。
- 普通 **函数、变量、hook**：**camelCase**（如 `fetchStrategyList`、`getStrategyWorkbenchPath`）。
- 文件名使用 camelCase **不** 要求与组件名逐字相同：例如文件 `strategyListPage.js` 内仍导出 `function StrategyListPage()`，这是正常做法。

## 3. 样式

- **CSS/SCSS 的 class**：常用 **kebab-case** 或与 BEM 一致（如 `.strategy-list-page`、`.ntq-content`），与 `settings` / HTML 类名习惯一致，**不** 使用驼峰作类名。
- **与组件同目录的样式**：`strategyListPage.scss` 等，与 JS 同名的 `scss` 紧随模块；全局变量、入口在 `src/assets/scss/`。

## 4. 与本次约定关系

- 新代码按本节执行；历史文件中仍可能残留帕斯卡式文件名，可随改动逐步重命名，避免为改名而单开巨型 PR。

## 5. 修订

- 约定随项目演进可增补；变更宜在本文件更新并知会协作方。
