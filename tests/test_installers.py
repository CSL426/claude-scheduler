from pathlib import Path


def test_bash_installer_prints_current_shell_activation():
    content = Path("install.sh").read_text(encoding="utf-8")

    assert "Activate now without reopening:" in content
    assert 'export PATH=\\"$BIN_DIR:\\$PATH\\" && hash -r &&' in content
    assert 'source <(\\"$destination\\" completion bash)' in content


def test_powershell_installer_activates_completion_in_current_runspace():
    content = Path("install.ps1").read_text(encoding="utf-8")

    assert ". $PowerShellCompletionPath" in content
    assert "no restart is required" in content
