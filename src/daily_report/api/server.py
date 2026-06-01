from __future__ import annotations

import socket

import uvicorn

from daily_report.api.app import create_app


def run_api_server(
    *,
    host: str = '127.0.0.1',
    port: int = 8765,
    token: str | None = None,
) -> None:
    if host == '0.0.0.0':
        raise ValueError('Refusing to listen on 0.0.0.0 for the local sidecar API.')

    resolved_port = _resolve_port(host, int(port))
    print(f'Daily Report API listening on http://{host}:{resolved_port}', flush=True)
    uvicorn.run(
        create_app(api_token=token),
        host=host,
        port=resolved_port,
        log_level='warning',
        access_log=False,
    )


def _resolve_port(host: str, port: int) -> int:
    if port != 0:
        return port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, 0))
        return int(sock.getsockname()[1])

