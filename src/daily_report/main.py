from __future__ import annotations

import sys
import argparse
import logging

from daily_report.service.app import DailyReportService


def setup_logging(level: str = 'INFO') -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format='[%(asctime)s] %(levelname)s %(name)s: %(message)s',
    )


def run_service(args: argparse.Namespace) -> None:
    setup_logging(args.log_level)

    service = DailyReportService()
    service.run()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog='daily-report',
        description='Daily report collector and generator.',
    )

    subparsers = parser.add_subparsers(dest='command')

    run_parser = subparsers.add_parser(
        'run',
        help='Run background collectors.',
    )
    run_parser.add_argument(
        '--log-level',
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
    )
    run_parser.set_defaults(func=run_service)

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