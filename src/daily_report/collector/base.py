from __future__ import annotations

import threading
from typing import Optional, Protocol


class Collector(Protocol):
    name: str

    def start(self, blocking: bool = False) -> Optional[threading.Thread]:
        ...

    def stop(self) -> None:
        ...