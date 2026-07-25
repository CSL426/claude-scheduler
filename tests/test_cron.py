import subprocess

import pytest

from claude_scheduler.platforms.cron import (
    BEGIN_MARKER,
    END_MARKER,
    CronBackend,
    _has_legacy_entries,
    _without_legacy_entries,
    _without_managed_block,
)


class FakeCron:
    def __init__(self, content=""):
        self.content = content
        self.calls = []

    def __call__(self, command, **kwargs):
        self.calls.append((command, kwargs))
        if command == ["crontab", "-l"]:
            return subprocess.CompletedProcess(command, 0, self.content, "")
        self.content = kwargs["input"]
        return subprocess.CompletedProcess(command, 0, "", "")


def test_install_preserves_unmanaged_crontab_and_quotes_command():
    process = FakeCron("15 1 * * * backup\n")
    backend = CronBackend(process)

    backend.install(
        ["/home/person/My Tools/ccs"],
        ("07:00", "12:05"),
    )

    assert process.content.startswith("15 1 * * * backup\n")
    assert BEGIN_MARKER in process.content
    assert (
        "00 07 * * * '/home/person/My Tools/ccs' run"
        in process.content
    )
    assert "05 12 * * *" in process.content
    assert process.content.endswith(f"{END_MARKER}\n")


def test_remove_only_managed_crontab():
    process = FakeCron(
        "15 1 * * * backup\n"
        f"{BEGIN_MARKER}\n"
        "00 07 * * * scheduler run\n"
        f"{END_MARKER}\n"
    )

    CronBackend(process).remove()

    assert process.content == "15 1 * * * backup\n"


def test_unclosed_managed_block_fails_closed():
    with pytest.raises(RuntimeError, match="missing its end marker"):
        _without_managed_block(f"existing\n{BEGIN_MARKER}\nmanaged\n")


def test_unmatched_end_marker_fails_closed():
    with pytest.raises(RuntimeError, match="missing its begin marker"):
        _without_managed_block(f"existing\n{END_MARKER}\n")


def test_install_removes_legacy_script_entry():
    process = FakeCron(
        "15 1 * * * backup\n"
        "30 7 * * * PATH=/usr/bin:$PATH /repo/claude_scheduler.sh\n"
    )

    CronBackend(process).install(["/bin/ccs"], ("07:00",))

    assert "backup" in process.content
    assert "claude_scheduler.sh" not in process.content
    assert "ccs run" in process.content


def test_legacy_detection_ignores_comments():
    content = (
        "# /repo/claude_scheduler.sh\n"
        "30 7 * * * /repo/claude_scheduler.sh\n"
    )

    assert _has_legacy_entries(content)
    assert _without_legacy_entries(content) == "# /repo/claude_scheduler.sh\n"


def test_legacy_detection_preserves_commands_that_reference_script_as_data():
    content = (
        "0 2 * * * tar -czf backup.tgz /repo/claude_scheduler.sh\n"
        "0 3 * * * diff expected /repo/claude_scheduler.sh\n"
    )

    assert not _has_legacy_entries(content)
    assert _without_legacy_entries(content) == content
