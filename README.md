# Claude Auto Scheduler

自動執行 `claude -p 'hi'` 指令，配合 Claude 每5小時重製週期。

## 支援平台

- **Windows**: PowerShell + Task Scheduler
- **macOS / Linux**: Bash + Cron

## 快速開始

### Windows
```cmd
# 設定排程任務（需要管理員權限）
windows.bat

# 立即測試（不需要管理員權限）
test_now.bat
```

### macOS / Linux
```bash
# 設定 cron 任務
./linux.sh

# 立即測試
./test_now.sh
```

## 執行時間

每5小時執行一次，可依需求更改：
- 07:30, 12:30, 17:30, 22:30

## 背景執行

- **Windows**: 完全隱藏執行，不會跳出視窗
- **macOS / Linux**: 背景執行

## 時區設定

### macOS / Linux
預設 UTC+8，可修改 `claude_scheduler.sh` 中的 `TIMEZONE`

### Windows
使用系統時區

## 自訂設定

### 修改時間
```bash
# macOS / Linux: 編輯 claude_scheduler.sh
SCHEDULE_TIMES=("08:00" "13:00" "18:00" "23:00")

# Windows: 編輯 claude_scheduler.ps1
$scheduleTimes = @("08:00", "13:00", "18:00", "23:00")
```

### 修改指令
```bash
# macOS / Linux
COMMAND_TO_RUN="your command"

# Windows
$commandToRun = "your command"
```

## 日誌查看

所有執行記錄都整合在單一日誌檔中：
- `scheduled_task.log` - 包含所有日誌、命令輸出和錯誤訊息

## 測試功能

可隨時測試腳本功能，無需等待排程時間：

### Windows
```cmd
test_now.bat
```

### macOS / Linux
```bash
./test_now.sh
```

## 移除任務

### Windows
```cmd
schtasks /delete /tn Claude_0730 /f
schtasks /delete /tn Claude_1230 /f
schtasks /delete /tn Claude_1730 /f
schtasks /delete /tn Claude_2230 /f
```

### macOS / Linux
```bash
crontab -e  # 刪除相關行
```

## 檔案說明

### Windows
- `claude_scheduler.ps1` - 主腳本
- `windows.bat` - 排程設定工具（需要管理員權限）
- `test_now.bat` - 立即測試工具

### macOS / Linux
- `claude_scheduler.sh` - 主腳本
- `linux.sh` - cron 設定工具
- `test_now.sh` - 立即測試工具

### 共用
- `README.md` - 說明文件
- `scheduled_task.log` - 執行日誌
