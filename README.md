# Claude Scheduler

跨平台的 Claude Code CLI 排程工具。Linux 使用 cron、macOS 使用
launchd、Windows 使用 Task Scheduler；三個平台共用同一套 Python
設定、驗證、執行與日誌邏輯。

預設會在系統本地時區的以下時間執行：

- 07:00
- 12:05
- 17:10
- 22:15

執行的 Claude 指令等同於：

```text
claude --model claude-haiku-4-5-20251001 -p "reply with only the word: hi"
```

本工具不會保存或複製 Claude 憑證，而是沿用該機器既有的 Claude CLI
登入狀態。

## 安裝

### Standalone 一行安裝

Release 執行檔已包含 Python runtime，目標機器只需先安裝並登入 Claude
Code CLI。

Linux 或 macOS：

```bash
curl -fsSL https://raw.githubusercontent.com/ac-Spark/claude-scheduler/main/install.sh | bash
```

Windows PowerShell：

```powershell
irm https://raw.githubusercontent.com/ac-Spark/claude-scheduler/main/install.ps1 | iex
```

安裝器會：

- 下載目前平台的 GitHub Release 執行檔。
- 驗證 SHA-256。
- 安裝 `claude-scheduler`。
- 尋找本機的 Claude 與 Node 執行檔。
- 建立使用者層級的排程，不需要管理員權限。

只安裝 CLI、不建立排程：

```bash
CLAUDE_SCHEDULER_SKIP_SETUP=1 \
  curl -fsSL https://raw.githubusercontent.com/ac-Spark/claude-scheduler/main/install.sh | bash
```

Windows PowerShell：

```powershell
$env:CLAUDE_SCHEDULER_SKIP_SETUP = "1"
irm https://raw.githubusercontent.com/ac-Spark/claude-scheduler/main/install.ps1 | iex
```

可用 `CLAUDE_SCHEDULER_VERSION` 指定 release tag。

### Clone 後安裝

需要 Python 3.11 以上版本：

```bash
git clone https://github.com/ac-Spark/claude-scheduler.git
cd claude-scheduler
python -m venv .venv
.venv/bin/pip install --editable .
.venv/bin/claude-scheduler install
```

Windows PowerShell：

```powershell
git clone https://github.com/ac-Spark/claude-scheduler.git
Set-Location claude-scheduler
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --editable .
.\.venv\Scripts\claude-scheduler.exe install
```

這種方式建立的排程會指向該 `.venv`，因此安裝後不可刪除或搬動 checkout。

## CLI 指令

```text
claude-scheduler install
claude-scheduler remove
claude-scheduler status
claude-scheduler run
claude-scheduler config
claude-scheduler version
```

- `install`：建立或更新排程。
- `remove`：移除本工具管理的排程。
- `status`：顯示排程狀態、設定與日誌位置。
- `run`：立即執行一次 Claude。
- `config`：顯示或修改設定。
- `version`：顯示版本。

第一次安裝會移除舊版 `claude_scheduler.sh` cron 項目及 Windows
`Claude_HHMM` 任務；其他不相關的排程不會被變更。

## 設定排程時間

查看目前設定：

```bash
claude-scheduler config
```

用重複的 `--time HH:MM` 取代完整排程時間清單：

```bash
claude-scheduler config \
  --time 08:00 \
  --time 13:00 \
  --time 18:00 \
  --time 23:00
claude-scheduler install
```

時間使用 24 小時制與系統本地時區。修改時間後要再執行一次 `install`，
讓 cron、launchd 或 Task Scheduler 套用新時間。

修改模型或提示詞：

```bash
claude-scheduler config \
  --model <model-id> \
  --prompt "<prompt>"
```

手動指定 Claude CLI：

```bash
claude-scheduler config --claude-path /absolute/path/to/claude
```

Windows npm 安裝若找不到 Node：

```powershell
claude-scheduler config --node-path C:\path\to\node.exe
```

Windows npm 的 `claude.cmd` 不會直接經過 `cmd.exe` 執行；工具會解析其
Node 與 Claude CLI JavaScript entrypoint，避免 prompt 被 shell 展開。

## 設定與日誌位置

設定檔：

- Linux：`${XDG_CONFIG_HOME:-~/.config}/claude-scheduler/config.json`
- macOS：`~/Library/Application Support/claude-scheduler/config.json`
- Windows：`%APPDATA%\claude-scheduler\config.json`

日誌目錄：

- Linux：`${XDG_STATE_HOME:-~/.local/state}/claude-scheduler/`
- macOS：`~/Library/Logs/claude-scheduler/`
- Windows：`%LOCALAPPDATA%\claude-scheduler\`

`install` 會把設定檔與 state 目錄的絕對路徑寫入排程。若安裝時能找到
Node，也會保存 Node 絕對路徑，並在執行 Claude 時補進 `PATH`，避免 cron
的精簡環境讓 Claude hooks 找不到 Node。

## 開發與發布驗證

```bash
python -m pytest
ruff check claude_scheduler tests scripts/standalone_entry.py
bash -n install.sh linux.sh test_now.sh
git diff --check
```

GitHub Actions 會在 Linux、macOS、Windows 的 Python 3.11 與 3.12
執行測試。`v*` tag 會建立以下 standalone 執行檔及 SHA-256：

- Linux x86-64
- Windows x86-64
- macOS x86-64
- macOS arm64

更多設計細節：

- [架構](docs/architecture.md)
- [平台行為](docs/platform-behavior.md)
