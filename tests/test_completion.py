import pytest

from claude_scheduler import completion


@pytest.mark.parametrize(
    "command",
    (
        "setup",
        "install",
        "remove",
        "status",
        "run",
        "config",
        "completion",
        "update",
        "version",
    ),
)
def test_bash_completion_includes_every_command(command):
    assert command in completion.bash_completion()


@pytest.mark.parametrize("option", completion.CONFIG_OPTIONS)
def test_bash_completion_includes_every_config_option(option):
    assert option in completion.bash_completion()


def test_bash_completion_handles_values_and_only_registers_ccs():
    rendered = completion.bash_completion()

    assert "--claude-path)" in rendered
    assert "--node-path)" in rendered
    assert "compgen -W 'auto'" in rendered
    assert "compgen -f" in rendered
    assert "--time)" in rendered
    assert "07:00 12:05 17:10 22:15" in rendered
    assert '[[ -z "$current" || "$current" == -* ]]' in rendered
    assert "complete -o default -F _ccs_completion ccs" in rendered
    assert "claude-scheduler" not in rendered


def test_powershell_completion_handles_commands_options_and_paths():
    rendered = completion.powershell_completion()

    for command in completion.COMMANDS:
        assert f"'{command}'" in rendered
    for option in completion.CONFIG_OPTIONS:
        assert f"'{option}'" in rendered
    assert "CompleteFilename" in rendered
    assert "$previousArgument -eq '--claude-path'" in rendered
    assert "'auto' -like" in rendered
    assert "-not $wordToComplete" in rendered
    assert "Register-ArgumentCompleter -CommandName 'ccs'" in rendered
    assert "claude-scheduler" not in rendered


@pytest.mark.parametrize("shell", completion.SHELLS)
def test_render_completion_supports_documented_shells(shell):
    assert completion.render_completion(shell)


def test_render_completion_rejects_unknown_shell():
    with pytest.raises(ValueError, match="Unsupported completion shell"):
        completion.render_completion("fish")
