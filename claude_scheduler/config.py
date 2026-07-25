from __future__ import annotations

import json
import os
import re
import sys
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

DEFAULT_MODEL = "claude-haiku-4-5-20251001"
DEFAULT_PROMPT = "reply with only the word: hi"
DEFAULT_TIMES = ("07:00", "12:05", "17:10", "22:15")
TIME_PATTERN = re.compile(r"(?:[01]\d|2[0-3]):[0-5]\d")


class ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class SchedulerConfig:
    times: tuple[str, ...] = DEFAULT_TIMES
    model: str = DEFAULT_MODEL
    prompt: str = DEFAULT_PROMPT
    claude_path: str | None = None
    node_path: str | None = None

    def validate(self) -> SchedulerConfig:
        if not self.times:
            raise ConfigError("At least one schedule time is required")
        if len(set(self.times)) != len(self.times):
            raise ConfigError("Schedule times must be unique")
        invalid = [value for value in self.times if not TIME_PATTERN.fullmatch(value)]
        if invalid:
            raise ConfigError(f"Invalid schedule time: {invalid[0]}")
        if not self.model.strip():
            raise ConfigError("Model must not be empty")
        if not self.prompt.strip():
            raise ConfigError("Prompt must not be empty")
        return self


def config_path() -> Path:
    override = os.environ.get(
        "CCS_CONFIG",
        os.environ.get("CLAUDE_SCHEDULER_CONFIG"),
    )
    if override:
        return Path(override).expanduser().resolve()
    if sys.platform == "win32":
        root = Path(os.environ.get("APPDATA", Path.home() / "AppData/Roaming"))
    elif sys.platform == "darwin":
        root = Path.home() / "Library/Application Support"
    else:
        root = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return root / "claude-scheduler/config.json"


def state_dir() -> Path:
    override = os.environ.get(
        "CCS_STATE_DIR",
        os.environ.get("CLAUDE_SCHEDULER_STATE_DIR"),
    )
    if override:
        return Path(override).expanduser().resolve()
    if sys.platform == "win32":
        root = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local"))
    elif sys.platform == "darwin":
        root = Path.home() / "Library/Logs"
    else:
        root = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state"))
    return root / "claude-scheduler"


def log_path() -> Path:
    return state_dir() / "scheduled_task.log"


def load_config(path: Path | None = None) -> SchedulerConfig:
    target = path or config_path()
    if not target.exists():
        return SchedulerConfig()
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ConfigError(f"Cannot read configuration: {error}") from error
    if not isinstance(data, dict):
        raise ConfigError("Configuration root must be an object")
    return _config_from_mapping(data)


def save_config(config: SchedulerConfig, path: Path | None = None) -> Path:
    config.validate()
    target = path or config_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = asdict(config)
    payload["times"] = list(config.times)
    content = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    descriptor, temporary_name = tempfile.mkstemp(
        dir=target.parent,
        prefix=f".{target.name}.",
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(content)
        temporary.replace(target)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
    return target


def _config_from_mapping(data: dict[str, Any]) -> SchedulerConfig:
    allowed = {"times", "model", "prompt", "claude_path", "node_path"}
    unknown = sorted(set(data) - allowed)
    if unknown:
        raise ConfigError(f"Unknown configuration field: {unknown[0]}")
    times = data.get("times", DEFAULT_TIMES)
    if not isinstance(times, list) or not all(isinstance(item, str) for item in times):
        raise ConfigError("times must be a list of HH:MM strings")
    model = data.get("model", DEFAULT_MODEL)
    prompt = data.get("prompt", DEFAULT_PROMPT)
    claude_path = data.get("claude_path")
    node_path = data.get("node_path")
    if not isinstance(model, str) or not isinstance(prompt, str):
        raise ConfigError("model and prompt must be strings")
    if claude_path is not None and not isinstance(claude_path, str):
        raise ConfigError("claude_path must be a string or null")
    if node_path is not None and not isinstance(node_path, str):
        raise ConfigError("node_path must be a string or null")
    return SchedulerConfig(
        times=tuple(times),
        model=model,
        prompt=prompt,
        claude_path=claude_path,
        node_path=node_path,
    ).validate()
