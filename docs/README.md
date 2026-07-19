# daily_report 文档导航

本目录按文档用途组织。产品与架构文档描述当前基线；`reports/` 中的内容是阶段性快照，仅用于追溯当时的实现与验证结论。

## 当前基线

### 产品与体验

- [产品定义](product/product-definition.md)：产品定位、目标用户、核心价值、边界与成功标准。
- [UX 设计](product/ux-design.md)：用户故事、核心流程、信息架构、交互与视觉基线。
- [UX Prototype Specification（进行中）](product/ux-prototype-specification.md)：使用真实一天样本推进 Prototype、Review 与迭代。

### 技术架构

- [架构总览](architecture/overview.md)：桌面技术栈、运行链路、本地 API、数据源适配与隐私原则。
- [统一浏览器数据源](architecture/browser-data-source.md)：浏览历史、浏览器事件与 AI 提问的统一模型。
- [浏览器事件](architecture/browser-events.md)：事件类型、存储、接口与采集边界。
- [数据治理](architecture/data-governance.md)：基于 `entry_key` 的标注、选择与敏感信息治理。

## 工作资料

- [UX 原型阶段 Agent Prompt](prompts/ux-prototype-agent-prompt.md)：进入原型与 UX Review 阶段时使用的工作提示词。

## 历史阶段报告

### Phase 0

- [验收报告](reports/phase-0/acceptance.md)
- [Tauri + Vue + FastAPI 检查报告](reports/phase-0/tauri-fastapi-check.md)

### Phase 1

- [SourceAdapter 实施报告](reports/phase-1/source-adapter.md)

### Phase 2/3

- [浏览器事件实施报告](reports/phase-2-3/browser-events-implementation.md)
- [统一浏览器数据源实施前检查](reports/phase-2-3/unified-browser-precheck.md)
- [统一浏览器数据源实施报告](reports/phase-2-3/unified-browser-implementation.md)

## 维护约定

- 使用 kebab-case 文件名，并把新文档放入对应的用途目录。
- 新增、移动或废弃文档时同步更新本导航和仓库根目录的相关链接。
- 当前决策写入 `product/` 或 `architecture/`；一次性的阶段验证结果写入 `reports/`。
- 历史报告原则上只修正错字和失效链接，不随当前实现持续改写。
