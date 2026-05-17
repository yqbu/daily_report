from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ReportMaterialBundle:
    date: str
    total_time: str = '0m'
    active_time: str = '0m'
    top_apps: list[str] = field(default_factory=list)
    app_sessions: list[str] = field(default_factory=list)
    clipboard_items: list[str] = field(default_factory=list)
    browser_items: list[str] = field(default_factory=list)
    ai_prompts: list[str] = field(default_factory=list)


def _section(title: str, items: list[str], *, empty_text: str = '无') -> str:
    if not items:
        return f'## {title}\n{empty_text}\n'
    lines = [f'## {title}']
    lines.extend(f'- {item}' for item in items if item)
    return '\n'.join(lines) + '\n'


def build_daily_report_prompt(bundle: ReportMaterialBundle, *, max_chars: int = 12000) -> str:
    prompt = f"""
你需要根据用户本地采集的工作痕迹, 生成一份中文 Markdown 工作日报。

要求:
1. 不要编造没有出现在素材中的具体事项
2. 可以对窗口标题、搜索词、AI 提问进行归纳, 但要保持克制
3. 输出结构建议包含: 今日概览、主要工作内容、问题与处理、明日计划
4. 语气正式、简洁, 适合作为个人工作日报初稿
5. 如素材不足, 请明确写成“根据已采集素材, 今日主要活动为……”, 不要硬凑

# 日期
{bundle.date}

# 时间概览
- 总记录时长: {bundle.total_time}
- 活跃工作时长: {bundle.active_time}

{_section('Top 应用', bundle.top_apps)}
{_section(f'已选前台窗口记录({len(bundle.app_sessions)}条)', bundle.app_sessions)}
{_section(f'已选剪贴板素材({len(bundle.clipboard_items)}条)', bundle.clipboard_items)}
{_section(f'已选浏览/搜索记录({len(bundle.browser_items)}条)', bundle.browser_items)}
{_section(f'已选 AI 提问记录({len(bundle.ai_prompts)}条)', bundle.ai_prompts)}

请直接输出日报 Markdown, 不要解释你的生成过程。
 """.strip()

    if max_chars > 0 and len(prompt) > max_chars:
        prompt = prompt[:max_chars] + '\n\n[提示: 由于长度限制, 后续素材已截断]'
    return prompt


def build_material_summary(bundle: ReportMaterialBundle) -> str:
    lines: list[str] = [
        f"日期：{bundle.date}",
        f"总时长：{bundle.total_time}",
        f"活跃时间：{bundle.active_time}",
        "",
        "Top 应用：",
    ]
    lines.extend([f"- {item}" for item in bundle.top_apps] or ["- 暂无"])

    sections = [
        ("应用使用记录", bundle.app_sessions),
        ("剪贴板素材", bundle.clipboard_items),
        ("浏览记录与搜索", bundle.browser_items),
        ("AI 提问记录", bundle.ai_prompts),
    ]
    for title, items in sections:
        lines.extend(["", f"{title}："])
        lines.extend([f"- {item}" for item in items] or ["- 暂无"])
    return "\n".join(lines)