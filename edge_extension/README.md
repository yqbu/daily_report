# Daily Report AI Prompt Collector Edge Extension

This extension captures only user-submitted prompts on:

- `https://chatgpt.com/*`
- `https://chat.openai.com/*`
- `https://chat.deepseek.com/*`

It posts the prompt text to the local receiver:

```text
http://127.0.0.1:8765/api/ai-prompt
```

It does not capture model responses.

## Install

1. Open `edge://extensions/`.
2. Enable developer mode.
3. Click "Load unpacked".
4. Select this `edge_extension` directory.
5. Start the local collector:

```powershell
daily-report run
```

For receiver-only debugging:

```powershell
python -m daily_report.collector.ai_prompt_receiver
```

## Optional Token

If Python is started with:

```powershell
$env:DAILY_REPORT_AI_PROMPT_TOKEN="your-local-token"
```

set the same token in `content_script.js`:

```js
authToken: "your-local-token"
```
