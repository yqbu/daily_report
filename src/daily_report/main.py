from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

def setup_logging(level: str = 'INFO') -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format='[%(asctime)s] %(levelname)s %(name)s: %(message)s',
    )


def configured_log_level(override: str | None = None) -> str:
    if override:
        return override
    from daily_report.config.local_settings import load_local_settings

    return load_local_settings().logging.level


def run_service(args: argparse.Namespace) -> None:
    setup_logging(configured_log_level(args.log_level))
    # 延迟导入, 避免只执行 report/status 命令时被采集服务依赖阻断
    from daily_report.service.app import DailyReportService
    service = DailyReportService()
    service.run()


def run_status(args: argparse.Namespace) -> None:
    # status 是给 YASB 高频调用的, 尽量不要输出额外日志到 stdout
    # 否则 YASB 解析 JSON 时可能失败
    from daily_report.yasb_bridge.usage_status import print_status

    print_status(
        target_date=args.date,
        limit=args.limit,
        as_json=args.json,
    )


def run_build_prompt(args: argparse.Namespace) -> None:
    from daily_report.service.report_service import ReportService

    service = ReportService(db_path=args.db_path)
    prompt = service.build_prompt(
        args.date,
        template_name=args.template_name,
        max_chars=args.max_chars,
    )
    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(prompt, encoding='utf-8')
        print(f'Prompt saved to: {out_path}')
    else:
        print(prompt)


def run_generate_today(args: argparse.Namespace) -> None:
    from daily_report.service.report_service import ReportService

    setup_logging(configured_log_level(args.log_level))
    service = ReportService(db_path=args.db_path)
    result = service.generate_report(
        target_date=args.date,
        api_key=args.api_key,
        save=not args.no_save,
        template_name=args.template_name,
    )

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(result.report_markdown, encoding='utf-8')
        print(f'Report markdown saved to: {out_path}')

    if args.print_prompt:
        print('\n' + '=' * 20 + ' PROMPT ' + '=' * 20)
        print(result.prompt_text)

    print('\n' + '=' * 20 + ' REPORT ' + '=' * 20)
    print(result.report_markdown)
    if result.report_id > 0:
        print(f'\nSaved report id: {result.report_id}')


def run_latest_report(args: argparse.Namespace) -> None:
    from daily_report.service.report_service import ReportService

    service = ReportService(db_path=args.db_path)
    record = service.get_latest_report(args.date)
    if record is None:
        print('No report found' )
        return
    print(record.report_markdown)


def run_gui_cmd(args: argparse.Namespace) -> None:
    if getattr(args, "backend", "tauri") == "pyside":
        run_pyside_gui_cmd(args)
        return

    from daily_report.gui_launcher.tauri_launcher import launch_tauri_gui

    try:
        exit_code = launch_tauri_gui(
            project_root=Path(args.project_root) if args.project_root else None,
            manual_api=args.manual_api or args.no_sidecar,
        )
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        print(
            "Tauri GUI failed to start. You can try:\n"
            "1. Confirm Node.js and npm are installed.\n"
            "2. Run npm install in the repository root.\n"
            "3. Run npm run tauri:dev:sidecar manually.\n"
            "4. Or use the legacy GUI: daily-report gui-pyside",
            file=sys.stderr,
        )
        raise SystemExit(1) from exc
    raise SystemExit(exit_code)


def run_pyside_gui_cmd(args: argparse.Namespace) -> None:
    from daily_report.gui_launcher.pyside_launcher import launch_pyside_gui

    remote_debugging_port = None
    if getattr(args, "remote_debugging", False):
        remote_debugging_port = args.remote_debugging_port
    try:
        exit_code = launch_pyside_gui(
            dev=getattr(args, "dev", False),
            dev_port=getattr(args, "dev_port", 5173),
            remote_debugging_port=remote_debugging_port,
            manage_api=not getattr(args, "no_api", False),
            api_host=getattr(args, "api_host", "127.0.0.1"),
            api_port=getattr(args, "api_port", 8765),
        )
    except Exception as exc:
        print(
            "PySide6 GUI failed to start. The recommended GUI is now Tauri: daily-report gui",
            file=sys.stderr,
        )
        print(f"Underlying error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    raise SystemExit(exit_code)


def run_api_cmd(args: argparse.Namespace) -> None:
    from daily_report.api.server import run_api_server

    run_api_server(host=args.host, port=args.port, token=args.token)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog='daily-report',
        description='Daily report collector and generator' ,
    )

    subparsers = parser.add_subparsers(dest='command')

    run_parser = subparsers.add_parser('run', help='Run background collectors' )
    run_parser.add_argument('--log-level', default=None, choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'])
    run_parser.set_defaults(func=run_service)

    status_parser = subparsers.add_parser('status', help='Print today\'s status for YASB or command line' )
    status_parser.add_argument('--json', action='store_true', help='Output status as JSON' )
    status_parser.add_argument(
        '--date', default=None, help='Target date, format: YYYY-MM-DD. Default: today'
    )
    status_parser.add_argument( '--limit', type=int, default=5, help='Top app limit' )
    status_parser.set_defaults(func=run_status)

    prompt_parser = subparsers.add_parser(
        'build-prompt',
        help='Build the daily report prompt without calling the model' ,
    )
    prompt_parser.add_argument('--date', default=None, help='Target date, format: YYYY-MM-DD' )
    prompt_parser.add_argument('--max-chars', type=int, default=None)
    prompt_parser.add_argument('--template-name', default='daily_standard')
    prompt_parser.add_argument('--out', default=None, help='Optional output txt path' )
    prompt_parser.add_argument('--db-path', default=None, help='Optional SQLite db path' )
    prompt_parser.set_defaults(func=run_build_prompt)

    gen_parser = subparsers.add_parser(
        'generate-report', help='Generate a Markdown daily report with DeepSeek and save it' ,
    )
    gen_parser.add_argument('--date', default=None, help='Target date, format: YYYY-MM-DD' )
    gen_parser.add_argument('--api-key', default=None, help='DeepSeek API key override' )
    gen_parser.add_argument('--template-name', default='daily_standard')
    gen_parser.add_argument('--db-path', default=None, help='Optional SQLite db path' )
    gen_parser.add_argument('--out', default=None, help='Optional output markdown path' )
    gen_parser.add_argument('--no-save', action='store_true', help='Do not save to daily_reports' )
    gen_parser.add_argument('--print-prompt', action='store_true', help='Print prompt before report' )
    gen_parser.add_argument('--log-level', default=None, choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'])
    gen_parser.set_defaults(func=run_generate_today)

    gen_today_parser = subparsers.add_parser(
        'generate-today', help='Alias for generate-report kept for compatibility'
    )
    gen_today_parser.add_argument('--date', default=None, help='Target date, format: YYYY-MM-DD' )
    gen_today_parser.add_argument('--api-key', default=None, help='DeepSeek API key override' )
    gen_today_parser.add_argument('--template-name', default='daily_standard')
    gen_today_parser.add_argument('--db-path', default=None, help='Optional SQLite db path' )
    gen_today_parser.add_argument('--out', default=None, help='Optional output markdown path' )
    gen_today_parser.add_argument('--no-save', action='store_true', help='Do not save to daily_reports' )
    gen_today_parser.add_argument('--print-prompt', action='store_true', help='Print prompt before report' )
    gen_today_parser.add_argument('--log-level', default=None, choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'])
    gen_today_parser.set_defaults(func=run_generate_today)

    latest_parser = subparsers.add_parser('latest-report', help='Print latest saved report markdown for a date' )
    latest_parser.add_argument('--date', default=None, help='Target date, format: YYYY-MM-DD' )
    latest_parser.add_argument('--db-path', default=None, help='Optional SQLite db path' )
    latest_parser.set_defaults(func=run_latest_report)

    gui_parser = subparsers.add_parser('gui', help='Open the recommended Tauri desktop GUI')
    gui_parser.add_argument('--project-root', default=None, help='Daily Report repository root')
    gui_parser.add_argument(
        '--manual-api',
        action='store_true',
        help='Do not ask Tauri to start Python API; equivalent to npm run tauri:dev',
    )
    gui_parser.add_argument('--no-sidecar', action='store_true', help='Alias for --manual-api')
    gui_parser.add_argument(
        '--backend',
        choices=['tauri', 'pyside'],
        default='tauri',
        help='GUI backend to launch. Defaults to tauri.',
    )
    gui_parser.set_defaults(func=run_gui_cmd)

    gui_tauri_parser = subparsers.add_parser('gui-tauri', help='Open the Tauri desktop GUI')
    gui_tauri_parser.add_argument('--project-root', default=None, help='Daily Report repository root')
    gui_tauri_parser.add_argument(
        '--manual-api',
        action='store_true',
        help='Do not ask Tauri to start Python API; equivalent to npm run tauri:dev',
    )
    gui_tauri_parser.add_argument('--no-sidecar', action='store_true', help='Alias for --manual-api')
    gui_tauri_parser.set_defaults(func=run_gui_cmd, backend='tauri')

    gui_pyside_parser = subparsers.add_parser('gui-pyside', help='Open the legacy PySide6 GUI fallback')
    gui_pyside_parser.add_argument('--dev', action='store_true', help='Start Vite dev server and load it in QWebEngine')
    gui_pyside_parser.add_argument('--dev-port', type=int, default=5173, help='Vite dev server port, default: 5173')
    gui_pyside_parser.add_argument('--api-host', default='127.0.0.1', help='Managed API host, default: 127.0.0.1')
    gui_pyside_parser.add_argument('--api-port', type=int, default=8765, help='Managed API port, default: 8765')
    gui_pyside_parser.add_argument('--no-api', action='store_true', help='Do not auto-start the local FastAPI sidecar')
    gui_pyside_parser.add_argument(
        '--remote-debugging',
        action='store_true',
        help='Enable QWebEngine remote debugging, default port: 9223',
    )
    gui_pyside_parser.add_argument('--remote-debugging-port', type=int, default=9223)
    gui_pyside_parser.set_defaults(func=run_pyside_gui_cmd)

    api_parser = subparsers.add_parser('api', help='Run local FastAPI sidecar API')
    api_parser.add_argument('--host', default='127.0.0.1', help='Bind host, default: 127.0.0.1')
    api_parser.add_argument('--port', type=int, default=8765, help='Bind port, default: 8765; 0 uses a free port')
    api_parser.add_argument('--token', default=None, help='Optional bearer token required by protected APIs')
    api_parser.set_defaults(func=run_api_cmd)

    return parser


def main() -> None:
    parser = build_parser()

    # 如果没有任何参数, 默认执行 run 命令
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
