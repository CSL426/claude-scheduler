from __future__ import annotations

import re
import shlex
import subprocess
from collections.abc import Callable, Sequence

BEGIN_MARKER = "# BEGIN claude-scheduler"
END_MARKER = "# END claude-scheduler"
LEGACY_SCRIPT = "claude_scheduler.sh"
SHELL_ASSIGNMENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*=.*")
RunProcess = Callable[..., subprocess.CompletedProcess[str]]


class CronBackend:
    def __init__(self, process_runner: RunProcess = subprocess.run) -> None:
        self._run = process_runner

    def install(self, command: Sequence[str], times: tuple[str, ...]) -> None:
        existing = self._read()
        retained = _without_legacy_entries(_without_managed_block(existing))
        invocation = " ".join(shlex.quote(part) for part in (*command, "run"))
        entries = [BEGIN_MARKER]
        for value in times:
            hour, minute = value.split(":")
            entries.append(f"{minute} {hour} * * * {invocation}")
        entries.append(END_MARKER)
        content = "\n".join([part for part in (retained.rstrip(), *entries) if part])
        self._run(
            ["crontab", "-"],
            input=content + "\n",
            capture_output=True,
            text=True,
            check=True,
        )

    def remove(self) -> None:
        existing = self._read()
        retained = _without_legacy_entries(_without_managed_block(existing))
        if retained == existing:
            return
        self._run(
            ["crontab", "-"],
            input=retained,
            capture_output=True,
            text=True,
            check=True,
        )

    def status(self) -> tuple[bool, str]:
        content = self._read()
        _without_managed_block(content)
        installed = BEGIN_MARKER in content and END_MARKER in content
        if installed:
            return True, "cron"
        if _has_legacy_entries(content):
            return True, "cron (legacy)"
        return False, "cron"

    def remove_legacy(self) -> None:
        existing = self._read()
        retained = _without_legacy_entries(existing)
        if retained == existing:
            return
        self._run(
            ["crontab", "-"],
            input=retained,
            capture_output=True,
            text=True,
            check=True,
        )

    def _read(self) -> str:
        result = self._run(
            ["crontab", "-l"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode not in (0, 1):
            raise RuntimeError(result.stderr.strip() or "Cannot read crontab")
        return result.stdout if result.returncode == 0 else ""


def _without_managed_block(content: str) -> str:
    lines = content.splitlines()
    retained: list[str] = []
    inside = False
    for line in lines:
        if line == BEGIN_MARKER:
            if inside:
                raise RuntimeError("Managed cron block has duplicate begin markers")
            inside = True
            continue
        if line == END_MARKER:
            if not inside:
                raise RuntimeError("Managed cron block is missing its begin marker")
            inside = False
            continue
        if not inside:
            retained.append(line)
    if inside:
        raise RuntimeError("Managed cron block is missing its end marker")
    return "\n".join(retained).rstrip() + ("\n" if retained else "")


def _without_legacy_entries(content: str) -> str:
    retained = [
        line
        for line in content.splitlines()
        if not _is_legacy_entry(line)
    ]
    return "\n".join(retained).rstrip() + ("\n" if retained else "")


def _has_legacy_entries(content: str) -> bool:
    return any(_is_legacy_entry(line) for line in content.splitlines())


def _is_legacy_entry(line: str) -> bool:
    stripped = line.lstrip()
    if not stripped or stripped.startswith("#"):
        return False
    fields = stripped.split(maxsplit=5)
    if len(fields) != 6:
        return False
    try:
        command = shlex.split(fields[5])
    except ValueError:
        return False
    while command and SHELL_ASSIGNMENT.fullmatch(command[0]):
        command.pop(0)
    if not command:
        return False
    return command[0].rsplit("/", maxsplit=1)[-1] == LEGACY_SCRIPT
