from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path

from . import PRODUCT_NAME, __version__
from .config import (
    ConfigError,
    SchedulerConfig,
    config_path,
    load_config,
    save_config,
    state_dir,
)
from .platforms import SchedulerBackend, current_backend
from .runner import (
    ClaudeNotFoundError,
    resolve_claude,
    resolve_claude_launcher,
    resolve_node,
    run_claude,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ccs")
    parser.add_argument(
        "-V",
        "--version",
        action="version",
        version=f"{PRODUCT_NAME} {__version__}",
    )
    parser.add_argument("--config-path", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--state-dir", type=Path, help=argparse.SUPPRESS)
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("install", help="Install or replace scheduled tasks")
    subparsers.add_parser("remove", help="Remove scheduled tasks")
    subparsers.add_parser("status", help="Show configuration and task status")
    subparsers.add_parser("run", help="Run Claude immediately")
    subparsers.add_parser("setup", help="Configure interactively")
    subparsers.add_parser("update", help="Download and install the latest release")
    subparsers.add_parser("version", help="Show version")
    completion_parser = subparsers.add_parser(
        "completion",
        help="Generate shell completion",
    )
    completion_parser.add_argument("shell", choices=("bash", "powershell"))

    config_parser = subparsers.add_parser("config", help="Show or edit configuration")
    config_parser.add_argument(
        "--time",
        action="append",
        dest="times",
        metavar="HH:MM",
        help="Replace schedule times; repeat for multiple times",
    )
    config_parser.add_argument("--model")
    config_parser.add_argument("--prompt")
    config_parser.add_argument(
        "--claude-path",
        metavar="PATH|auto",
        help="Pin a Claude executable, or use auto to follow CLI updates",
    )
    config_parser.add_argument("--node-path", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command is None:
        build_parser().print_help()
        return 0
    if args.command == "version":
        print(f"{PRODUCT_NAME} {__version__}")
        return 0
    if args.command == "update":
        from .update import run_update

        return run_update()
    if args.command == "completion":
        from .completion import render_completion

        print(render_completion(args.shell), end="")
        return 0
    selected_config = (
        args.config_path.expanduser().resolve()
        if args.config_path is not None
        else config_path()
    )
    selected_state = (
        args.state_dir.expanduser().resolve()
        if args.state_dir is not None
        else state_dir()
    )
    try:
        config = load_config(selected_config)
        if args.command == "config":
            return _configure(args, config, selected_config)
        if args.command == "setup":
            return _setup(config, selected_config, selected_state)
        if args.command == "run":
            return run_claude(
                config,
                output_path=selected_state / "scheduled_task.log",
            )
        backend = current_backend()
        if args.command == "install":
            return _install(config, selected_config, selected_state, backend)
        if args.command == "remove":
            backend.remove()
            print("Removed scheduled tasks.")
            return 0
        if args.command == "status":
            installed, scheduler = backend.status()
            try:
                resolved_claude_path = resolve_claude(config)
            except ClaudeNotFoundError:
                resolved_claude_path = None
            payload = {
                "installed": installed,
                "scheduler": scheduler,
                "times": list(config.times),
                "model": config.model,
                "claude_path": config.claude_path,
                "claude_path_mode": config.claude_path_mode,
                "resolved_claude_path": resolved_claude_path,
                "node_path": config.node_path,
                "config_path": str(selected_config),
                "log_path": str(selected_state / "scheduled_task.log"),
            }
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            return 0
    except (
        ClaudeNotFoundError,
        ConfigError,
        OSError,
        RuntimeError,
        subprocess.SubprocessError,
    ) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 2


def _install(
    config: SchedulerConfig,
    selected_config: Path,
    selected_state: Path,
    backend: SchedulerBackend | None = None,
) -> int:
    selected_backend = backend or current_backend()
    launch_command = _launch_command()
    executable = resolve_claude(config)
    launcher = resolve_claude_launcher(config)
    node_path = resolve_node(config)
    if len(launcher) == 2:
        node_path = launcher[0]
    if executable != config.claude_path or node_path != config.node_path:
        config = replace(
            config,
            claude_path=executable,
            node_path=node_path,
        )
        save_config(config, selected_config)
    scheduled_command = [
        *launch_command,
        "--config-path",
        str(selected_config),
        "--state-dir",
        str(selected_state),
    ]
    selected_backend.install(scheduled_command, config.times)
    _remove_legacy_entrypoint()
    print(
        f"Installed {len(config.times)} task(s) with "
        f"{selected_backend.status()[1]}."
    )
    return 0


def _setup(
    config: SchedulerConfig,
    selected_config: Path,
    selected_state: Path,
) -> int:
    try:
        times = _prompt_times(config)
        model = _prompt_value("Model", config.model)
        prompt = _prompt_value("Prompt", config.prompt)
        install_now = _prompt_confirmation(
            "Install scheduled tasks now?",
            default=True,
        )
    except EOFError as error:
        raise ConfigError(
            "Interactive setup requires terminal input"
        ) from error

    updated = replace(
        config,
        times=times,
        model=model,
        prompt=prompt,
    ).validate()
    target = save_config(updated, selected_config)
    print(f"Saved configuration to {target}.")
    if not install_now:
        print("Run 'ccs install' when you are ready.")
        return 0
    return _install(updated, selected_config, selected_state)


def _prompt_times(config: SchedulerConfig) -> tuple[str, ...]:
    current = ", ".join(config.times)
    while True:
        answer = input(f"Schedule times [{current}]: ").strip()
        if not answer:
            return config.times
        times = tuple(answer.replace(",", " ").split())
        try:
            replace(config, times=times).validate()
        except ConfigError as error:
            print(f"Invalid schedule: {error}")
            continue
        return times


def _prompt_value(label: str, current: str) -> str:
    answer = input(f"{label} [{current}]: ").strip()
    return answer or current


def _prompt_confirmation(question: str, *, default: bool) -> bool:
    suffix = "[Y/n]" if default else "[y/N]"
    while True:
        answer = input(f"{question} {suffix}: ").strip().lower()
        if not answer:
            return default
        if answer in {"y", "yes"}:
            return True
        if answer in {"n", "no"}:
            return False
        print("Please answer y or n.")


def console_main() -> int:
    return main()


def _configure(
    args: argparse.Namespace,
    config: SchedulerConfig,
    selected_config: Path,
) -> int:
    updates = any(
        value is not None
        for value in (
            args.times,
            args.model,
            args.prompt,
            args.claude_path,
            args.node_path,
        )
    )
    if not updates:
        payload = {
            "times": list(config.times),
            "model": config.model,
            "prompt": config.prompt,
            "claude_path": config.claude_path,
            "claude_path_mode": config.claude_path_mode,
            "node_path": config.node_path,
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    claude_path = config.claude_path
    claude_path_mode = config.claude_path_mode
    if args.claude_path is not None:
        if args.claude_path.lower() == "auto":
            automatic = replace(
                config,
                claude_path=None,
                claude_path_mode="auto",
            )
            claude_path = resolve_claude(automatic)
            claude_path_mode = "auto"
        else:
            selected_path = Path(args.claude_path).expanduser().absolute()
            if not selected_path.is_file():
                raise ConfigError(
                    f"Claude CLI does not exist: {selected_path}"
                )
            claude_path = str(selected_path)
            claude_path_mode = "explicit"
    node_path = config.node_path
    if args.node_path is not None:
        resolved_node = args.node_path.expanduser().resolve()
        if not resolved_node.is_file():
            raise ConfigError(f"node does not exist: {resolved_node}")
        node_path = str(resolved_node)
    updated = replace(
        config,
        times=tuple(args.times) if args.times is not None else config.times,
        model=args.model if args.model is not None else config.model,
        prompt=args.prompt if args.prompt is not None else config.prompt,
        claude_path=claude_path,
        claude_path_mode=claude_path_mode,
        node_path=node_path,
    )
    target = save_config(updated, selected_config)
    print(f"Saved configuration to {target}.")
    return 0


def _launch_command() -> list[str]:
    if getattr(sys, "frozen", False):
        return [str(Path(sys.executable).resolve())]
    entrypoint = Path(sys.argv[0])
    if entrypoint.name in {"ccs", "ccs.exe"}:
        return [str(entrypoint.resolve())]
    raise RuntimeError(
        "Scheduling from 'python -m' is not persistent. Install the package "
        "and run ccs install."
    )


def _remove_legacy_entrypoint() -> None:
    if getattr(sys, "frozen", False):
        entrypoint = Path(sys.executable).resolve()
    else:
        entrypoint = Path(sys.argv[0]).resolve()
    if entrypoint.name not in {"ccs", "ccs.exe"}:
        return
    legacy_name = (
        "claude-scheduler.exe"
        if entrypoint.name == "ccs.exe"
        else "claude-scheduler"
    )
    legacy = entrypoint.with_name(legacy_name)
    if not legacy.is_file() and not legacy.is_symlink():
        return
    try:
        legacy.unlink()
    except OSError as error:
        print(
            f"warning: Could not remove legacy command {legacy}: {error}",
            file=sys.stderr,
        )
