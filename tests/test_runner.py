import subprocess

from claude_scheduler.config import SchedulerConfig
from claude_scheduler.runner import run_claude


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
        SchedulerConfig(claude_path=str(executable)),
        process_runner=fake_run,
        output_path=tmp_path / "task.log",
    )

    assert result == 7
    assert "stderr: failed" in (tmp_path / "task.log").read_text(encoding="utf-8")


def test_runner_bypasses_windows_npm_cmd_shim(tmp_path):
    npm_dir = tmp_path / "npm"
    cli_script = npm_dir / "node_modules/@anthropic-ai/claude-code/cli.js"
    cli_script.parent.mkdir(parents=True)
    cli_script.touch()
    claude_shim = npm_dir / "claude.cmd"
    claude_shim.touch()
    node = tmp_path / "node.exe"
    node.touch()
    captured = {}

    def fake_run(command, **kwargs):
        captured["command"] = command
        captured["kwargs"] = kwargs
        return subprocess.CompletedProcess(command, 0, "hi\n", "")

    config = SchedulerConfig(
        claude_path=str(claude_shim),
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
