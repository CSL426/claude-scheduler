from __future__ import annotations

import sys
from collections.abc import Sequence
from typing import Protocol

from .cron import CronBackend
from .launchd import LaunchdBackend
from .windows import WindowsTaskBackend


class SchedulerBackend(Protocol):
    def install(self, command: Sequence[str], times: tuple[str, ...]) -> None: ...

    def remove(self) -> None: ...

    def status(self) -> tuple[bool, str]: ...


def current_backend(platform: str | None = None) -> SchedulerBackend:
    selected = platform or sys.platform
    if selected == "win32":
        return WindowsTaskBackend()
    if selected == "darwin":
        return LaunchdBackend()
    if selected.startswith("linux"):
        return CronBackend()
    raise RuntimeError(f"Unsupported platform: {selected}")
