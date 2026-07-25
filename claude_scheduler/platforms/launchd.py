from __future__ import annotations

import os
import plistlib
import subprocess
from collections.abc import Callable, Sequence
from pathlib import Path

from ..config import state_dir
from .cron import CronBackend

LABEL = "com.ac-spark.claude-scheduler"
RunProcess = Callable[..., subprocess.CompletedProcess[str]]


class LaunchdBackend:
    def __init__(
        self,
        process_runner: RunProcess = subprocess.run,
        agents_dir: Path | None = None,
        legacy_cron: CronBackend | None = None,
    ) -> None:
        self._run = process_runner
        self._agents_dir = agents_dir or Path.home() / "Library/LaunchAgents"
        self._legacy_cron = legacy_cron or CronBackend()

    @property
    def plist_path(self) -> Path:
        return self._agents_dir / f"{LABEL}.plist"

    def install(self, command: Sequence[str], times: tuple[str, ...]) -> None:
        self._legacy_cron.remove_legacy()
        self._agents_dir.mkdir(parents=True, exist_ok=True)
        log_dir = state_dir()
        log_dir.mkdir(parents=True, exist_ok=True)
        intervals = []
        for value in times:
            hour, minute = value.split(":")
            intervals.append({"Hour": int(hour), "Minute": int(minute)})
        payload = {
            "Label": LABEL,
            "ProgramArguments": [*command, "run"],
            "RunAtLoad": False,
            "StartCalendarInterval": intervals,
            "StandardOutPath": str(log_dir / "launchd.stdout.log"),
            "StandardErrorPath": str(log_dir / "launchd.stderr.log"),
        }
        self.plist_path.write_bytes(plistlib.dumps(payload, sort_keys=True))
        domain = f"gui/{os.getuid()}"
        self._run(
            ["launchctl", "bootout", domain, str(self.plist_path)],
            capture_output=True,
            text=True,
            check=False,
        )
        self._run(
            ["launchctl", "bootstrap", domain, str(self.plist_path)],
            capture_output=True,
            text=True,
            check=True,
        )

    def remove(self) -> None:
        self._legacy_cron.remove_legacy()
        domain = f"gui/{os.getuid()}"
        self._run(
            ["launchctl", "bootout", domain, str(self.plist_path)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.plist_path.unlink(missing_ok=True)

    def status(self) -> tuple[bool, str]:
        if not self.plist_path.exists():
            return False, "launchd"
        result = self._run(
            ["launchctl", "print", f"gui/{os.getuid()}/{LABEL}"],
            capture_output=True,
            text=True,
            check=False,
        )
        return result.returncode == 0, "launchd"
