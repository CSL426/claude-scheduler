import json
from pathlib import Path

import pytest

from claude_scheduler.config import (
    DEFAULT_TIMES,
    ConfigError,
    SchedulerConfig,
    config_path,
    load_config,
    save_config,
    state_dir,
)


def test_missing_config_uses_defaults(tmp_path):
    config = load_config(tmp_path / "missing.json")

    assert config.times == DEFAULT_TIMES
    assert config.claude_path is None


def test_config_round_trip(tmp_path):
    path = tmp_path / "nested/config.json"
    expected = SchedulerConfig(
        times=("08:15", "19:45"),
        model="test-model",
        prompt="hello",
        claude_path="/opt/bin/claude",
        node_path="/opt/bin/node",
    )

    save_config(expected, path)

    assert load_config(path) == expected
    assert json.loads(path.read_text(encoding="utf-8"))["times"] == [
        "08:15",
        "19:45",
    ]


@pytest.mark.parametrize(
    ("times", "message"),
    [
        ((), "At least one"),
        (("07:00", "07:00"), "unique"),
        (("24:00",), "Invalid"),
        (("7:00",), "Invalid"),
    ],
)
def test_config_rejects_invalid_times(times, message):
    with pytest.raises(ConfigError, match=message):
        SchedulerConfig(times=times).validate()


def test_config_rejects_unknown_fields(tmp_path):
    path = tmp_path / "config.json"
    path.write_text('{"secret": "value"}', encoding="utf-8")

    with pytest.raises(ConfigError, match="Unknown configuration field"):
        load_config(path)


def test_environment_paths_are_resolved(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("CLAUDE_SCHEDULER_CONFIG", "relative/config.json")
    monkeypatch.setenv("CLAUDE_SCHEDULER_STATE_DIR", "relative/state")

    assert config_path() == Path(tmp_path / "relative/config.json")
    assert state_dir() == Path(tmp_path / "relative/state")


def test_ccs_environment_paths_take_precedence(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("CCS_CONFIG", "ccs/config.json")
    monkeypatch.setenv("CCS_STATE_DIR", "ccs/state")
    monkeypatch.setenv("CLAUDE_SCHEDULER_CONFIG", "legacy/config.json")
    monkeypatch.setenv("CLAUDE_SCHEDULER_STATE_DIR", "legacy/state")

    assert config_path() == Path(tmp_path / "ccs/config.json")
    assert state_dir() == Path(tmp_path / "ccs/state")
