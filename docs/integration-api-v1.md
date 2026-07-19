# Workbench Integration API V1

`daily_report` 提供一个独立、只读、默认关闭的本地 HTTP Provider, 供 Workbench 等本机消费者读取报告摘要. 该边界不属于 Desktop RPC, 不会自动随现有 API、采集器或桌面 UI 启动.

## 激活与停止

生产 Provider 仅在 `--enabled true` 时启动. 缺少参数或传入 `--enabled false` 会静默退出, 不创建 socket、线程、timer、watcher 或额外日志. Bearer Secret 只从指定环境变量读取, 默认引用名为 `DAILY_REPORT_INTEGRATION_TOKEN`; 不支持把 Secret 作为 CLI 参数传入.

```powershell
daily-report integration serve --enabled true --host 127.0.0.1 --port 8766
```

默认 Base URL 为 `http://127.0.0.1:8766`. 只允许显式绑定 `127.0.0.1` 或 `::1`; `0.0.0.0`、`::`、主机名和局域网地址都会在监听前被拒绝. 使用 `Ctrl+C` 停止, Windows 进程组也支持 `Ctrl+Break` 优雅停止.

Provider 启动、Secret 加载、数据库只读投影或端口绑定失败只会让该独立命令退出, 不会改变 daily_report 核心 API、采集器、报告生成、文件输出或桌面 UI 的健康状态.

## 鉴权

全部 V1 Endpoint 都要求 Bearer Secret. 缺少凭据返回 `401`, 错误凭据返回 `403`. Secret 不进入响应、日志、Revision、ETag 或 readiness 输出. `/api/health` 等既有 API 的行为和鉴权边界未改变.

## Endpoint

Provider 只暴露以下 `GET` 操作, 不自动补斜杠, 不提供重定向或写入方法:

- `GET /api/integration/v1/capabilities`
- `GET /api/integration/v1/daily/{YYYY-MM-DD}`
- `GET /api/integration/v1/range?start={YYYY-MM-DD}&end={YYYY-MM-DD}&limit={1..90}`
- `GET /api/integration/v1/range?...&afterRevision={opaque-revision}`

日期采用严格 Gregorian `YYYY-MM-DD`, 范围为 `0001-01-01` 到 `9999-12-31`. Range 首尾均包含, 最多 90 天; `limit` 为 1 到 90. 重复、缺失、未知或类型错误的参数返回安全的 `422` envelope.

## V1 Schema

Capabilities 固定声明 V1 和只读操作:

```json
{
  "ok": true,
  "data": {
    "schemaVersion": 1,
    "currentRevision": "opaque-capability-revision",
    "operations": ["daily", "range"]
  }
}
```

Daily 返回特定日期的稳定摘要. 没有报告不是错误, `report` 为 `null`:

```json
{
  "ok": true,
  "data": {
    "schemaVersion": 1,
    "meta": {
      "revision": "opaque-resource-revision",
      "generatedAt": "2026-07-18T00:00:00.000Z"
    },
    "freshness": {
      "sourceUpdatedAt": "2026-07-17T23:59:00.000Z"
    },
    "report": {
      "date": "2026-07-18",
      "reportId": "report-7",
      "summary": "Bounded provider-owned summary"
    }
  }
}
```

Range 按日期严格升序返回, 从 `start` 起最多生成 `limit` 项. 空白日期显式返回 `report: null`; 不会伪造报告. 非空项只包含 `reportId` 和 `summary`, 不包含完整正文.

```json
{
  "ok": true,
  "data": {
    "schemaVersion": 1,
    "meta": {
      "revision": "opaque-resource-revision",
      "generatedAt": "2026-07-18T00:00:00.000Z"
    },
    "items": [
      {
        "date": "2026-07-17",
        "report": null
      },
      {
        "date": "2026-07-18",
        "report": {
          "reportId": "report-7",
          "summary": "Bounded provider-owned summary"
        }
      }
    ]
  }
}
```

`reportId` 长度为 1 到 256, `summary` 可以为 `null` 且最长 16384 字符. 全部 instant 使用 UTC ISO 8601 毫秒格式和 `Z` 后缀. `generatedAt` 使用资源日期的 UTC 起点, 因此同一公开表示在进程重启后保持确定性. 单个响应不超过 2 MiB.

可控错误使用统一安全结构, 不包含堆栈、数据库路径、私有内容或内部异常文本:

```json
{
  "ok": false,
  "error": {
    "code": "validation_error",
    "message": "Invalid request parameters."
  }
}
```

## Revision 与 HTTP Cache

Revision 和 ETag 都是不透明字符串, Consumer 只能比较是否相等, 不应解析格式. 它们由规范化后的公开字段生成, 不包含 JSON 字段顺序、Secret、绝对路径、PID、启动时间或其他内部数据.

Daily validator 按日期隔离; Range validator 按 `start`、`end` 和 `limit` 组合隔离. 公开内容不变时 ETag 稳定, 匹配 `If-None-Match` 返回无 body 的 `304` 和当前 ETag. validator 不匹配时返回完整 `200`. 只有 `afterRevision` 而没有 `If-None-Match` 的首次 Range 请求始终返回 `200`.

Capabilities 可缓存 24 小时. V1 兼容性语义变化时必须更新 `currentRevision`.

## 数据所有权与只读边界

报告摘要由 daily_report 拥有. 历史报告没有结构化摘要时, Provider 在 daily_report 内执行确定性、长度受限的 Markdown 兼容转换; 该转换不调用 LLM. 无可靠摘要时返回 `null`, 不进行推断或虚构.

生产 Projection 使用 SQLite `mode=ro` 和 `query_only`, 只查询最新报告的 `id`、`date`、`report_markdown`、`created_at` 和 `updated_at`. 它不调用报告生成器、`ReportService`、`OverviewService` 或任何写入方法, 不执行 schema 初始化或 migration, 也不读取 `prompt_text`、`material_snapshot_json`、原始事件或敏感材料.

`POST /api/desktop/{method}` 是桌面 UI 的内部 RPC, 不是 Workbench 公共 API, 不提供兼容性保证. Workbench 只能依赖本页列出的版本化契约.

## Schema Version 升级规则

V1 可以增加 Consumer 可安全忽略的可选字段. 改变必需字段名称、类型、含义或删除字段属于破坏性变更, 必须使用新的 URL 和 `schemaVersion`, 同时改变 capability revision. 不会在 V1 响应中静默复用不兼容语义.

## Disposable live-test

测试模式必须显式使用 `live-test --test-only`, 只在操作系统临时目录中创建确定性 fixture、进程内随机只读 Secret、权限受限的临时 Secret 文件和 readiness 文件. 它不读取生产数据库、Vault、用户文档或真实报告.

```powershell
daily-report integration live-test --test-only --runtime-dir "$env:TEMP\daily-report-integration-v1" --profile normal
```

readiness 只包含 PID、loopback Base URL、fixture ID、capability revision 和 Secret reference. Secret 通道文件名为 `integration-token`, readiness 文件名为 `readiness.json`. 每次启动都会轮换 Secret; 正常停止后 socket、临时文件和空运行目录都会删除.

可用测试启动档包括 `normal`、`unsupported-schema`、`redirect`、`oversized-response`、`delayed-response`, 以及规范定义的 `status-*` 档. 这些档只存在于显式 test-only 命令, 不可通过网络修改, 也不会进入生产启动路径.
