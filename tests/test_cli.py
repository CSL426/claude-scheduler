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


def test_setup_interactively_saves_and_installs(tmp_path, monkeypatch):
    path = tmp_path / "config.json"
    state = tmp_path / "state"
    executable = tmp_path / "bin/claude"
    executable.parent.mkdir()
    executable.touch()
    backend = FakeBackend()
    answers = iter(
        [
            "06:30, 18:45",
            "",
            "reply with hi",
            "yes",
        ]
    )
    monkeypatch.setattr("builtins.input", lambda prompt: next(answers))
    monkeypatch.setattr(
        "claude_scheduler.runner.shutil.which",
        lambda name: str(executable) if name == "claude" else None,
    )
    monkeypatch.setattr(cli, "current_backend", lambda: backend)
    monkeypatch.setattr(cli, "_launch_command", lambda: ["/bin/scheduler"])

    result = cli.main(
        [
            "--config-path",
            str(path),
            "--state-dir",
            str(state),
            "setup",
        ]
    )

    assert result == 0
    config = load_config(path)
    assert config.times == ("06:30", "18:45")
    assert config.model == "claude-haiku-4-5-20251001"
    assert config.prompt == "reply with hi"
    assert config.claude_path == str(executable.resolve())
    assert backend.installed == (
        [
            "/bin/scheduler",
            "--config-path",
            str(path),
            "--state-dir",
            str(state),
        ],
        ("06:30", "18:45"),
    )


def test_setup_can_save_without_installing(tmp_path, monkeypatch, capsys):
    path = tmp_path / "config.json"
    answers = iter(["09:15 21:45", "", "", "n"])
    monkeypatch.setattr("builtins.input", lambda prompt: next(answers))

    result = cli.main(["--config-path", str(path), "setup"])

    assert result == 0
    assert load_config(path).times == ("09:15", "21:45")
    assert "claude-scheduler install" in capsys.readouterr().out


def test_setup_reprompts_invalid_times(tmp_path, monkeypatch, capsys):
    path = tmp_path / "config.json"
    answers = iter(["25:00", "08:30", "", "", "no"])
    monkeypatch.setattr("builtins.input", lambda prompt: next(answers))

    result = cli.main(["--config-path", str(path), "setup"])

    assert result == 0
    assert load_config(path).times == ("08:30",)
    assert "Invalid schedule" in capsys.readouterr().out
