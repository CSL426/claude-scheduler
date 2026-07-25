import subprocess

import pytest

from claude_scheduler.config import SchedulerConfig
from claude_scheduler.runner import (
    ClaudeNotFoundError,
    resolve_claude,
    run_claude,
)


def test_runner_uses_argument_list_and_writes_log(tmp_path):
    executable = tmp_path / "claude"
    executable.touch()
    captured = {}

    def fake_run(command, **kwargs):
        captured["command"] = command
        captured["kwargs"] = kwargs
        return subprocess.CompletedProcess(command, 0, "hi\n", "")

    output_path = tmp_path / "state/task.log"
    config = SchedulerConfig(
        model="test-model",
        prompt="prompt with spaces; echo unsafe",
        claude_path=str(executable),
        claude_path_mode="explicit",
    )

    result = run_claude(
        config,
        process_runner=fake_run,
        output_path=output_path,
    )

    assert result == 0
    assert captured["command"] == (
        str(executable),
        "--model",
        "test-model",
        "-p",
        "prompt with spaces; echo unsafe",
    )
    assert captured["kwargs"]["check"] is False
    assert str(executable.parent) in captured["kwargs"]["env"]["PATH"]
    content = output_path.read_text(encoding="utf-8")
    assert "stdout: hi" in content
    assert "prompt with spaces" not in content


def test_runner_returns_nonzero_exit_code(tmp_path):
    executable = tmp_path / "claude"
    executable.touch()

    def fake_run(command, **kwargs):
        return subprocess.CompletedProcess(command, 7, "", "failed\n")

    result = run_claude(
        SchedulerConfig(
            claude_path=str(executable),
            claude_path_mode="explicit",
        ),
        process_runner=fake_run,
        output_path=tmp_path / "task.log",
    )

    assert result == 7
    assert "stderr: failed" in (tmp_path / "task.log").read_text(encoding="utf-8")


@pytest.mark.parametrize("claude_path_mode", ["auto", "explicit"])
def test_runner_bypasses_windows_npm_cmd_shim(
    claude_path_mode,
    tmp_path,
    monkeypatch,
):
    npm_dir = tmp_path / "npm"
    cli_script = npm_dir / "node_modules/@anthropic-ai/claude-code/cli.js"
    cli_script.parent.mkdir(parents=True)
    cli_script.touch()
    claude_shim = npm_dir / "claude.cmd"
    claude_shim.touch()
    node = tmp_path / "node.exe"
    node.touch()
    captured = {}
    monkeypatch.setattr(
        "claude_scheduler.runner.shutil.which",
        lambda name: str(claude_shim) if name == "claude" else None,
    )

    def fake_run(command, **kwargs):
        captured["command"] = command
        captured["kwargs"] = kwargs
        return subprocess.CompletedProcess(command, 0, "hi\n", "")

    config = SchedulerConfig(
        claude_path=str(claude_shim),
        claude_path_mode=claude_path_mode,
        node_path=str(node),
        prompt='unsafe %PATH% & "quoted"',
    )

    result = run_claude(
        config,
        process_runner=fake_run,
        output_path=tmp_path / "task.log",
    )

    assert result == 0
    assert captured["command"][0:2] == (str(node), str(cli_script.resolve()))
    assert "claude.cmd" not in captured["command"]
    assert captured["command"][-1] == 'unsafe %PATH% & "quoted"'
    assert str(node.parent) in captured["kwargs"]["env"]["PATH"]


def test_auto_claude_path_prefers_current_launcher(tmp_path, monkeypatch):
    cached = tmp_path / "versions/old"
    cached.parent.mkdir()
    cached.touch()
    launcher = tmp_path / "bin/claude"
    launcher.parent.mkdir()
    launcher.touch()
    monkeypatch.setattr(
        "claude_scheduler.runner.shutil.which",
        lambda name: str(launcher) if name == "claude" else None,
    )

    result = resolve_claude(
        SchedulerConfig(
            claude_path=str(cached),
            claude_path_mode="auto",
        )
    )

    assert result == str(launcher.absolute())


def test_auto_claude_path_migrates_native_version_path(
    tmp_path,
    monkeypatch,
):
    cached = (
        tmp_path
        / ".local/share/claude/versions/2.1.218"
    )
    cached.parent.mkdir(parents=True)
    cached.touch()
    launcher = tmp_path / ".local/bin/claude"
    launcher.parent.mkdir(parents=True)
    launcher.touch()
    monkeypatch.setattr(
        "claude_scheduler.runner.shutil.which",
        lambda _name: None,
    )

    result = resolve_claude(
        SchedulerConfig(
            claude_path=str(cached),
            claude_path_mode="auto",
        )
    )

    assert result == str(launcher.absolute())


def test_auto_claude_path_normalizes_versioned_path_lookup(
    tmp_path,
    monkeypatch,
):
    versioned = (
        tmp_path
        / ".local/share/claude/versions/2.1.220"
    )
    versioned.parent.mkdir(parents=True)
    versioned.touch()
    launcher = tmp_path / ".local/bin/claude"
    launcher.parent.mkdir(parents=True)
    launcher.touch()
    monkeypatch.setattr(
        "claude_scheduler.runner.shutil.which",
        lambda name: str(versioned) if name == "claude" else None,
    )

    result = resolve_claude(SchedulerConfig())

    assert result == str(launcher.absolute())


def test_auto_claude_path_falls_back_to_cached_executable(
    tmp_path,
    monkeypatch,
):
    cached = tmp_path / "custom/claude"
    cached.parent.mkdir()
    cached.touch()
    monkeypatch.setattr(
        "claude_scheduler.runner.shutil.which",
        lambda _name: None,
    )

    result = resolve_claude(
        SchedulerConfig(
            claude_path=str(cached),
            claude_path_mode="auto",
        )
    )

    assert result == str(cached)


def test_explicit_claude_path_ignores_current_launcher(
    tmp_path,
    monkeypatch,
):
    pinned = tmp_path / "pinned/claude"
    pinned.parent.mkdir()
    pinned.touch()
    current = tmp_path / "current/claude"
    current.parent.mkdir()
    current.touch()
    monkeypatch.setattr(
        "claude_scheduler.runner.shutil.which",
        lambda name: str(current) if name == "claude" else None,
    )

    result = resolve_claude(
        SchedulerConfig(
            claude_path=str(pinned),
            claude_path_mode="explicit",
        )
    )

    assert result == str(pinned)


def test_missing_explicit_claude_path_does_not_fall_back(
    tmp_path,
    monkeypatch,
):
    current = tmp_path / "current/claude"
    current.parent.mkdir()
    current.touch()
    monkeypatch.setattr(
        "claude_scheduler.runner.shutil.which",
        lambda name: str(current) if name == "claude" else None,
    )

    with pytest.raises(ClaudeNotFoundError, match="does not exist"):
        resolve_claude(
            SchedulerConfig(
                claude_path=str(tmp_path / "missing"),
                claude_path_mode="explicit",
            )
        )
