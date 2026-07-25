from pathlib import Path

from claude_scheduler import cli
from claude_scheduler.config import load_config


class FakeBackend:
    def __init__(self):
        self.installed = None

    def install(self, command, times):
        self.installed = (command, times)

    def remove(self):
        pass

    def status(self):
        return self.installed is not None, "test scheduler"


def test_config_command_saves_repeated_times(tmp_path, monkeypatch):
    path = tmp_path / "config.json"
    monkeypatch.setenv("CLAUDE_SCHEDULER_CONFIG", str(path))

    result = cli.main(["config", "--time", "08:00", "--time", "13:30"])

    assert result == 0
    assert load_config(path).times == ("08:00", "13:30")


def test_install_resolves_claude_and_uses_backend(tmp_path, monkeypatch):
    path = tmp_path / "config.json"
    executable = tmp_path / "bin/claude"
    executable.parent.mkdir()
    executable.touch()
    backend = FakeBackend()
    monkeypatch.setenv("CLAUDE_SCHEDULER_CONFIG", str(path))
    monkeypatch.setenv("CLAUDE_SCHEDULER_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setattr(
        "claude_scheduler.runner.shutil.which",
        lambda name: str(executable) if name == "claude" else None,
    )
    monkeypatch.setattr(cli, "current_backend", lambda: backend)
    monkeypatch.setattr(cli, "_launch_command", lambda: ["/bin/scheduler"])

    result = cli.main(["install"])

    assert result == 0
    assert backend.installed == (
        [
            "/bin/scheduler",
            "--config-path",
            str(path),
            "--state-dir",
            str(tmp_path / "state"),
        ],
        ("07:00", "12:05", "17:10", "22:15"),
    )
    assert load_config(path).claude_path == str(executable.resolve())


def test_config_rejects_missing_claude_path(tmp_path, monkeypatch, capsys):
    config = tmp_path / "config.json"
    monkeypatch.setenv("CLAUDE_SCHEDULER_CONFIG", str(config))

    result = cli.main(
        ["config", "--claude-path", str(Path("missing-claude"))]
    )

    assert result == 1
    assert "does not exist" in capsys.readouterr().err
    assert not config.exists()
