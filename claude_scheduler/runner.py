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
    if config.claude_path_mode == "explicit":
        if config.claude_path and Path(config.claude_path).is_file():
            return config.claude_path
        raise ClaudeNotFoundError(
            f"Configured Claude CLI does not exist: {config.claude_path}"
        )
    executable = _discover_claude(config)
    if executable is not None:
        return executable
    raise ClaudeNotFoundError(
        "Claude CLI was not found. Install it or run config --claude-path PATH."
    )


def _discover_claude(config: SchedulerConfig) -> str | None:
    executable = shutil.which("claude")
    if executable:
        absolute_executable = _absolute_path(executable)
        stable_launcher = _native_launcher_from_cached_path(
            absolute_executable
        )
        return stable_launcher or absolute_executable
    stable_launcher = _native_launcher_from_cached_path(config.claude_path)
    if stable_launcher is not None:
        return stable_launcher
    if config.claude_path and Path(config.claude_path).is_file():
        return config.claude_path
    return None


def _absolute_path(value: str | Path) -> str:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = Path.cwd() / path
    return str(path.absolute())


def _native_launcher_from_cached_path(cached: str | None) -> str | None:
    if cached is None:
        return None
    path = Path(cached).expanduser()
    if (
        path.parent.name != "versions"
        or path.parent.parent.name != "claude"
        or len(path.parents) < 4
    ):
        return None
    bin_dir = path.parents[3] / "bin"
    for name in ("claude", "claude.exe", "claude.cmd", "claude.bat"):
        candidate = bin_dir / name
        if candidate.is_file():
            return str(candidate.absolute())
    return None


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
