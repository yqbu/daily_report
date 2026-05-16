from __future__ import annotations

import logging
import os
import shutil
import sqlite3
import tempfile
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterator, Optional, Protocol
from urllib.parse import parse_qs, unquote, urlparse

from daily_report.storage.database import (
    SqliteConnectionFactory,
    create_connection,
    default_db_path,
    init_database,
)
from daily_report.storage.storage_adapter.edge_history_store import (
    RepositoryEdgeHistoryEntryStore,
)

logger = logging.getLogger(__name__)

BROWSER_EDGE = 'edge'

# Chromium 的内部时间是从 Windows epoch, 即 1601-01-01 UTC 开始计数的微秒值
# Chromium 源码中 base::Time 也说明其内部以 Windows epoch 1601 的微秒存储
CHROME_EPOCH = datetime(1601, 1, 1, tzinfo=timezone.utc)

NOISE_SCHEMES = {
    'edge',
    'chrome',
    'devtools',
    'chrome-extension',
    'edge-extension',
    'about',
    'file',
}

EXCLUDED_PROFILE_NAMES = {
    'System Profile',
    'Guest Profile',
}


@dataclass(frozen=True)
class EdgeProfileHistory:
    profile_name: str
    history_path: Path


@dataclass
class EdgeHistoryEntryState:
    id: Optional[int]

    date: str

    browser: str
    profile_name: str

    visit_id: int
    visit_time: datetime
    visit_time_chrome: int

    title: str
    url: str
    domain: str

    transition: Optional[int]
    visit_duration_sec: float

    is_search: bool
    search_engine: Optional[str]
    search_query: Optional[str]

    is_noise: bool
    is_selected: bool


class EdgeHistoryEntryStore(Protocol):
    def save_entry(self, entry: EdgeHistoryEntryState) -> int:
        ...

    def get_latest_visit_time_chrome(
        self,
        browser: str,
        profile_name: str,
    ) -> Optional[int]:
        ...

    def close(self) -> None:
        ...


def default_edge_user_data_dir() -> Optional[Path]:
    """
    默认 Edge 用户数据目录。

    常见路径：
    %LOCALAPPDATA%\\Microsoft\\Edge\\User Data
    """
    local_app_data = os.getenv('LOCALAPPDATA')
    if not local_app_data:
        return None

    return Path(local_app_data) / 'Microsoft' / 'Edge' / 'User Data'


def find_edge_history_files(
    user_data_dir: Optional[str | Path] = None,
    profile_names: Optional[list[str]] = None,
) -> list[EdgeProfileHistory]:
    """
    查找 Edge 各 profile 下的 History 数据库。

    常见结构：
    User Data/
      Default/History
      Profile 1/History
      Profile 2/History
    """
    root = Path(user_data_dir) if user_data_dir is not None else default_edge_user_data_dir()

    if root is None or not root.exists():
        logger.warning('Edge user data directory not found: %s', root)
        return []

    allowed_profiles = set(profile_names) if profile_names else None

    histories: list[EdgeProfileHistory] = []

    for history_path in root.glob('*/History'):
        profile_name = history_path.parent.name

        if profile_name in EXCLUDED_PROFILE_NAMES:
            continue

        if allowed_profiles is not None and profile_name not in allowed_profiles:
            continue

        if history_path.is_file():
            histories.append(
                EdgeProfileHistory(
                    profile_name=profile_name,
                    history_path=history_path,
                )
            )

    histories.sort(key=lambda item: item.profile_name.lower())
    return histories


@contextmanager
def copied_history_database(history_path: Path) -> Iterator[Path]:
    """
    Edge 正在运行时 History SQLite 可能被占用。

    这里先复制 History、History-wal、History-shm 到临时目录，
    再读取副本，避免直接连接浏览器正在写入的数据库。
    """
    with tempfile.TemporaryDirectory(prefix='daily_report_edge_history_') as tmp_dir:
        tmp_root = Path(tmp_dir)
        copied_history = tmp_root / 'History'

        shutil.copy2(history_path, copied_history)

        for suffix in ('-wal', '-shm'):
            sidecar = Path(str(history_path) + suffix)
            if sidecar.exists():
                shutil.copy2(sidecar, tmp_root / f'History{suffix}')

        yield copied_history


def chrome_time_to_datetime(value: int) -> datetime:
    """
    Chromium/Edge History 中 visits.visit_time 的格式：
    从 1601-01-01 00:00:00 UTC 开始的微秒数。
    """
    dt_utc = CHROME_EPOCH + timedelta(microseconds=int(value))
    return dt_utc.astimezone().replace(tzinfo=None)


def datetime_to_chrome_time(value: datetime) -> int:
    """
    将本地 datetime 转换为 Chromium 微秒时间。
    """
    if value.tzinfo is None:
        value = value.astimezone()

    value_utc = value.astimezone(timezone.utc)
    delta = value_utc - CHROME_EPOCH
    return int(delta.total_seconds() * 1_000_000)


def normalize_text(value: Optional[str]) -> str:
    if value is None:
        return ''

    return str(value).replace('\x00', '').strip()


def extract_domain(url: str) -> str:
    try:
        parsed = urlparse(url)
    except Exception:
        return ''

    host = (parsed.hostname or '').lower().strip()
    if host.startswith('www.'):
        host = host[4:]

    return host


def _first_query_param(params: dict[str, list[str]], keys: tuple[str, ...]) -> Optional[str]:
    for key in keys:
        values = params.get(key)
        if not values:
            continue

        value = unquote(values[0]).strip()
        if value:
            return value

    return None


def extract_search_info(url: str) -> tuple[bool, Optional[str], Optional[str]]:
    """
    从常见搜索引擎 URL 中提取搜索词。

    第一版只做高价值搜索引擎：
    - Bing: q
    - Google: q
    - Baidu: wd / word
    - Sogou: query / keyword
    - 360: q
    - DuckDuckGo: q
    """
    try:
        parsed = urlparse(url)
    except Exception:
        return False, None, None

    host = (parsed.hostname or '').lower()
    params = parse_qs(parsed.query)

    if not host:
        return False, None, None

    if host == 'bing.com' or host.endswith('.bing.com'):
        query = _first_query_param(params, ('q',))
        return (True, 'Bing', query) if query else (False, None, None)

    if host.startswith('google.') or '.google.' in host:
        query = _first_query_param(params, ('q',))
        return (True, 'Google', query) if query else (False, None, None)

    if host == 'baidu.com' or host.endswith('.baidu.com'):
        query = _first_query_param(params, ('wd', 'word'))
        return (True, 'Baidu', query) if query else (False, None, None)

    if host == 'sogou.com' or host.endswith('.sogou.com'):
        query = _first_query_param(params, ('query', 'keyword'))
        return (True, 'Sogou', query) if query else (False, None, None)

    if host == 'so.com' or host.endswith('.so.com'):
        query = _first_query_param(params, ('q',))
        return (True, '360 Search', query) if query else (False, None, None)

    if host == 'duckduckgo.com' or host.endswith('.duckduckgo.com'):
        query = _first_query_param(params, ('q',))
        return (True, 'DuckDuckGo', query) if query else (False, None, None)

    return False, None, None


def is_noise_url(url: str, title: str) -> bool:
    """
    标记噪声记录。

    注意：这里不直接丢弃，而是写入 is_noise=1，方便后续排查。
    """
    if not url:
        return True

    try:
        parsed = urlparse(url)
    except Exception:
        return True

    scheme = parsed.scheme.lower()

    if scheme in NOISE_SCHEMES:
        return True

    if scheme not in {'http', 'https'}:
        return True

    if not parsed.netloc:
        return True

    # 标题为空不一定是噪声, 例如刚打开的页面可能标题尚未写入
    # 所以这里只做非常保守的过滤
    return False


def read_history_rows(
    copied_db_path: Path,
    *,
    min_visit_time_chrome: int,
    limit: int,
) -> list[sqlite3.Row]:
    """
    从复制后的 Edge History SQLite 中读取新增访问记录。
    """
    uri = f'file:{copied_db_path.as_posix()}?mode=ro'

    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row

    try:
        conn.execute('PRAGMA query_only=ON;')

        cursor = conn.execute(
            """
            SELECT
                visits.id AS visit_id,
                visits.visit_time AS visit_time_chrome,
                visits.transition AS transition,
                COALESCE(visits.visit_duration, 0) AS visit_duration,
                COALESCE(urls.title, '') AS title,
                urls.url AS url
            FROM visits
            JOIN urls ON urls.id = visits.url
            WHERE visits.visit_time > ?
            ORDER BY visits.visit_time ASC
            LIMIT ?
            """,
            (int(min_visit_time_chrome), int(limit)),
        )

        return list(cursor.fetchall())
    finally:
        conn.close()


class EdgeHistoryCollector:
    """
    Edge 浏览历史采集器。

    设计目标：
    1. 不直接读取正在使用的 History 数据库，而是复制副本；
    2. 只增量读取 visits.visit_time > last_visit_time_chrome 的记录；
    3. 提取 domain / search_engine / search_query；
    4. 噪声记录不丢弃，只标记 is_noise；
    5. 默认不高频轮询，日报场景 60 秒一次足够。
    """

    name: str = 'edge_history'

    def __init__(
        self,
        store: EdgeHistoryEntryStore,
        poll_interval_sec: float = 60.0,
        initial_lookback_hours: int = 24,
        max_rows_per_profile: int = 500,
        edge_user_data_dir: Optional[str | Path] = None,
        profile_names: Optional[list[str]] = None,
    ):
        self.store = store
        self.poll_interval_sec = poll_interval_sec
        self.initial_lookback_hours = initial_lookback_hours
        self.max_rows_per_profile = max_rows_per_profile
        self.edge_user_data_dir = Path(edge_user_data_dir) if edge_user_data_dir else None
        self.profile_names = profile_names

        self._stop_event = threading.Event()
        self._last_visit_time_by_profile: dict[str, int] = {}

    def start(self, blocking: bool = False) -> Optional[threading.Thread]:
        if blocking:
            self.run_forever()
            return None

        thread = threading.Thread(
            target=self.run_forever,
            name='EdgeHistoryCollector',
            daemon=True,
        )
        thread.start()
        return thread

    def stop(self) -> None:
        self._stop_event.set()

    def run_forever(self) -> None:
        logger.info('EdgeHistoryCollector started.')

        try:
            while not self._stop_event.is_set():
                try:
                    self.poll_once()
                except Exception:
                    logger.exception('EdgeHistoryCollector poll failed.')

                self._stop_event.wait(self.poll_interval_sec)
        finally:
            self._close_store()
            logger.info('EdgeHistoryCollector stopped.')

    def poll_once(self) -> None:
        profiles = find_edge_history_files(
            user_data_dir=self.edge_user_data_dir,
            profile_names=self.profile_names,
        )

        if not profiles:
            logger.debug('No Edge history profiles found.')
            return

        total_saved = 0

        for profile in profiles:
            saved = self._poll_profile(profile)
            total_saved += saved

        if total_saved > 0:
            logger.info('Saved %s Edge history entries.', total_saved)

    def _poll_profile(self, profile: EdgeProfileHistory) -> int:
        min_visit_time_chrome = self._get_min_visit_time_chrome(profile.profile_name)

        try:
            with copied_history_database(profile.history_path) as copied_db_path:
                rows = read_history_rows(
                    copied_db_path,
                    min_visit_time_chrome=min_visit_time_chrome,
                    limit=self.max_rows_per_profile,
                )
        except FileNotFoundError:
            logger.debug('Edge history file disappeared: %s', profile.history_path)
            return 0
        except PermissionError:
            logger.debug('No permission to copy Edge history: %s', profile.history_path)
            return 0
        except sqlite3.DatabaseError:
            logger.debug(
                'Failed to read copied Edge history database: %s',
                profile.history_path,
                exc_info=True,
            )
            return 0
        except Exception:
            logger.debug(
                'Failed to copy/read Edge history: %s',
                profile.history_path,
                exc_info=True,
            )
            return 0

        if not rows:
            return 0

        saved_count = 0
        max_seen = min_visit_time_chrome

        for row in rows:
            entry = self._build_entry(profile.profile_name, row)

            entry.id = self.store.save_entry(entry)
            saved_count += 1

            max_seen = max(max_seen, entry.visit_time_chrome)

            logger.debug(
                'Saved Edge history entry id=%s profile=%s domain=%s title=%s',
                entry.id,
                entry.profile_name,
                entry.domain,
                entry.title,
            )

        self._last_visit_time_by_profile[profile.profile_name] = max_seen
        return saved_count

    def _get_min_visit_time_chrome(self, profile_name: str) -> int:
        cached = self._last_visit_time_by_profile.get(profile_name)
        if cached is not None:
            return cached

        latest = self.store.get_latest_visit_time_chrome(
            BROWSER_EDGE,
            profile_name,
        )

        if latest is not None:
            self._last_visit_time_by_profile[profile_name] = latest
            return latest

        start_time = datetime.now() - timedelta(hours=self.initial_lookback_hours)
        initial = datetime_to_chrome_time(start_time)

        self._last_visit_time_by_profile[profile_name] = initial
        return initial

    def _build_entry(
        self,
        profile_name: str,
        row: sqlite3.Row,
    ) -> EdgeHistoryEntryState:
        visit_id = int(row['visit_id'])
        visit_time_chrome = int(row['visit_time_chrome'])
        visit_time = chrome_time_to_datetime(visit_time_chrome)

        title = normalize_text(row['title'])
        url = normalize_text(row['url'])
        domain = extract_domain(url)

        transition = row['transition']
        transition = int(transition) if transition is not None else None

        visit_duration = row['visit_duration']
        visit_duration_sec = float(visit_duration or 0) / 1_000_000.0

        is_search, search_engine, search_query = extract_search_info(url)
        is_noise = is_noise_url(url, title)

        return EdgeHistoryEntryState(
            id=None,
            date=visit_time.date().isoformat(),
            browser=BROWSER_EDGE,
            profile_name=profile_name,
            visit_id=visit_id,
            visit_time=visit_time,
            visit_time_chrome=visit_time_chrome,
            title=title,
            url=url,
            domain=domain,
            transition=transition,
            visit_duration_sec=visit_duration_sec,
            is_search=is_search,
            search_engine=search_engine,
            search_query=search_query,
            is_noise=is_noise,
            is_selected=not is_noise,
        )

    def _close_store(self) -> None:
        close = getattr(self.store, 'close', None)
        if callable(close):
            close()


def debug_main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] %(levelname)s %(name)s: %(message)s',
    )

    db_path = default_db_path()
    logger.info('SQLite database path: %s', db_path)

    conn = create_connection(db_path)
    try:
        init_database(conn)
    finally:
        conn.close()

    connection_factory = SqliteConnectionFactory(db_path)
    store = RepositoryEdgeHistoryEntryStore(connection_factory)

    collector = EdgeHistoryCollector(
        store=store,
        poll_interval_sec=60.0,
        initial_lookback_hours=24,
        max_rows_per_profile=500,
    )

    try:
        collector.run_forever()
    except KeyboardInterrupt:
        collector.stop()


if __name__ == '__main__':
    debug_main()