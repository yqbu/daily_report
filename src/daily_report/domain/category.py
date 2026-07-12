from __future__ import annotations

from urllib.parse import urlparse

DEV_CATEGORY = "\u5f00\u53d1\u7f16\u7801"
DEBUG_CATEGORY = "\u95ee\u9898\u6392\u67e5"
RESEARCH_CATEGORY = "\u8d44\u6599\u8c03\u7814"
AI_CATEGORY = "AI \u8f85\u52a9"
DOC_CATEGORY = "\u6587\u6863\u6574\u7406"
COMM_CATEGORY = "\u6c9f\u901a\u534f\u4f5c"
SYSTEM_CATEGORY = "\u7cfb\u7edf\u914d\u7f6e"
DEFAULT_CATEGORY = "\u5176\u4ed6"

CATEGORIES: tuple[str, ...] = (
    DEV_CATEGORY,
    DEBUG_CATEGORY,
    RESEARCH_CATEGORY,
    AI_CATEGORY,
    DOC_CATEGORY,
    COMM_CATEGORY,
    SYSTEM_CATEGORY,
    DEFAULT_CATEGORY,
)


def infer_category_for_app(process_name: str | None, window_title: str | None = None) -> str:
    text = f"{process_name or ''} {window_title or ''}".lower()
    if any(token in text for token in ("pycharm", "code", "cursor", "git", "terminal", "powershell", "python")):
        return DEV_CATEGORY
    if any(token in text for token in ("error", "exception", "traceback", "debug", "log")):
        return DEBUG_CATEGORY
    if any(token in text for token in ("edge", "chrome", "firefox", "browser", "docs", "search")):
        return RESEARCH_CATEGORY
    if any(token in text for token in ("chatgpt", "deepseek", "claude", "gemini", "copilot")):
        return AI_CATEGORY
    if any(token in text for token in ("word", "excel", "powerpoint", "notepad", "typora", "markdown")):
        return DOC_CATEGORY
    if any(token in text for token in ("wechat", "weixin", "qq", "teams", "slack", "discord", "mail")):
        return COMM_CATEGORY
    if any(token in text for token in ("settings", "control", "taskmgr", "explorer")):
        return SYSTEM_CATEGORY
    return DEFAULT_CATEGORY


def infer_category_for_browser(url: str | None, title: str | None = None) -> str:
    text = f"{url or ''} {title or ''}".lower()
    try:
        host = urlparse(url or "").hostname or ""
    except ValueError:
        host = ""

    if any(token in text for token in ("chatgpt", "deepseek", "claude", "gemini", "openai")):
        return AI_CATEGORY
    if any(token in host for token in ("github", "stackoverflow", "developer", "docs", "readthedocs")):
        return DEV_CATEGORY
    if any(token in text for token in ("search", "google", "bing", "baidu", "wiki")):
        return RESEARCH_CATEGORY
    return RESEARCH_CATEGORY


def infer_category_for_clipboard(content: str | None) -> str:
    text = (content or "").lower()
    if any(token in text for token in ("def ", "class ", "function ", "import ", "select *", "```")):
        return DEV_CATEGORY
    if any(token in text for token in ("http://", "https://", "www.")):
        return RESEARCH_CATEGORY
    return DOC_CATEGORY if text.strip() else DEFAULT_CATEGORY


def infer_category_for_ai_prompt(prompt_text: str | None, platform: str | None = None) -> str:
    return AI_CATEGORY
