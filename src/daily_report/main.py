from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from daily_report.service.report_service import ReportService
from daily_report.yasb_bridge.usage_status import print_status


def setup_logging(level: str = 'INFO') -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format='[%(asctime)s] %(levelname)s %(name)s: %(message)s',
    )


def run_service(args: argparse.Namespace) -> None:
    setup_logging(args.log_level)
    # 延迟导入，避免只执行 report/status 命令时被采集服务依赖阻断。
    from daily_report.service.app import DailyReportService
    service = DailyReportService()
    service.run()


def run_status(args: argparse.Namespace) -> None:
    # status 是给 YASB 高频调用的, 尽量不要输出额外日志到 stdout
    # 否则 YASB 解析 JSON 时可能失败
    print_status(
        target_date=args.date,
        limit=args.limit,
        as_json=args.json,
    )


def run_build_prompt(args: argparse.Namespace) -> None:
    service = ReportService(db_path=args.db_path)
    prompt = service.build_prompt(args.date, max_chars=args.max_chars)
    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(prompt, encoding="utf-8")
        print(f"Prompt saved to: {out_path}")
    else:
        print(prompt)


def run_generate_today(args: argparse.Namespace) -> None:
    setup_logging(args.log_level)
    service = ReportService(db_path=args.db_path)
    result = service.generate_report(
        target_date=args.date,
        api_key=args.api_key,
        save=not args.no_save,
    )

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(result.report_markdown, encoding="utf-8")
        print(f"Report markdown saved to: {out_path}")

    if args.print_prompt:
        print("\n" + "=" * 20 + " PROMPT " + "=" * 20)
        print(result.prompt_text)

    print("\n" + "=" * 20 + " REPORT " + "=" * 20)
    print(result.report_markdown)
    if result.report_id > 0:
        print(f"\nSaved report id: {result.report_id}")


def run_latest_report(args: argparse.Namespace) -> None:
    service = ReportService(db_path=args.db_path)
    record = service.get_latest_report(args.date)
    if record is None:
        print("No report found.")
        return
    print(record.report_markdown)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog='daily-report',
        description='Daily report collector and generator.',
    )

    subparsers = parser.add_subparsers(dest='command')

    run_parser = subparsers.add_parser('run', help='Run background collectors.')
    run_parser.add_argument('--log-level', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'])
    run_parser.set_defaults(func=run_service)

    status_parser = subparsers.add_parser('status', help="Print today's status for YASB or command line.")
    status_parser.add_argument('--json', action='store_true', help='Output status as JSON.')
    status_parser.add_argument(
        '--date', default=None, help='Target date, format: YYYY-MM-DD. Default: today.'
    )
    status_parser.add_argument( '--limit', type=int, default=5, help='Top app limit.')
    status_parser.set_defaults(func=run_status)

    prompt_parser = subparsers.add_parser(
        "build-prompt",
        help="Build the daily report prompt without calling the model.",
    )
    prompt_parser.add_argument("--date", default=None, help="Target date, format: YYYY-MM-DD.")
    prompt_parser.add_argument("--max-chars", type=int, default=None)
    prompt_parser.add_argument("--out", default=None, help="Optional output txt path.")
    prompt_parser.add_argument("--db-path", default=None, help="Optional SQLite db path.")
    prompt_parser.set_defaults(func=run_build_prompt)

    gen_parser = subparsers.add_parser(
        "generate-report", help="Generate a Markdown daily report with DeepSeek and save it.",
    )
    gen_parser.add_argument("--date", default=None, help="Target date, format: YYYY-MM-DD.")
    gen_parser.add_argument("--api-key", default=None, help="DeepSeek API key override.")
    gen_parser.add_argument("--db-path", default=None, help="Optional SQLite db path.")
    gen_parser.add_argument("--out", default=None, help="Optional output markdown path.")
    gen_parser.add_argument("--no-save", action="store_true", help="Do not save to daily_reports.")
    gen_parser.add_argument("--print-prompt", action="store_true", help="Print prompt before report.")
    gen_parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    gen_parser.set_defaults(func=run_generate_today)

    latest_parser = subparsers.add_parser("latest-report", help="Print latest saved report markdown for a date.")
    latest_parser.add_argument("--date", default=None, help="Target date, format: YYYY-MM-DD.")
    latest_parser.add_argument("--db-path", default=None, help="Optional SQLite db path.")
    latest_parser.set_defaults(func=run_latest_report)

    return parser


def main() -> None:
    parser = build_parser()

    # 如果没有任何参数，默认执行 run 命令
    if len(sys.argv) == 1:
        args = parser.parse_args(['run'])
    else:
        args = parser.parse_args()

    if not hasattr(args, 'func'):
        parser.print_help()
        return

    args.func(args)


if __name__ == '__main__':
    main()