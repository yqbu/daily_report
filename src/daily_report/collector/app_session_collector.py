from __future__ import annotations

import ctypes
import logging
import threading
import time
from ctypes import wintypes
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, Protocol

import psutil
import win32gui
import win32process

from daily_report.storage.database import create_connection, default_db_path, init_database, SqliteConnectionFactory
from daily_report.storage.storage_adapter.app_session_store import RepositoryForegroundSessionStore

logger = logging.getLogger(__name__)


# =========================
# Windows idle time
# =========================

class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [
        ('cbSize', wintypes.UINT),
        ('dwTime', wintypes.DWORD),
    ]


def get_idle_seconds() -> float:
    """
    返回用户距离上一次键盘/鼠标输入过去了多少秒
    用于判断当前是否处于挂机状态
    """
    lii = LASTINPUTINFO()
    lii.cbSize = ctypes.sizeof(LASTINPUTINFO)

    if not ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii)):
        return 0.0

    tick_count = ctypes.windll.kernel32.GetTickCount64()
    idle_ms = tick_count - lii.dwTime
    return max(float(idle_ms) / 1000.0, 0.0)


# =========================
# Data models
# =========================

@dataclass
class ForegroundSnapshot:
    hwnd: int
    pid: int
    process_name: str
    app_name: str
    exe_path: Optional[str]
    window_title: str
    captured_at: datetime
    idle_seconds: float
    is_active: bool
    track_enabled: bool = True


@dataclass
class AppSessionState:
    id: Optional[int]
    date: str
    app_name: str
    process_name: str
    pid: int
    hwnd: int
    exe_path: Optional[str]
    window_title: str
    start_time: datetime
    end_time: datetime
    duration_sec: float
    active_duration_sec: float
    is_active: bool
    track_enabled: bool = True


# =========================
# Store protocol
# =========================

class ForegroundSessionStore(Protocol):
    def prepare_snapshot(self, snapshot: ForegroundSnapshot) -> ForegroundSnapshot:
        ...

    def open_session(self, session: AppSessionState) -> int:
        ...

    def update_session(self, session: AppSessionState) -> None:
        ...

    def close_session(self, session: AppSessionState) -> None:
        ...


# =========================
# Foreground window utilities
# =========================

_APP_NAME_OVERRIDES = {
    'code.exe': 'Visual Studio Code',
    'cursor.exe': 'Cursor',
    'msedge.exe': 'Microsoft Edge',
    'chrome.exe': 'Google Chrome',
    'firefox.exe': 'Firefox',
    'pycharm64.exe': 'PyCharm',
    'idea64.exe': 'IDEA',
    'wechat.exe': '微信',
    'weixin.exe': '微信',
    'wxwork.exe': '企业微信',
    'dingtalk.exe': '钉钉',
    'feishu.exe': '飞书',
    'explorer.exe': 'File Explorer',
    'cmd.exe': 'Command Prompt',
    'powershell.exe': 'PowerShell',
    'windowsterminal.exe': 'Windows Terminal',
    'uSmartView_VDI_Client.exe': '云桌面'
}


def friendly_app_name(process_name: str, exe_path: Optional[str]) -> str:
    """
    生成更适合展示的应用名
    第一版先用进程名映射即可, 后续可以改成读取 exe 的 FileDescription
    """
    key = process_name.lower()

    if key in _APP_NAME_OVERRIDES:
        return _APP_NAME_OVERRIDES[key]

    if exe_path:
        stem = Path(exe_path).stem
        if stem:
            return stem

    return process_name


def read_foreground_snapshot(
    idle_threshold_sec: int = 180,
) -> Optional[ForegroundSnapshot]:
    """
    读取当前前台窗口快照
    返回 None 表示当前没有有效前台窗口
    """
    hwnd = win32gui.GetForegroundWindow()

    if not hwnd:
        return None

    try:
        title = win32gui.GetWindowText(hwnd).strip()
    except Exception:
        title = ''

    try:
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
    except Exception:
        return None

    if not pid:
        return None

    try:
        proc = psutil.Process(pid)
        process_name = proc.name()
        try:
            exe_path = proc.exe()
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            exe_path = None
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return None

    idle_seconds = get_idle_seconds()
    is_active = idle_seconds < idle_threshold_sec

    app_name = friendly_app_name(process_name, exe_path)

    return ForegroundSnapshot(
        hwnd=int(hwnd),
        pid=int(pid),
        process_name=process_name,
        app_name=app_name,
        exe_path=exe_path,
        window_title=title,
        captured_at=datetime.now(),
        idle_seconds=idle_seconds,
        is_active=is_active,
    )


# =========================
# Collector
# =========================

class ForegroundCollector:
    """
    前台应用采集器

    设计目标:
    1. 不依赖 GUI
    2. 只负责采集并写入 store
    3. 通过 stop_event 安全停止
    """
    name: str = 'foreground'

    def __init__(
        self,
        store: ForegroundSessionStore,
        poll_interval_sec: float = 2.0,
        idle_threshold_sec: int = 180,
        split_on_title_change: bool = True,
        min_title_change_interval_sec: float = 2.0,
        flush_interval_sec: float = 10.0,
    ):
        self.store = store
        self.poll_interval_sec = poll_interval_sec
        self.idle_threshold_sec = idle_threshold_sec
        self.split_on_title_change = split_on_title_change
        self.min_title_change_interval_sec = min_title_change_interval_sec
        self.flush_interval_sec = flush_interval_sec

        self._stop_event = threading.Event()
        self._current: Optional[AppSessionState] = None
        self._last_monotonic: Optional[float] = None
        self._last_flush_monotonic: Optional[float] = None

    def start(self, blocking: bool = False) -> Optional[threading.Thread]:
        """
        blocking=True: 当前线程持续运行
        blocking=False: 启动后台线程并返回
        """
        if blocking:
            self.run_forever()
            return None

        thread = threading.Thread(
            target=self.run_forever,
            name='ForegroundCollector',
            daemon=True,
        )
        thread.start()
        return thread

    def stop(self) -> None:
        self._stop_event.set()

    def _close_store(self) -> None:
        close = getattr(self.store, 'close', None)
        if callable(close):
            close()

    def run_forever(self) -> None:
        logger.info('ForegroundCollector started.')

        self._last_monotonic = time.monotonic()
        self._last_flush_monotonic = self._last_monotonic

        try:
            while not self._stop_event.is_set():
                try:
                    self.poll_once()
                except Exception:
                    logger.exception('ForegroundCollector poll failed.')

                self._stop_event.wait(self.poll_interval_sec)

        finally:
            self._close_current_session()
            self._close_store()
            logger.info('ForegroundCollector stopped.')

    def poll_once(self) -> None:
        now_wall = datetime.now()
        now_mono = time.monotonic()

        if self._last_monotonic is None:
            elapsed_sec = 0.0
        else:
            elapsed_sec = max(now_mono - self._last_monotonic, 0.0)

        snapshot = read_foreground_snapshot(
            idle_threshold_sec=self.idle_threshold_sec,
        )
        if snapshot is not None:
            snapshot = self._prepare_snapshot(snapshot)
        # logger.info(
        #     'snapshot: %s | %s',
        #     snapshot.app_name,
        #     snapshot.window_title,
        # )

        # 当前没有有效窗口
        if snapshot is None:
            self._accumulate_current(
                now_wall=now_wall,
                elapsed_sec=elapsed_sec,
                is_active=False,
            )
            self._flush_current_if_needed(now_mono, force=True)
            self._last_monotonic = now_mono
            return

        # 跨天时切分 session, 方便日报按天统计
        if self._current is not None and self._current.date != now_wall.date().isoformat():
            self._accumulate_current(
                now_wall=now_wall,
                elapsed_sec=elapsed_sec,
                is_active=snapshot.is_active,
            )
            self._close_current_session()
            self._open_new_session(snapshot)
            self._last_monotonic = now_mono
            return

        # 第一次采集
        if self._current is None:
            self._open_new_session(snapshot)
            self._last_monotonic = now_mono
            return

        # 先把上一个采样间隔计入当前 session
        self._accumulate_current(
            now_wall=now_wall,
            elapsed_sec=elapsed_sec,
            is_active=snapshot.is_active,
        )

        # 判断是否切换了应用/窗口
        if self._should_switch_session(snapshot):
            self._close_current_session()
            self._open_new_session(snapshot)
        else:
            self._current.is_active = snapshot.is_active
            self._flush_current_if_needed(now_mono)

        self._last_monotonic = now_mono

    def _prepare_snapshot(self, snapshot: ForegroundSnapshot) -> ForegroundSnapshot:
        prepare = getattr(self.store, 'prepare_snapshot', None)
        if callable(prepare):
            return prepare(snapshot)
        return snapshot

    def _open_new_session(self, snapshot: ForegroundSnapshot) -> None:
        now = snapshot.captured_at

        session = AppSessionState(
            id=None,
            hwnd=snapshot.hwnd,
            date=now.date().isoformat(),
            app_name=snapshot.app_name,
            process_name=snapshot.process_name,
            pid=snapshot.pid,
            exe_path=snapshot.exe_path,
            window_title=snapshot.window_title,
            start_time=now,
            end_time=now,
            duration_sec=0.0,
            active_duration_sec=0.0,
            is_active=snapshot.is_active,
            track_enabled=snapshot.track_enabled,
        )

        logger.info(
            'Opening foreground session: app=%s pid=%s hwnd=%s title=%s',
            session.app_name,
            session.pid,
            session.hwnd,
            session.window_title,
        )

        session.id = self.store.open_session(session)
        self._current = session
        self._last_flush_monotonic = time.monotonic()

        logger.debug(
            'Open session: %s | %s',
            session.app_name,
            session.window_title,
        )

    def _close_current_session(self) -> None:
        if self._current is None:
            return

        try:
            self.store.close_session(self._current)
            logger.debug(
                'Close session: %s | %.1fs active %.1fs | %s',
                self._current.app_name,
                self._current.duration_sec,
                self._current.active_duration_sec,
                self._current.window_title,
            )
        finally:
            self._current = None

    def _accumulate_current(
        self,
        now_wall: datetime,
        elapsed_sec: float,
        is_active: bool,
    ) -> None:
        if self._current is None:
            return

        self._current.end_time = now_wall
        self._current.duration_sec += elapsed_sec

        if is_active:
            self._current.active_duration_sec += elapsed_sec

        self._current.is_active = is_active

    def _flush_current_if_needed(
        self,
        now_mono: float,
        force: bool = False,
    ) -> None:
        if self._current is None:
            return

        if self._last_flush_monotonic is None:
            self._last_flush_monotonic = now_mono

        should_flush = (
            force
            or now_mono - self._last_flush_monotonic >= self.flush_interval_sec
        )

        if should_flush:
            self.store.update_session(self._current)
            self._last_flush_monotonic = now_mono

    def _should_switch_session(self, snapshot: ForegroundSnapshot) -> bool:
        if self._current is None:
            return True

        # 窗口句柄变了, 说明前台窗口变了
        if snapshot.hwnd != self._current.hwnd:
            return True

        # 进程变了, 一定切 session
        if snapshot.pid != self._current.pid:
            return True

        # 进程名变了, 也切
        if snapshot.process_name != self._current.process_name:
            return True

        if not self.split_on_title_change:
            return False

        # 标题变化频繁时, 如果当前 session 太短, 可以不立刻切, 避免碎片过多
        title_changed = snapshot.window_title != self._current.window_title

        if not title_changed:
            return False

        current_duration = self._current.duration_sec

        if current_duration < self.min_title_change_interval_sec:
            # 短时间内标题变化, 直接更新标题, 不切 session
            self._current.window_title = snapshot.window_title
            return False

        return True


# =========================
# Minimal runnable entry
# =========================
def debug_main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] %(levelname)s %(name)s: %(message)s',
    )

    db_path = default_db_path()
    logger.info('SQLite database path: %s', db_path)

    # 关键: 先初始化数据库
    conn = create_connection(db_path)
    try:
        init_database(conn)
    finally:
        conn.close()

    connection_factory = SqliteConnectionFactory(db_path)
    store = RepositoryForegroundSessionStore(connection_factory)

    collector = ForegroundCollector(
        store=store,
        poll_interval_sec=2.0,
        idle_threshold_sec=180,
        split_on_title_change=True,
        min_title_change_interval_sec=2.0,
        flush_interval_sec=10.0,
    )

    try:
        collector.run_forever()
    except KeyboardInterrupt:
        collector.stop()

if __name__ == '__main__':
    debug_main()
