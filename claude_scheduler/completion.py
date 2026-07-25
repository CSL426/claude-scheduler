"""Shell completion generation for ccs."""

from .config import DEFAULT_TIMES

COMMANDS = (
    "setup",
    "install",
    "remove",
    "status",
    "run",
    "config",
    "completion",
    "update",
    "version",
    "--version",
    "--help",
    "-V",
    "-h",
)
CONFIG_OPTIONS = (
    "--time",
    "--model",
    "--prompt",
    "--claude-path",
    "--node-path",
)
PATH_OPTIONS = ("--node-path",)
SHELLS = ("bash", "powershell")


def bash_completion() -> str:
    commands = " ".join(COMMANDS)
    config_options = " ".join(CONFIG_OPTIONS)
    default_times = " ".join(DEFAULT_TIMES)
    shells = " ".join(SHELLS)
    return f"""_ccs_completion() {{
    local current command previous
    current="${{COMP_WORDS[COMP_CWORD]}}"
    previous="${{COMP_WORDS[COMP_CWORD-1]}}"
    if (( COMP_CWORD == 1 )); then
        COMPREPLY=( $(compgen -W '{commands}' -- "$current") )
        return
    fi
    command="${{COMP_WORDS[1]}}"
    case "$command" in
        config)
            case "$previous" in
                --claude-path)
                    COMPREPLY=(
                        $(compgen -W 'auto' -- "$current")
                        $(compgen -f -- "$current")
                    )
                    compopt -o filenames 2>/dev/null || true
                    return
                    ;;
                --node-path)
                    COMPREPLY=( $(compgen -f -- "$current") )
                    compopt -o filenames 2>/dev/null || true
                    return
                    ;;
                --time)
                    COMPREPLY=( $(compgen -W '{default_times}' -- "$current") )
                    return
                    ;;
                --model|--prompt)
                    return
                    ;;
            esac
            if [[ -z "$current" || "$current" == -* ]]; then
                COMPREPLY=( $(compgen -W '{config_options}' -- "$current") )
            fi
            ;;
        completion)
            if (( COMP_CWORD == 2 )); then
                COMPREPLY=( $(compgen -W '{shells}' -- "$current") )
            fi
            ;;
    esac
}}
complete -o default -F _ccs_completion ccs
"""


def powershell_completion() -> str:
    commands = ", ".join(f"'{value}'" for value in COMMANDS)
    config_options = ", ".join(f"'{value}'" for value in CONFIG_OPTIONS)
    default_times = ", ".join(f"'{value}'" for value in DEFAULT_TIMES)
    path_options = ", ".join(f"'{value}'" for value in PATH_OPTIONS)
    shells = ", ".join(f"'{value}'" for value in SHELLS)
    return f"""Register-ArgumentCompleter -CommandName 'ccs' -ScriptBlock {{
    param($wordToComplete, $commandAst, $cursorPosition)
    $commands = @({commands})
    $configOptions = @({config_options})
    $defaultTimes = @({default_times})
    $pathOptions = @({path_options})
    $shells = @({shells})
    $arguments = @(
        $commandAst.CommandElements |
            Select-Object -Skip 1 |
            ForEach-Object {{ $_.Extent.Text }}
    )
    if ($arguments.Count -eq 0 -or ($arguments.Count -eq 1 -and $wordToComplete)) {{
        $candidates = $commands
    }}
    else {{
        $command = $arguments[0]
        if ($arguments[-1] -eq $wordToComplete -and $arguments.Count -gt 1) {{
            $previousArgument = $arguments[-2]
        }}
        else {{
            $previousArgument = $arguments[-1]
        }}
        if ($command -eq 'config') {{
            if ($previousArgument -eq '--claude-path') {{
                if ('auto' -like "$wordToComplete*") {{
                    'auto'
                }}
                [System.Management.Automation.CompletionCompleters]::CompleteFilename(
                    $wordToComplete
                )
                return
            }}
            if ($pathOptions -contains $previousArgument) {{
                [System.Management.Automation.CompletionCompleters]::CompleteFilename(
                    $wordToComplete
                )
                return
            }}
            if ($previousArgument -eq '--time') {{
                $candidates = $defaultTimes
            }}
            elseif ($previousArgument -in @('--model', '--prompt')) {{
                $candidates = @()
            }}
            elseif (
                -not $wordToComplete -or
                $wordToComplete -like '-*'
            ) {{
                $candidates = $configOptions
            }}
            else {{
                $candidates = @()
            }}
        }}
        elseif ($command -eq 'completion') {{
            if (
                $arguments.Count -eq 1 -or
                ($arguments.Count -eq 2 -and $arguments[-1] -eq $wordToComplete)
            ) {{
                $candidates = $shells
            }}
            else {{
                $candidates = @()
            }}
        }}
        else {{
            $candidates = @()
        }}
    }}
    $candidates |
        Where-Object {{ $_ -like "$wordToComplete*" }} |
        Sort-Object -Unique
}}
"""


def render_completion(shell: str) -> str:
    if shell == "bash":
        return bash_completion()
    if shell == "powershell":
        return powershell_completion()
    raise ValueError(f"Unsupported completion shell: {shell}")
