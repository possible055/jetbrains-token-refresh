# Daemon 配置說明

## 配置文件位置

Daemon 配置文件現在位於：
```
jetbrains_refresh_token/daemon/daemon_config.json
```

## 配置結構

```json
{
  "scheduler": {
    "timezone": "Asia/Taipei",
    "max_workers": 3,
    "coalesce": true,
    "max_instances": 1,
    "misfire_grace_time": 300
  },
  "jobs": {
    "token_refresh": {
      "enabled": true,
      "interval_minutes": 5,
      "description": "自動檢查並刷新過期的 JWT tokens"
    },
    "quota_check": {
      "enabled": true,
      "interval_minutes": 2,
      "description": "檢查所有帳戶的配額使用情況"
    },
    "health_check": {
      "enabled": true,
      "interval_minutes": 1,
      "description": "Daemon 健康檢查和狀態更新"
    }
  },
  "logging": {
    "level": "INFO",
    "max_history": 100,
    "status_update_interval": 30
  },
  "paths": {
    "status_file": "logs/daemon_status.json",
    "command_file": "logs/daemon_commands.json",
    "log_directory": "logs"
  }
}
```

## 如何調整排程時間

編輯 `jetbrains_refresh_token/daemon/daemon_config.json` 文件中的 `interval_minutes` 值：

- `token_refresh.interval_minutes`: Token 刷新間隔（分鐘）
- `quota_check.interval_minutes`: 配額檢查間隔（分鐘）
- `health_check.interval_minutes`: 健康檢查間隔（分鐘）

## 啟用/停用任務

設定 `enabled` 為 `true` 或 `false` 來啟用或停用特定任務。

## 重新載入配置

修改配置後，重新啟動服務來應用新配置：
```bash
python main.py
```
