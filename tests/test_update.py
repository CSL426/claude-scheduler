import os
import subprocess
import sys
from pathlib import Path

import pytest

from claude_scheduler import update


@pytest.mark.parametrize(
    ("current", "latest", "expected"),
    [
        ("0.3.0", "0.3.0", True),
        ("0.3", "0.3.0", True),
        ("0.4.0", "0.3.0", True),
        ("0.2.9", "0.3.0", False),
        ("dev", "dev", True),
        ("dev", "0.3.0", False),
    ],
)
def test_is_up_to_date(current, latest, expected):
    assert update.is_up_to_date(current, latest) is expected


def test_source_update_delegates_to_primary_standalone(
    tmp_path,
    monkeypatch,
    capsys,
):
    executable = tmp_path / "ccs"
    executable.write_text("standalone\n", encoding="utf-8")
    executable.chmod(0o755)
    calls = {}

    def fake_run(command, **kwargs):
        calls["command"] = command
        calls["environment"] = kwargs["env"]
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(update, "standalone_candidates", lambda: (executable,))
    monkeypatch.setattr(update.subprocess, "run", fake_run)
    monkeypatch.setattr(sys, "frozen", False, raising=False)
    monkeypatch.setattr(sys, "argv", [str(tmp_path / "source-ccs")])
    monkeypatch.delenv(update.DELEGATED_UPDATE, raising=False)

    assert update.run_update() == 0
    assert calls["command"] == [str(executable), "update"]
    assert calls["environment"][update.DELEGATED_UPDATE] == "1"
    assert "Delegating update" in capsys.readouterr().out


def test_source_update_without_standalone_explains_git_pull(
    monkeypatch,
    capsys,
):
    monkeypatch.setattr(update, "standalone_candidates", tuple)
    monkeypatch.setattr(sys, "frozen", False, raising=False)

    assert update.run_update() == 1
    captured = capsys.readouterr()
    assert "runs from source" in captured.err
    assert "git pull" in captured.out


def test_frozen_update_skips_download_when_current(monkeypatch, capsys):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(update, "__version__", "0.3.0")
    monkeypatch.setattr(update, "latest_release_version", lambda: "0.3.0")
    monkeypatch.setattr(
        update,
        "run_posix_update",
        lambda _bin_dir: pytest.fail("must not download"),
    )

    assert update.run_update() == 0
    assert "already up to date" in capsys.readouterr().out


def test_frozen_posix_update_uses_executable_directory(
    tmp_path,
    monkeypatch,
):
    executable = tmp_path / "bin" / "ccs"
    executable.parent.mkdir()
    executable.touch()
    calls = {}

    def fake_update(bin_dir):
        calls["bin_dir"] = bin_dir
        return 23

    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(sys, "executable", str(executable))
    monkeypatch.setattr(update, "__version__", "0.3.0")
    monkeypatch.setattr(update, "latest_release_version", lambda: "0.4.0")
    monkeypatch.setattr(update, "run_posix_update", fake_update)

    assert update.run_update() == 23
    assert calls["bin_dir"] == executable.parent.resolve()


def test_posix_update_preserves_scheduler_setup(
    tmp_path,
    monkeypatch,
):
    calls = {}

    def fake_run(command, **kwargs):
        calls["command"] = command
        calls["input"] = kwargs["input"]
        calls["environment"] = kwargs["env"]
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(update, "download_installer", lambda: "installer\n")
    monkeypatch.setattr(update.subprocess, "run", fake_run)

    assert update.run_posix_update(tmp_path) == 0
    assert calls["command"] == ["bash"]
    assert calls["input"] == "installer\n"
    assert calls["environment"]["CCS_BIN_DIR"] == str(tmp_path)
    assert calls["environment"]["CCS_SKIP_SETUP"] == "1"


def test_windows_update_hands_off_after_parent_exit(
    tmp_path,
    monkeypatch,
    capsys,
):
    calls = {}

    def fake_popen(command, **kwargs):
        calls["command"] = command
        calls["kwargs"] = kwargs
        return object()

    monkeypatch.setattr(update.subprocess, "Popen", fake_popen)

    assert update.launch_windows_update(tmp_path) == 0
    assert calls["command"][:5] == [
        "powershell.exe",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
    ]
    script = calls["command"][5]
    assert f"Wait-Process -Id {os.getpid()}" in script
    assert "CCS_SKIP_SETUP" in script
    assert str(tmp_path) in script
    assert "install.ps1" in script
    assert "handed off to PowerShell" in capsys.readouterr().out


def test_standalone_candidates_only_include_ccs(tmp_path, monkeypatch):
    monkeypatch.setenv("CCS_BIN_DIR", str(tmp_path))
    monkeypatch.setattr(sys, "platform", "linux")

    assert update.standalone_candidates() == (Path(tmp_path, "ccs"),)
