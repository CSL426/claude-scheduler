import json
from pathlib import Path

import pytest

from claude_scheduler import PRODUCT_NAME, __version__, cli
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
    assert load_config(path).claude_path_mode == "auto"


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
    assert config.claude_path_mode == "auto"
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
    assert "ccs install" in capsys.readouterr().out


def test_setup_uses_saved_times_as_prompt_default(tmp_path, monkeypatch):
    path = tmp_path / "config.json"
    prompts = []
    answers = iter(["", "", "", "n"])

    assert cli.main(
        [
            "--config-path",
            str(path),
            "config",
            "--time",
            "08:10",
            "--time",
            "19:20",
        ]
    ) == 0

    def answer(prompt):
        prompts.append(prompt)
        return next(answers)

    monkeypatch.setattr("builtins.input", answer)

    assert cli.main(["--config-path", str(path), "setup"]) == 0
    assert prompts[0] == "Schedule times [08:10, 19:20]: "
    assert load_config(path).times == ("08:10", "19:20")


def test_setup_reprompts_invalid_times(tmp_path, monkeypatch, capsys):
    path = tmp_path / "config.json"
    answers = iter(["25:00", "08:30", "", "", "no"])
    monkeypatch.setattr("builtins.input", lambda prompt: next(answers))

    result = cli.main(["--config-path", str(path), "setup"])

    assert result == 0
    assert load_config(path).times == ("08:30",)
    assert "Invalid schedule" in capsys.readouterr().out


def test_config_explicitly_pins_claude_path(
    tmp_path,
    monkeypatch,
):
    config_path = tmp_path / "config.json"
    executable = tmp_path / "bin/claude"
    executable.parent.mkdir()
    executable.touch()
    monkeypatch.setenv("CCS_CONFIG", str(config_path))

    result = cli.main(
        ["config", "--claude-path", str(executable)]
    )

    assert result == 0
    config = load_config(config_path)
    assert config.claude_path == str(executable.absolute())
    assert config.claude_path_mode == "explicit"


def test_config_can_switch_claude_path_back_to_auto(
    tmp_path,
    monkeypatch,
):
    config_path = tmp_path / "config.json"
    pinned = tmp_path / "pinned/claude"
    pinned.parent.mkdir()
    pinned.touch()
    current = tmp_path / "current/claude"
    current.parent.mkdir()
    current.touch()
    monkeypatch.setenv("CCS_CONFIG", str(config_path))
    monkeypatch.setattr(
        "claude_scheduler.runner.shutil.which",
        lambda name: str(current) if name == "claude" else None,
    )

    assert cli.main(
        ["config", "--claude-path", str(pinned)]
    ) == 0
    assert cli.main(["config", "--claude-path", "auto"]) == 0

    config = load_config(config_path)
    assert config.claude_path == str(current.absolute())
    assert config.claude_path_mode == "auto"


def test_config_output_includes_claude_path_mode(
    tmp_path,
    monkeypatch,
    capsys,
):
    config_path = tmp_path / "config.json"
    monkeypatch.setenv("CCS_CONFIG", str(config_path))

    assert cli.main(["config"]) == 0

    payload = capsys.readouterr().out
    assert '"claude_path_mode": "auto"' in payload


def test_status_distinguishes_cached_and_resolved_claude_paths(
    tmp_path,
    monkeypatch,
    capsys,
):
    config_path = tmp_path / "config.json"
    cached = tmp_path / "versions/old"
    cached.parent.mkdir()
    cached.touch()
    current = tmp_path / "bin/claude"
    current.parent.mkdir()
    current.touch()
    config_path.write_text(
        json.dumps(
            {
                "times": ["07:00"],
                "model": "model",
                "prompt": "prompt",
                "claude_path": str(cached),
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "claude_scheduler.runner.shutil.which",
        lambda name: str(current) if name == "claude" else None,
    )
    monkeypatch.setattr(cli, "current_backend", FakeBackend)

    assert cli.main(
        ["--config-path", str(config_path), "status"]
    ) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["claude_path"] == str(cached)
    assert payload["claude_path_mode"] == "auto"
    assert payload["resolved_claude_path"] == str(current.absolute())


def test_version_subcommand(capsys):
    result = cli.main(["version"])

    assert result == 0
    assert capsys.readouterr().out.strip() == f"{PRODUCT_NAME} {__version__}"


@pytest.mark.parametrize("argument", ["--version", "-V"])
def test_version_flags(argument, capsys):
    with pytest.raises(SystemExit) as exit_info:
        cli.main([argument])

    assert exit_info.value.code == 0
    assert capsys.readouterr().out.strip() == f"{PRODUCT_NAME} {__version__}"


def test_update_command_runs_updater(monkeypatch):
    from claude_scheduler import update

    monkeypatch.setattr(update, "run_update", lambda: 17)

    assert cli.main(["update"]) == 17


@pytest.mark.parametrize(
    ("shell", "expected"),
    [
        ("bash", "complete -o default -F _ccs_completion ccs"),
        ("powershell", "Register-ArgumentCompleter -CommandName 'ccs'"),
    ],
)
def test_completion_command(shell, expected, capsys):
    assert cli.main(["completion", shell]) == 0
    assert expected in capsys.readouterr().out


@pytest.mark.parametrize("executable_name", ["ccs", "ccs.exe"])
def test_launch_command_accepts_only_ccs_entrypoints(
    executable_name,
    tmp_path,
    monkeypatch,
):
    executable = tmp_path / executable_name
    monkeypatch.setattr(cli.sys, "argv", [str(executable)])
    monkeypatch.setattr(cli.sys, "frozen", False, raising=False)

    assert cli._launch_command() == [str(executable.resolve())]


@pytest.mark.parametrize(
    "executable_name",
    ["claude-scheduler", "claude-scheduler.exe"],
)
def test_launch_command_rejects_removed_entrypoints(
    executable_name,
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(cli.sys, "argv", [str(tmp_path / executable_name)])
    monkeypatch.setattr(cli.sys, "frozen", False, raising=False)

    with pytest.raises(RuntimeError, match="run ccs install"):
        cli._launch_command()


@pytest.mark.parametrize(
    ("entrypoint_name", "legacy_name"),
    [
        ("ccs", "claude-scheduler"),
        ("ccs.exe", "claude-scheduler.exe"),
    ],
)
def test_successful_install_can_remove_legacy_entrypoint(
    entrypoint_name,
    legacy_name,
    tmp_path,
    monkeypatch,
):
    legacy = tmp_path / legacy_name
    legacy.write_text("legacy\n", encoding="utf-8")
    monkeypatch.setattr(cli.sys, "argv", [str(tmp_path / entrypoint_name)])
    monkeypatch.setattr(cli.sys, "frozen", False, raising=False)

    cli._remove_legacy_entrypoint()

    assert not legacy.exists()


def test_legacy_entrypoint_directory_is_never_removed(tmp_path, monkeypatch):
    legacy = tmp_path / "claude-scheduler"
    legacy.mkdir()
    monkeypatch.setattr(cli.sys, "argv", [str(tmp_path / "ccs")])
    monkeypatch.setattr(cli.sys, "frozen", False, raising=False)

    cli._remove_legacy_entrypoint()

    assert legacy.is_dir()
