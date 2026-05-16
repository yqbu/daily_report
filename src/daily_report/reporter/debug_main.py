from __future__ import annotations

from daily_report.service.report_service import ReportService


def debug_generate_report() -> None:
    """
    IDE/debug 专用入口

    API key 读取优先级：
    1. 环境变量 DEEPSEEK_API_KEY
    2. %APPDATA%/daily-report/local_settings.json 中的 model.api_key
    """
    service = ReportService()
    result = service.generate_report()
    print("=" * 20, "PROMPT", "=" * 20)
    print(result.prompt_text)
    print("=" * 20, "REPORT", "=" * 20)
    print(result.report_markdown)
    print(f"Saved report id: {result.report_id}")


def debug_build_prompt() -> None:
    service = ReportService()
    print(service.build_prompt())


if __name__ == "__main__":
    debug_generate_report()
