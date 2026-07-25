import tomllib
from pathlib import Path

from claude_scheduler import __version__


def test_package_versions_match():
    metadata = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

    assert metadata["project"]["version"] == __version__
