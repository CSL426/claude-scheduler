from __future__ import annotations

import csv
import io
import re
import subprocess
from collections.abc import Callable, Sequence

TASK_PREFIX = "ClaudeScheduler_"
LEGACY_TASK_PATTERN = re.compile(r"(?:^|\\)Claude_\d{4}$")
LEGACY_TASK_NAME = r"\ClaudeAutoReset"
RunProcess = Callable[..., subprocess.CompletedProcess[str]]


class WindowsTaskBackend:
    def __init__(self, process_runner: RunProcess = subprocess.run) -> None:
        self._run = process_runner

    def install(self, command: Sequence[str], times: tuple[str, ...]) -> None:
        self.remove()
        action = subprocess.list2cmdline([*command, "run"])
        for value in times:
            task_name = f"{TASK_PREFIX}{value.replace(':', '')}"
            self._run(
                [
                    "schtasks.exe",
                    "/Create",
                    "/SC",
                    "DAILY",
                    "/ST",
                    value,
                    "/TN",
                    task_name,
                    "/TR",
                    action,
                    "/F",
                ],
                capture_output=True,
                text=True,
                check=True,
            )

    def remove(self) -> None:
        for task_name in self._task_names():
            self._run(
                ["schtasks.exe", "/Delete", "/TN", task_name, "/F"],
                capture_output=True,
                text=True,
                check=True,
            )

    def status(self) -> tuple[bool, str]:
        names = self._task_names()
        if any(_is_current_task(name) for name in names):
            return True, "Task Scheduler"
        if names:
            return True, "Task Scheduler (legacy)"
        return False, "Task Scheduler"

    def _task_names(self) -> list[str]:
        result = self._run(
            ["schtasks.exe", "/Query", "/FO", "CSV", "/NH"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return []
        names = []
        for row in csv.reader(io.StringIO(result.stdout)):
            if not row:
                continue
            if _is_owned_task(row[0]):
                names.append(row[0])
        return names


def _is_current_task(name: str) -> bool:
    leaf = name.rsplit("\\", maxsplit=1)[-1]
    return leaf.startswith(TASK_PREFIX)


def _is_owned_task(name: str) -> bool:
    return (
        _is_current_task(name)
        or bool(LEGACY_TASK_PATTERN.search(name))
        or name == LEGACY_TASK_NAME
    )
