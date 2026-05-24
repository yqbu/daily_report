from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
import os
from pathlib import Path
from typing import Any

from daily_report.config.paths import get_installed_share_root, get_runtime_paths
from daily_report.reporter.material_card import MaterialCard

DEFAULT_TEMPLATE_NAME = 'daily_standard'


@dataclass(frozen=True)
class ReportMaterialBundle:
    """Compatibility bundle used by older callers."""

    date: str
    total_time: str = '0m'
    active_time: str = '0m'
    top_apps: list[str] = field(default_factory=list)
    app_sessions: list[str] = field(default_factory=list)
    clipboard_items: list[str] = field(default_factory=list)
    browser_items: list[str] = field(default_factory=list)
    ai_prompts: list[str] = field(default_factory=list)


class PromptBuilder:
    def __init__(self, template_dir: str | Path | None = None):
        if template_dir:
            self.template_dir = Path(template_dir)
            return

        env_template_dir = os.getenv('DAILY_REPORT_TEMPLATE_DIR')
        candidates = [
            Path(env_template_dir) if env_template_dir else None,
            get_runtime_paths().project_root / 'configs' / 'report_templates',
            get_installed_share_root() / 'configs' / 'report_templates',
        ]
        self.template_dir = next(
            (candidate for candidate in candidates if candidate and candidate.exists()),
            get_runtime_paths().project_root / 'configs' / 'report_templates',
        )

    def build_prompt(
        self,
        *,
        date: str,
        materials: list[MaterialCard],
        stats: dict[str, Any] | None = None,
        template_name: str = DEFAULT_TEMPLATE_NAME,
        max_chars: int = 12000,
    ) -> str:
        stats = stats or {}
        template_text = self.load_template(template_name)
        material_text = self._format_materials(materials)
        if not materials:
            material_text = '今日有效素材不足。请只基于已有统计进行保守总结，不要补充不存在的事项。'

        prompt = f"""你是一名严谨的个人工作日报写作助手。请根据用户本地采集并人工筛选后的素材，生成中文 Markdown 日报。

# 日期
{date}

# 今日统计
- 有效工作时长：{stats.get('active_time', '0m')}
- 总记录时长：{stats.get('total_time', '0m')}
- 前台应用素材：{stats.get('app', 0)}
- 浏览器素材：{stats.get('browser', 0)}
- 剪切板素材：{stats.get('clipboard', 0)}
- AI 提问素材：{stats.get('ai_prompt', 0)}

# 输出模板
{template_text}

# 已筛选素材
{material_text}

# 写作要求
- 只根据“已筛选素材”和“今日统计”写作。
- 禁止编造没有出现在素材中的项目、会议、客户、提交记录、邮件或日程。
- 禁止输出 API Key、密码、令牌、Cookie、Authorization、手机号、邮箱、身份证、银行卡等敏感内容。
- 对剪切板素材只引用摘要含义，不展开完整原文。
- 输出必须是 Markdown，直接给日报正文，不解释生成过程。
"""
        if max_chars > 0 and len(prompt) > max_chars:
            prompt = prompt[: max_chars - 80].rstrip() + '\n\n[提示：由于长度限制，后续素材已截断。]'
        return prompt

    def load_template(self, template_name: str) -> str:
        safe_name = template_name if template_name in {
            'daily_standard',
            'daily_technical',
            'daily_brief',
        } else DEFAULT_TEMPLATE_NAME
        path = self.template_dir / f'{safe_name}.md'
        if path.exists():
            return path.read_text(encoding='utf-8').strip()
        return (
            '## 今日工作概述\n\n'
            '## 主要工作内容\n\n'
            '## 问题与处理\n\n'
            '## 明日计划\n\n'
            '## 备注'
        )

    @staticmethod
    def _format_materials(materials: list[MaterialCard]) -> str:
        grouped: dict[str, list[MaterialCard]] = defaultdict(list)
        for material in materials:
            grouped[material.category or '其他'].append(material)

        lines: list[str] = []
        for category in sorted(grouped):
            lines.append(f'## {category}')
            for material in grouped[category]:
                sensitive_label = '，敏感素材已过滤' if material.is_sensitive else ''
                lines.append(
                    f"- [{material.time_range}] ({material.source_type}) {material.title}"
                    f"{sensitive_label}\n"
                    f"  - 摘要：{material.summary}\n"
                    f"  - 证据：{material.evidence}"
                )
        return '\n'.join(lines).strip()


def build_prompt_from_materials(
    *,
    date: str,
    materials: list[MaterialCard],
    stats: dict[str, Any] | None = None,
    template_name: str = DEFAULT_TEMPLATE_NAME,
    max_chars: int = 12000,
) -> str:
    return PromptBuilder().build_prompt(
        date=date,
        materials=materials,
        stats=stats,
        template_name=template_name,
        max_chars=max_chars,
    )


def build_daily_report_prompt(bundle: ReportMaterialBundle, *, max_chars: int = 12000) -> str:
    materials: list[MaterialCard] = []
    for source_type, category, items in (
        ('app', '开发编码', bundle.app_sessions),
        ('clipboard', '其他', bundle.clipboard_items),
        ('browser', '资料调研', bundle.browser_items),
        ('ai_prompt', 'AI 辅助', bundle.ai_prompts),
    ):
        for index, item in enumerate(items, start=1):
            materials.append(
                MaterialCard(
                    source_type=source_type,
                    source_id=index,
                    time_range='',
                    category=category,
                    title=item[:80],
                    summary=item,
                    evidence=item,
                    importance=0,
                    is_sensitive=False,
                )
            )
    stats = {
        'active_time': bundle.active_time,
        'total_time': bundle.total_time,
        'app': len(bundle.app_sessions),
        'clipboard': len(bundle.clipboard_items),
        'browser': len(bundle.browser_items),
        'ai_prompt': len(bundle.ai_prompts),
    }
    return build_prompt_from_materials(
        date=bundle.date,
        materials=materials,
        stats=stats,
        max_chars=max_chars,
    )


def build_material_summary(bundle: ReportMaterialBundle) -> str:
    return (
        f'date={bundle.date}; active_time={bundle.active_time}; total_time={bundle.total_time}; '
        f'app={len(bundle.app_sessions)}; clipboard={len(bundle.clipboard_items)}; '
        f'browser={len(bundle.browser_items)}; ai_prompt={len(bundle.ai_prompts)}'
    )
