# Progress（`infra.progress`）

按节点 id 把进度写入文件。根节点和每一层 steps 使用同一种结构。界面、PHP 和 BFF 读取文件里已经算好的 ratio，不再自己加权。

一次任务一个根文件，路径是 userspace 临时目录下的 `progress/{根id}.json`。节点 id 在这个目录里唯一。外部每调用一次 tick，状态就更新一次；短时间内的多次更新会合并成一次写盘。读取接口立刻返回最新内容。

结果、机会列表和失败日志不放进进度文件。

## 适用场景

- 一次长时间任务需要告诉界面做到哪
- 任务只有一步，或下面还有多层步骤
- 多个任务同时跑，各自一份文件

## 模块依赖

- `infra.project_context`：定位 userspace 下的临时目录

## 设计初衷

各模块曾经各自写进度，界面要认多套字段。本模块只提供统一的进度文件。业务结果仍由各模块自己保存。

## 常见问题

**Q：百分比在哪里算？**  
A：写入时算好，放在每个节点的 ratio。0 到 1。有子节点时来自子节点的 weight；没有子节点时是 done / total。

**Q：怎么找到某一层的步骤？**  
A：tick、finish、fail 只接收节点 id，在文件里递归查找。

**Q：写盘失败会不会让任务停？**  
A：不会。找不到节点会报错，方便发现调用错误。

## 相关文档

- [快速开始](./QUICKSTART.md)
- [公开 API](./API.md)
- [术语表](./glossary.yaml)
- [架构](./docs/ARCHITECTURE.md)
- [设计](./docs/DESIGN.md)
- [测试用例](./__test__/TEST_CASES.md)
