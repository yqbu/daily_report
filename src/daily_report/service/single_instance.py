from __future__ import annotations

import logging
import os
from pathlib import Path
from types import TracebackType
from typing import Optional, Type

logger = logging.getLogger(__name__)


class SingleInstanceError(RuntimeError):
    """Raised when another collector instance is already running."""


class SingleInstanceLock:
    """
    Windows file-lock based single instance guard.

    特点：
    1. 不依赖进程名判断，PyCharm / daily-report.exe / python -m 都能统一防重。
    2. 进程异常退出后，Windows 会自动释放文件锁。
    3. lock 文件残留没关系，只要锁已释放，下次仍然可以启动。
    """

    def __init__(self, lock_path: str | Path, app_name: str = 'daily-report') -> None:
        self.lock_path = Path(lock_path)
        self.app_name = app_name
        self._fp = None

    def acquire(self) -> None:
        if os.name != 'nt':
            raise RuntimeError('SingleInstanceLock currently supports Windows only.')

        import msvcrt

        self.lock_path.parent.mkdir(parents=True, exist_ok=True)

        # a+b: 不存在则创建存在则不清空
        self._fp = open(self.lock_path, 'a+b')

        # 确保文件至少有 1 字节, 否则某些锁实现对空文件行为不稳定
        self._fp.seek(0, os.SEEK_END)
        if self._fp.tell() == 0:
            self._fp.write(b'\0')
            self._fp.flush()

        self._fp.seek(0)

        try:
            # 非阻塞锁定第 1 个字节
            msvcrt.locking(self._fp.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError as exc:
            owner = self._read_owner_safely()
            self._close_file_safely()

            if owner:
                raise SingleInstanceError(
                    f'{self.app_name} is already running. lock={self.lock_path}, owner={owner}'
                ) from exc

            raise SingleInstanceError(
                f'{self.app_name} is already running. lock={self.lock_path}'
            ) from exc

        self._write_owner()
        logger.info('Acquired single-instance lock: %s', self.lock_path)

    def release(self) -> None:
        if self._fp is None:
            return

        if os.name == 'nt':
            import msvcrt

            try:
                self._fp.seek(0)
                msvcrt.locking(self._fp.fileno(), msvcrt.LK_UNLCK, 1)
                logger.info('Released single-instance lock: %s', self.lock_path)
            except OSError:
                logger.exception('Failed to release single-instance lock: %s', self.lock_path)

        self._close_file_safely()

    def _write_owner(self) -> None:
        if self._fp is None:
            return

        owner_text = (
            f'pid={os.getpid()}\n'
            f'app={self.app_name}\n'
        )

        self._fp.seek(0)
        self._fp.truncate()
        self._fp.write(owner_text.encode('utf-8'))
        self._fp.flush()

        # 重新回到开头, 保持锁定区域对应第 1 个字节
        self._fp.seek(0)

    def _read_owner_safely(self) -> str:
        if self._fp is None:
            return ''

        try:
            self._fp.seek(0)
            data = self._fp.read(256)
            return data.decode('utf-8', errors='ignore').strip()
        except Exception:
            return ''

    def _close_file_safely(self) -> None:
        if self._fp is None:
            return

        try:
            self._fp.close()
        finally:
            self._fp = None

    def __enter__(self) -> 'SingleInstanceLock':
        self.acquire()
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc: Optional[BaseException],
        tb: Optional[TracebackType],
    ) -> None:
        self.release()