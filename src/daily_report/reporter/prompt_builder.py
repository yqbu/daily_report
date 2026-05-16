from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ReportMaterialBundle:
    date: str
    active_time: str
    total_time: str
    top_apps: list[str]
    app_sessions: list[str]
    clipboard_items: list[str]
    browser_items: list[str]
    ai_prompts: list[str]


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


def build_daily_report_prompt(bundle: ReportMaterialBundle, *, max_chars: int = 12000) -> str:
    material_summary = build_material_summary(bundle)
    prompt = f"""请基于以下本地工作素材，生成一份结构化中文 Markdown 日报。
                要求：
                1. 不要编造未出现在素材中的事实；
                2. 将零散行为归纳为 3 到 6 个具体工作主题；
                3. 输出结构包含：今日工作概览、主要工作内容、问题与处理、明日计划；
                4. 语言要像正式工作日报，避免流水账；
                5. 涉及疑似敏感内容时只做概括，不输出密钥、token、密码或完整 URL。
                以下是已由用户在本地 GUI 中确认选中的素材：
                {material_summary}
             """
    if len(prompt) > max_chars:
        prompt = prompt[:max_chars] + "\n\n[提示：由于长度限制，后续素材已截断。]"
    return prompt
