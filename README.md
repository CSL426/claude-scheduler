# CC Scheduler

[![Cross-platform CLI](https://github.com/CSL426/claude-scheduler/actions/workflows/ci.yml/badge.svg)](https://github.com/CSL426/claude-scheduler/actions/workflows/ci.yml)

`ccs` 是跨平台的 Claude Code CLI 排程工具。Linux 使用 cron、macOS 使用
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
curl -fsSL https://raw.githubusercontent.com/CSL426/claude-scheduler/main/install.sh | bash
```

Windows PowerShell：

```powershell
irm https://raw.githubusercontent.com/CSL426/claude-scheduler/main/install.ps1 | iex
```

安裝器會：

- 下載目前平台的 GitHub Release 執行檔。
- 驗證 SHA-256。
- 安裝唯一的指令 `ccs`；Windows 安裝為 `ccs.exe`。
- 移除舊的 `claude-scheduler`／`claude-scheduler.exe` 指令。
- 安裝 Bash 與 PowerShell Tab completion。
- 尋找本機的 Claude 與 Node 執行檔。
- 建立使用者層級的排程，不需要管理員權限。

只安裝 CLI、不建立排程：

```bash
curl -fsSL https://raw.githubusercontent.com/CSL426/claude-scheduler/main/install.sh |
  CCS_SKIP_SETUP=1 bash
```

Windows PowerShell：

```powershell
$env:CCS_SKIP_SETUP = "1"
irm https://raw.githubusercontent.com/CSL426/claude-scheduler/main/install.ps1 | iex
```

若舊排程仍可能引用舊 executable，skip-setup 安裝會暫時保留舊檔；之後成功
執行 `ccs install` 時會重寫排程並自動移除舊指令。

可用 `CCS_VERSION` 指定 release tag；`CCS_BIN_DIR` 可指定安裝目錄，
`CCS_CONFIG`／`CCS_STATE_DIR` 可指定設定檔與 state 目錄，
`CCS_SKIP_COMPLETION=1` 可略過 completion 安裝。舊版
`CLAUDE_SCHEDULER_*` 安裝環境變數仍可讀取，方便既有自動化升級，但新設定
一律使用 `CCS_*`。

### Clone 後安裝

需要 Python 3.11 以上版本：

```bash
git clone https://github.com/CSL426/claude-scheduler.git
cd claude-scheduler
python -m venv .venv
.venv/bin/pip install --editable .
.venv/bin/ccs install
```

Windows PowerShell：

```powershell
git clone https://github.com/CSL426/claude-scheduler.git
Set-Location claude-scheduler
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --editable .
.\.venv\Scripts\ccs.exe install
```

這種方式建立的排程會指向該 `.venv`，因此安裝後不可刪除或搬動 checkout。

## CLI 指令

```text
ccs install
ccs remove
ccs status
ccs run
ccs setup
ccs config
ccs completion bash
ccs completion powershell
ccs update
ccs version
ccs --version
```

- `install`：建立或更新排程。
- `remove`：移除本工具管理的排程。
- `status`：顯示排程狀態、設定與日誌位置。
- `run`：立即執行一次 Claude。
- `setup`：互動設定時間、model、prompt，並選擇是否立即安裝。
- `config`：顯示或修改設定。
- `completion`：輸出 Bash 或 PowerShell completion script。
- `update`：檢查 GitHub Release 並更新 standalone 執行檔。
- `version`：顯示版本。

對外只提供 `ccs`；舊指令會在安裝或更新時移除。設定檔、日誌與既有系統
排程識別碼維持不變，安裝器會以 `ccs` 重建原排程，因此不會遺失原本的
時間、model 或 prompt。

第一次安裝會移除舊版 `claude_scheduler.sh` cron 項目及 Windows
`Claude_HHMM` 任務；其他不相關的排程不會被變更。

## 更新與版本

Standalone 安裝可直接更新：

```bash
ccs update
```

Linux 與 macOS 會更新目前執行檔所在目錄；Windows 會交給背景
PowerShell，等待目前程序結束後再替換執行檔。更新只替換 CLI，不會重新
建立或修改排程。

查看版本：

```bash
ccs version
ccs --version
ccs -V
```

輸出格式：

```text
CC Scheduler (ccs) 0.3.0
```

從 source checkout 執行 `ccs update` 時，若同時存在 standalone 版本，
會交由 standalone 更新；否則會提示使用 `git pull`。

## Tab completion

Standalone 安裝器會自動安裝 completion。Linux／macOS 安裝後若要讓目前的
Bash 立即生效，可執行安裝器顯示的：

```bash
hash -r && source "${BASH_COMPLETION_USER_DIR:-${XDG_DATA_HOME:-$HOME/.local/share}/bash-completion}/completions/ccs.bash"
```

Windows 會安裝 Git Bash completion，並把 PowerShell completion 載入區塊
寫入目前使用者的 PowerShell profile；重新開啟終端即可生效。

需要手動載入或檢查內容時：

```bash
source <(ccs completion bash)
```

```powershell
ccs completion powershell | Out-String | Invoke-Expression
```

Completion 涵蓋所有子指令、`config` 的全部選項、預設時間、路徑檔案選擇，
以及 `completion bash|powershell` 的 shell 名稱。

## 設定排程時間

互動設定：

```bash
ccs setup
```

依序輸入時間、model 與 prompt；直接按 Enter 會保留方括號內的目前值。
時間可使用逗號或空白分隔。最後可選擇立即建立或更新系統排程。

```text
Schedule times [07:00, 12:05, 17:10, 22:15]: 08:00, 13:30, 19:00
Model [claude-haiku-4-5-20251001]:
Prompt [reply with only the word: hi]:
Install scheduled tasks now? [Y/n]:
```

非互動設定：

查看目前設定：

```bash
ccs config
```

用重複的 `--time HH:MM` 取代完整排程時間清單：

```bash
ccs config \
  --time 08:00 \
  --time 13:00 \
  --time 18:00 \
  --time 23:00
ccs install
```

時間使用 24 小時制與系統本地時區。修改時間後要再執行一次 `install`，
讓 cron、launchd 或 Task Scheduler 套用新時間。

修改模型或提示詞：

```bash
ccs config \
  --model <model-id> \
  --prompt "<prompt>"
```

手動指定 Claude CLI：

```bash
ccs config --claude-path /absolute/path/to/claude
```

Windows npm 安裝若找不到 Node：

```powershell
ccs config --node-path C:\path\to\node.exe
```

Windows npm 的 `claude.cmd` 不會直接經過 `cmd.exe` 執行；工具會解析其
Node 與 Claude CLI JavaScript entrypoint，避免 prompt 被 shell 展開。

## 設定與日誌位置

設定檔：

- Linux：`${XDG_CONFIG_HOME:-~/.config}/claude-scheduler/config.json`
- macOS：`~/Library/Application Support/claude-scheduler/config.json`
- Windows：`%APPDATA%\claude-scheduler\config.json`

這些既有資料路徑刻意維持不變，避免 CLI 改名時另建空設定或遺失排程。

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

- `ccs-linux-x86_64`
- `ccs-windows-x86_64.exe`
- `ccs-macos-x86_64`
- `ccs-macos-arm64`

更多設計細節：

- [架構](docs/architecture.md)
- [平台行為](docs/platform-behavior.md)
