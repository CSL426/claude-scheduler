"""Self-update through the hosted cross-platform installers."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from urllib.request import Request, urlopen

from . import PRODUCT_NAME, __version__

DEFAULT_REPOSITORY = "CSL426/claude-scheduler"
DELEGATED_UPDATE = "CCS_UPDATE_DELEGATED"
RELEASE_VERSION = re.compile(r"^v?(\d+(?:\.\d+){1,3})$")


def repository() -> str:
    return os.environ.get(
        "CCS_REPOSITORY",
        os.environ.get("CLAUDE_SCHEDULER_REPOSITORY", DEFAULT_REPOSITORY),
    )


def installer_url(script: str) -> str:
    return f"https://raw.githubusercontent.com/{repository()}/main/{script}"


def latest_release_version() -> str:
    url = f"https://api.github.com/repos/{repository()}/releases/latest"
    request = Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "ccs-updater",
        },
    )
    with urlopen(request, timeout=15) as response:
        document = json.load(response)
    tag = document.get("tag_name") if isinstance(document, dict) else None
    if not isinstance(tag, str) or not RELEASE_VERSION.fullmatch(tag):
        raise RuntimeError("Latest GitHub release has an invalid version tag")
    return tag.removeprefix("v")


def version_key(value: str) -> tuple[int, ...] | None:
    match = RELEASE_VERSION.fullmatch(value)
    if match is None:
        return None
    return tuple(int(part) for part in match.group(1).split("."))


def is_up_to_date(current: str, latest: str) -> bool:
    current_key = version_key(current)
    latest_key = version_key(latest)
    if current_key is None or latest_key is None:
        return current == latest
    width = max(len(current_key), len(latest_key))
    current_key += (0,) * (width - len(current_key))
    latest_key += (0,) * (width - len(latest_key))
    return current_key >= latest_key


def standalone_candidates() -> tuple[Path, ...]:
    default_bin = Path.home() / ".local" / "bin"
    bin_dir = Path(
        os.environ.get(
            "CCS_BIN_DIR",
            os.environ.get("CLAUDE_SCHEDULER_BIN_DIR", default_bin),
        )
    ).expanduser()
    suffix = ".exe" if sys.platform == "win32" else ""
    return (bin_dir / f"ccs{suffix}",)


def delegate_source_update() -> int | None:
    if os.environ.get(DELEGATED_UPDATE) == "1":
        return None
    current = Path(sys.argv[0]).resolve()
    for candidate in standalone_candidates():
        if not candidate.is_file() or not os.access(candidate, os.X_OK):
            continue
        try:
            if candidate.resolve() == current:
                continue
        except OSError:
            continue
        environment = os.environ.copy()
        environment[DELEGATED_UPDATE] = "1"
        print(f"Delegating update to standalone release: {candidate}")
        completed = subprocess.run(
            [str(candidate), "update"],
            env=environment,
            check=False,
        )
        return completed.returncode
    return None


def powershell_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def windows_update_script(parent_pid: int, bin_dir: Path) -> str:
    url = powershell_literal(installer_url("install.ps1"))
    destination = powershell_literal(str(bin_dir))
    return "\n".join(
        (
            "$ErrorActionPreference = 'Stop'",
            f"Wait-Process -Id {parent_pid} -ErrorAction SilentlyContinue",
            "$env:CCS_SKIP_SETUP = '1'",
            f"$env:CCS_BIN_DIR = {destination}",
            (
                "$installer = Join-Path ([IO.Path]::GetTempPath()) "
                "('install-ccs-' + [guid]::NewGuid().ToString('N') + '.ps1')"
            ),
            "try {",
            (
                "  Invoke-WebRequest -UseBasicParsing "
                f"-Uri {url} -OutFile $installer"
            ),
            "  & $installer",
            "  exit $LASTEXITCODE",
            "}",
            "finally {",
            (
                "  Remove-Item -LiteralPath $installer -Force "
                "-ErrorAction SilentlyContinue"
            ),
            "}",
        )
    )


def launch_windows_update(bin_dir: Path) -> int:
    command = [
        "powershell.exe",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        windows_update_script(os.getpid(), bin_dir),
    ]
    try:
        subprocess.Popen(
            command,
            creationflags=getattr(
                subprocess,
                "CREATE_NEW_PROCESS_GROUP",
                0,
            ),
        )
    except OSError as error:
        print(f"error: Could not start the PowerShell updater: {error}", file=sys.stderr)
        return 1
    print(
        "Update handed off to PowerShell; installation will continue "
        "after this process exits."
    )
    return 0


def download_installer() -> str:
    request = Request(
        installer_url("install.sh"),
        headers={"User-Agent": "ccs-updater"},
    )
    with urlopen(request, timeout=15) as response:
        return response.read().decode("utf-8")


def run_posix_update(bin_dir: Path) -> int:
    try:
        script = download_installer()
    except (OSError, RuntimeError, ValueError) as error:
        print(
            f"error: Could not download the installer: {error}",
            file=sys.stderr,
        )
        return 1
    environment = os.environ.copy()
    environment["CCS_BIN_DIR"] = str(bin_dir)
    environment["CCS_SKIP_SETUP"] = "1"
    completed = subprocess.run(
        ["bash"],
        input=script,
        text=True,
        env=environment,
        check=False,
    )
    if completed.returncode != 0:
        print(
            "error: Update failed; the current binary is unchanged.",
            file=sys.stderr,
        )
    return completed.returncode


def run_update() -> int:
    if not getattr(sys, "frozen", False):
        delegated = delegate_source_update()
        if delegated is not None:
            return delegated
        print(
            "error: This ccs command runs from source, not a standalone release.",
            file=sys.stderr,
        )
        print(
            "Update the checkout with: git pull "
            "(then `pip install -e .` if package metadata changed)."
        )
        return 1

    try:
        latest = latest_release_version()
    except (OSError, RuntimeError, ValueError) as error:
        print(
            f"error: Could not check the latest release version: {error}",
            file=sys.stderr,
        )
        return 1
    print(f"{PRODUCT_NAME}: current {__version__}; latest {latest}")
    if is_up_to_date(__version__, latest):
        print(f"{PRODUCT_NAME} is already up to date.")
        return 0

    bin_dir = Path(sys.executable).resolve().parent
    if sys.platform == "win32":
        return launch_windows_update(bin_dir)
    return run_posix_update(bin_dir)
