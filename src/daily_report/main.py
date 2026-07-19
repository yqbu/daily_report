from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path


INTEGRATION_FAULT_PROFILES = (
    "normal",
    "unsupported-schema",
    "redirect",
    "oversized-response",
    "delayed-response",
    "status-400",
    "status-401",
    "status-403",
    "status-404",
    "status-409",
    "status-422",
    "status-408",
    "status-425",
    "status-429",
    "status-500",
)

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
    from daily_report.service.runtime_process_service import RuntimeProcessService

    runtime = RuntimeProcessService()
    collector_status = runtime.get_collector_runtime_status()
    if collector_status.get('status') == 'running':
        print('Collector already running')
        print(f"PID: {collector_status.get('pid')}")
        print(f"lock_path: {collector_status.get('lock_path')}")
        print('Use `daily-report runtime status` to view details.')
        return

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
            "2. Run npm install in the repository root to install all workspaces.\n"
            "3. Run npm run tauri:dev:sidecar manually.",
            file=sys.stderr,
        )
        raise SystemExit(1) from exc
    raise SystemExit(exit_code)
def run_api_cmd(args: argparse.Namespace) -> None:
    from daily_report.api.server import run_api_server

    try:
        from daily_report.service.runtime_process_service import RuntimeProcessService

        RuntimeProcessService().register_current_process('api', port=args.port)
        run_api_server(host=args.host, port=args.port, token=args.token)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc


def run_integration_serve(args: argparse.Namespace) -> None:
    if getattr(args, "enabled", None) is not True:
        return

    from daily_report.integration_v1.server import run_production_provider

    secret = os.getenv(args.secret_env)
    if not secret:
        print("Integration V1 unavailable: secret_unavailable", file=sys.stderr)
        raise SystemExit(1)
    try:
        run_production_provider(
            host=args.host,
            port=args.port,
            bearer_token=secret,
            db_path=args.db_path,
        )
    except Exception as exc:
        print("Integration V1 unavailable: startup_failed", file=sys.stderr)
        raise SystemExit(1) from exc


def run_integration_live_test(args: argparse.Namespace) -> None:
    if not args.test_only:
        print("Integration V1 live test requires --test-only.", file=sys.stderr)
        raise SystemExit(2)

    from daily_report.integration_v1.server import run_live_test_provider

    try:
        run_live_test_provider(
            host=args.host,
            port=args.port,
            runtime_dir=args.runtime_dir,
            profile=args.profile,
        )
    except Exception as exc:
        print("Integration V1 live test unavailable: startup_failed", file=sys.stderr)
        raise SystemExit(1) from exc


def _explicit_bool(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"true", "1"}:
        return True
    if normalized in {"false", "0"}:
        return False
    raise argparse.ArgumentTypeError("expected true or false")


def run_runtime_status(args: argparse.Namespace) -> None:
    from daily_report.service.runtime_process_service import RuntimeProcessService, summary_to_dict

    summary = RuntimeProcessService().get_summary()
    payload = summary_to_dict(summary)
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    print('Runtime Status')
    print(f"* API: {summary.api_status}, pid={summary.api_pid}, port={summary.api_port}")
    print(f"* Collector: {summary.collector_status}, pid={summary.collector_pid}")
    print(f"* Database: {summary.database_status}")
    print(f"* YASB: {summary.yasb_status}")
    print(f"* Orphans: {summary.orphan_process_count}")
    print(f"* Duplicates: {summary.duplicate_process_count}")
    print(f"* Diagnostics: warnings={summary.warning_count}, errors={summary.error_count}")


def run_runtime_processes(args: argparse.Namespace) -> None:
    from daily_report.service.runtime_process_service import RuntimeProcessService

    processes = RuntimeProcessService().list_processes()
    if not processes:
        print('No Daily Report related processes detected.')
        return
    for process in processes:
        print(
            f"{process.role} pid={process.pid} ppid={process.parent_pid} "
            f"status={process.status} cpu={process.cpu_percent} mem={process.memory_mb}MB "
            f"port={process.port} risk={process.risk_level}"
        )
        print(f"  started_at: {process.started_at}")
        print(f"  cwd: {process.cwd}")
        print(f"  cmdline: {process.cmdline_preview}")
        if process.reason:
            print(f"  reason: {process.reason}")


def run_runtime_doctor(args: argparse.Namespace) -> None:
    from daily_report.service.runtime_process_service import RuntimeProcessService

    diagnostics = RuntimeProcessService().run_doctor()
    for item in diagnostics:
        marker = item.level.upper()
        fixable = 'fixable' if item.fixable else 'manual'
        print(f"[{marker}] {item.title} ({fixable})")
        print(f"  {item.message}")
        if item.action:
            print(f"  action: {item.action}")


def run_runtime_cleanup_orphans(args: argparse.Namespace) -> None:
    from daily_report.service.runtime_process_service import RuntimeProcessService

    dry_run = not bool(args.execute)
    result = RuntimeProcessService().cleanup_orphans(dry_run=dry_run, force=bool(args.force))
    print(json.dumps(result, ensure_ascii=False, indent=2))


def run_runtime_repair(args: argparse.Namespace) -> None:
    from daily_report.service.runtime_process_service import RuntimeProcessService

    print(json.dumps(RuntimeProcessService().repair_runtime_state(), ensure_ascii=False, indent=2))


def run_runtime_stop_collector(args: argparse.Namespace) -> None:
    from daily_report.service.runtime_process_service import RuntimeProcessService

    print(json.dumps(RuntimeProcessService().stop_collector_gracefully(), ensure_ascii=False, indent=2))


def run_runtime_restart_collector(args: argparse.Namespace) -> None:
    from daily_report.service.runtime_process_service import RuntimeProcessService

    print(json.dumps(RuntimeProcessService().restart_collector(), ensure_ascii=False, indent=2))


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
    gui_parser.set_defaults(func=run_gui_cmd)

    gui_tauri_parser = subparsers.add_parser('gui-tauri', help='Open the Tauri desktop GUI')
    gui_tauri_parser.add_argument('--project-root', default=None, help='Daily Report repository root')
    gui_tauri_parser.add_argument(
        '--manual-api',
        action='store_true',
        help='Do not ask Tauri to start Python API; equivalent to npm run tauri:dev',
    )
    gui_tauri_parser.add_argument('--no-sidecar', action='store_true', help='Alias for --manual-api')
    gui_tauri_parser.set_defaults(func=run_gui_cmd)

    api_parser = subparsers.add_parser('api', help='Run local FastAPI sidecar API')
    api_parser.add_argument('--host', default='127.0.0.1', help='Bind host, default: 127.0.0.1')
    api_parser.add_argument('--port', type=int, default=8765, help='Bind port, default: 8765; 0 uses a free port')
    api_parser.add_argument('--token', default=None, help='Optional bearer token required by protected APIs')
    api_parser.set_defaults(func=run_api_cmd)

    integration_parser = subparsers.add_parser(
        "integration",
        help="Run the optional read-only Workbench V1 provider",
    )
    integration_subparsers = integration_parser.add_subparsers(dest="integration_command")

    integration_serve_parser = integration_subparsers.add_parser(
        "serve",
        help="Run the production read-only provider when explicitly enabled",
    )
    integration_serve_parser.add_argument("--enabled", type=_explicit_bool, default=None)
    integration_serve_parser.add_argument("--host", default="127.0.0.1")
    integration_serve_parser.add_argument("--port", type=int, default=8766)
    integration_serve_parser.add_argument(
        "--secret-env",
        default="DAILY_REPORT_INTEGRATION_TOKEN",
        help="Environment variable name containing the bearer secret",
    )
    integration_serve_parser.add_argument("--db-path", default=None)
    integration_serve_parser.set_defaults(func=run_integration_serve)

    integration_live_parser = integration_subparsers.add_parser(
        "live-test",
        help="Run the disposable synthetic Workbench V1 provider",
    )
    integration_live_parser.add_argument("--test-only", action="store_true")
    integration_live_parser.add_argument("--host", default="127.0.0.1")
    integration_live_parser.add_argument("--port", type=int, default=0)
    integration_live_parser.add_argument("--runtime-dir", required=True)
    integration_live_parser.add_argument(
        "--profile",
        default="normal",
        choices=INTEGRATION_FAULT_PROFILES,
    )
    integration_live_parser.set_defaults(func=run_integration_live_test)

    runtime_parser = subparsers.add_parser('runtime', help='Inspect and manage Daily Report runtime processes')
    runtime_subparsers = runtime_parser.add_subparsers(dest='runtime_command')

    runtime_status_parser = runtime_subparsers.add_parser('status', help='Show runtime status')
    runtime_status_parser.add_argument('--json', action='store_true', help='Output runtime status as JSON')
    runtime_status_parser.set_defaults(func=run_runtime_status)

    runtime_processes_parser = runtime_subparsers.add_parser('processes', help='List Daily Report related processes')
    runtime_processes_parser.set_defaults(func=run_runtime_processes)

    runtime_doctor_parser = runtime_subparsers.add_parser('doctor', help='Run runtime diagnostics')
    runtime_doctor_parser.set_defaults(func=run_runtime_doctor)

    runtime_repair_parser = runtime_subparsers.add_parser('repair', help='Repair stale runtime state')
    runtime_repair_parser.set_defaults(func=run_runtime_repair)

    runtime_cleanup_parser = runtime_subparsers.add_parser('cleanup-orphans', help='Clean orphan child processes')
    runtime_cleanup_parser.add_argument('--dry-run', action='store_true', default=True, help='Show what would be cleaned')
    runtime_cleanup_parser.add_argument('--execute', action='store_true', help='Actually terminate safe orphan processes')
    runtime_cleanup_parser.add_argument('--force', action='store_true', help='Use kill instead of terminate')
    runtime_cleanup_parser.set_defaults(func=run_runtime_cleanup_orphans)

    runtime_stop_parser = runtime_subparsers.add_parser('stop-collector', help='Gracefully stop collector')
    runtime_stop_parser.set_defaults(func=run_runtime_stop_collector)

    runtime_restart_parser = runtime_subparsers.add_parser('restart-collector', help='Restart collector')
    runtime_restart_parser.set_defaults(func=run_runtime_restart_collector)

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
