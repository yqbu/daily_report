from __future__ import annotations

CATEGORIES = (
    '开发编码',
    '问题排查',
    '资料调研',
    'AI 辅助',
    '文档整理',
    '沟通协作',
    '系统配置',
    '其他',
)

DEBUG_KEYWORDS = ('error', 'exception', 'bug', '报错', '问题', '修复', 'debug')
CONFIG_KEYWORDS = ('config', '配置', '环境', '安装')
DEV_KEYWORDS = (
    'pycharm',
    'vscode',
    'visual studio code',
    'cursor',
    'python',
    'terminal',
    'powershell',
    'cmd.exe',
    'windows terminal',
    '代码',
    '开发',
)
DOC_KEYWORDS = ('markdown', 'readme', '文档', '日报', '笔记')
COMM_KEYWORDS = ('wechat', 'weixin', 'dingtalk', 'feishu', 'teams', 'slack', '微信', '钉钉', '飞书')


def infer_category_for_app(process_name: str | None, window_title: str | None) -> str:
    text = _join(process_name, window_title)
    if _contains(text, DEBUG_KEYWORDS):
        return '问题排查'
    if _contains(text, CONFIG_KEYWORDS):
        return '系统配置'
    if _contains(text, DEV_KEYWORDS):
        return '开发编码'
    if _contains(text, DOC_KEYWORDS):
        return '文档整理'
    if _contains(text, COMM_KEYWORDS):
        return '沟通协作'
    return '其他'


def infer_category_for_browser(
    title: str | None,
    url: str | None,
    is_search: bool | int | None,
    search_query: str | None,
) -> str:
    text = _join(title, url, search_query)
    if _contains(text, DEBUG_KEYWORDS):
        return '问题排查'
    if _contains(text, CONFIG_KEYWORDS):
        return '系统配置'
    if _contains(text, DEV_KEYWORDS):
        return '开发编码'
    return '资料调研' if is_search or text else '其他'


def infer_category_for_clipboard(content_preview: str | None) -> str:
    text = _join(content_preview)
    if _contains(text, DEBUG_KEYWORDS):
        return '问题排查'
    if _contains(text, CONFIG_KEYWORDS):
        return '系统配置'
    if _contains(text, DEV_KEYWORDS):
        return '开发编码'
    if _contains(text, DOC_KEYWORDS):
        return '文档整理'
    return '其他'


def infer_category_for_ai_prompt(prompt_preview: str | None) -> str:
    text = _join(prompt_preview)
    if _contains(text, DEBUG_KEYWORDS):
        return '问题排查'
    if _contains(text, CONFIG_KEYWORDS):
        return '系统配置'
    return 'AI 辅助'


def _join(*values: str | None) -> str:
    return ' '.join(str(value or '') for value in values).lower()


def _contains(text: str, keywords: tuple[str, ...]) -> bool:
    return any(keyword.lower() in text for keyword in keywords)
