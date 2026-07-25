from __future__ import annotations

import os
import shutil
import subprocess
from collections.abc import Callable, Sequence
from datetime import datetime
from pathlib import Path

from .config import SchedulerConfig, log_path

RunProcess = Callable[..., subprocess.CompletedProcess[str]]


class ClaudeNotFoundError(RuntimeError):
    pass


def resolve_claude_launcher(config: SchedulerConfig) -> tuple[str, ...]:
    executable = resolve_claude(config)
    suffix = Path(executable).suffix.lower()
    if suffix in {".cmd", ".bat"}:
        cli_script = (
            Path(executable).parent
            / "node_modules"
            / "@anthropic-ai"
            / "claude-code"
            / "cli.js"
        )
        if not cli_script.is_file():
            raise ClaudeNotFoundError(
                f"Cannot safely resolve the npm Claude CLI behind {executable}."
            )
        node = resolve_node(config)
        if node is None:
            raise ClaudeNotFoundError(
                "node was not found for the npm Claude CLI. "
                "Run config --node-path PATH."
            )
        return node, str(cli_script.resolve())
    if suffix == ".ps1":
        raise ClaudeNotFoundError(
            "PowerShell Claude shims are not supported; configure claude.exe "
            "or claude.cmd."
        )
    return (executable,)


def resolve_claude(config: SchedulerConfig) -> str:
    if config.claude_path and Path(config.claude_path).is_file():
        return config.claude_path
    executable = shutil.which("claude")
    if executable:
        return str(Path(executable).resolve())
    raise ClaudeNotFoundError(
        "Claude CLI was not found. Install it or run config --claude-path PATH."
    )


def resolve_node(config: SchedulerConfig) -> str | None:
    if config.node_path and Path(config.node_path).is_file():
        return config.node_path
    executable = shutil.which("node")
    if executable:
        return str(Path(executable).resolve())
    return None


def run_claude(
    config: SchedulerConfig,
    *,
    process_runner: RunProcess = subprocess.run,
    output_path: Path | None = None,
) -> int:
    launcher = resolve_claude_launcher(config)
    command: Sequence[str] = (
        *launcher,
        "--model",
        config.model,
        "-p",
        config.prompt,
    )
    environment = _execution_environment(config)
    started = datetime.now().astimezone()
    result = process_runner(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=environment,
        check=False,
    )
    finished = datetime.now().astimezone()
    target = output_path or log_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    entries = [
        f"[{started.isoformat(timespec='seconds')}] Starting Claude CLI ({config.model})",
    ]
    if result.stdout:
        entries.append(f"stdout: {result.stdout.rstrip()}")
    if result.stderr:
        entries.append(f"stderr: {result.stderr.rstrip()}")
    entries.append(
        f"[{finished.isoformat(timespec='seconds')}] Finished with exit code "
        f"{result.returncode}"
    )
    with target.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write("\n".join(entries) + "\n")
    return result.returncode


def _execution_environment(config: SchedulerConfig) -> dict[str, str]:
    environment = os.environ.copy()
    directories = [str(Path(resolve_claude(config)).parent)]
    node = resolve_node(config)
    if node:
        directories.append(str(Path(node).parent))
    current_path = environment.get("PATH", "")
    if current_path:
        directories.append(current_path)
    environment["PATH"] = os.pathsep.join(dict.fromkeys(directories))
    return environment
