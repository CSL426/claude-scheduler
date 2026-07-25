import plistlib
import subprocess

from claude_scheduler.platforms.launchd import LABEL, LaunchdBackend


class FakeLaunchctl:
    def __init__(self):
        self.calls = []

    def __call__(self, command, **kwargs):
        self.calls.append((command, kwargs))
        return subprocess.CompletedProcess(command, 0, "", "")


class FakeLegacyCron:
    def __init__(self):
        self.removed = False

    def remove_legacy(self):
        self.removed = True


def test_launchd_writes_calendar_intervals(tmp_path, monkeypatch):
    monkeypatch.setenv("CLAUDE_SCHEDULER_STATE_DIR", str(tmp_path / "state"))
    process = FakeLaunchctl()
    legacy_cron = FakeLegacyCron()
    backend = LaunchdBackend(
        process,
        agents_dir=tmp_path / "agents",
        legacy_cron=legacy_cron,
        user_id=501,
    )

    backend.install(["/Applications/Claude Scheduler"], ("07:00", "12:05"))

    payload = plistlib.loads(backend.plist_path.read_bytes())
    assert payload["Label"] == LABEL
    assert payload["ProgramArguments"] == [
        "/Applications/Claude Scheduler",
        "run",
    ]
    assert payload["StartCalendarInterval"] == [
        {"Hour": 7, "Minute": 0},
        {"Hour": 12, "Minute": 5},
    ]
    assert legacy_cron.removed
    assert process.calls[-1][0][0:2] == ["launchctl", "bootstrap"]
    assert process.calls[-1][0][2] == "gui/501"


def test_launchd_remove_deletes_plist(tmp_path):
    process = FakeLaunchctl()
    backend = LaunchdBackend(
        process,
        agents_dir=tmp_path,
        legacy_cron=FakeLegacyCron(),
        user_id=501,
    )
    backend.plist_path.write_text("placeholder", encoding="utf-8")

    backend.remove()

    assert not backend.plist_path.exists()
    assert process.calls[0][0][0:3] == ["launchctl", "bootout", "gui/501"]
