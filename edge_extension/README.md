# Daily Report AI Prompt Collector Edge Extension

## 安装方式

1. 打开 Edge：`edge://extensions/`
2. 开启“开发人员模式”
3. 点击“加载解压缩的扩展”
4. 选择本目录 `edge_extension`
5. 启动 Python receiver：

```powershell
python -m daily_report.collector.ai_prompt_receiver
```

或启动整个服务：

```powershell
daily-report run
```

## Token 可选配置

如果 Python 侧设置了：

```powershell
$env:DAILY_REPORT_AI_PROMPT_TOKEN="your-local-token"
```

则需要在 `content_script.js` 中同步设置：

```js
authToken: "your-local-token"
```

MVP 阶段可以先留空；只要 receiver 也没有设置环境变量 token，就能正常联通。
