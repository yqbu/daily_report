from __future__ import annotations

from typing import Any

from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse


class ApiError(Exception):
    def __init__(self, error: str, code: str, status_code: int = 400):
        super().__init__(error)
        self.error = error
        self.code = code
        self.status_code = status_code


def ok(data: Any = None) -> dict[str, Any]:
    return {'ok': True, 'data': jsonable_encoder(data)}


def error_payload(error: str, code: str) -> dict[str, Any]:
    return {'ok': False, 'error': error, 'code': code}


def error_response(error: str, code: str, status_code: int = 400) -> JSONResponse:
    return JSONResponse(status_code=status_code, content=error_payload(error, code))

