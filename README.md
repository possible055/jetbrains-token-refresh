# JetBrains Token Refresh 工具

這個專案提供一個指令列工具，用於管理及自動更新 JetBrains AI 相關帳戶的 JWT 與 ID Token。
程式會讀取專案根目錄的 `config.json`（或由 `--config` 指定的路徑），依據檔案內容自動刷新即將過期的 Token，同時可備份設定檔、檢查使用配額並列出帳戶資訊。

## 功能特色

- **刷新 Access Token**：根據 ID Token 與授權資訊取得新的 JWT。可單一帳戶或所有帳戶一起更新。
- **刷新 ID Token**：利用 Refresh Token 更新帳戶的 ID Token 及 Access Token。
- **配額查詢**：呼叫 JetBrains API 取得目前剩餘使用量與比率。
- **備份設定**：在變更 Token 前自動備份設定檔至 `config-backup.json`。
- **列出帳戶資訊**：以易讀格式輸出各帳戶的 Token、到期時間與配額資訊。

## 安裝方式

1. 需要 Python 3.11 以上環境。
2. 安裝相依套件：
   ```bash
   pip install -r requirements.txt
   ```
3. 或者可直接使用 `pip install .` 於專案根目錄安裝。安裝時會自動設定 `jetbrain_refresh_token` 套件。

## 設定檔格式

`config.json` 檔案包含多個帳戶資訊，結構如下（節錄）：

```json
{
  "accounts": {
    "account_name": {
      "id_token": "<JWT>",
      "refresh_token": "<refresh token>",
      "access_token": "<JWT>",
      "access_token_expires_at": 1700000000,
      "license_id": "<license id>",
      "created_time": 1690000000,
      "quota_info": {
        "remaining_amount": "...",
        "usage_percentage": 0.0,
        "status": "normal"
      },
      "id_token_expires_at": 1700000000
    }
  }
}
```

預設路徑為 `config.json`，備份檔為 `config-backup.json`，可透過 `--config` 指定其他位置。

## 使用方法

主程式為 `main.py`，可直接執行並搭配下列參數：

```bash
python main.py [選項]
```

常用選項說明：

- `--config <路徑>`：指定設定檔位置。
- `--refresh-access <帳戶>`：刷新指定帳戶的 Access Token。
- `--refresh-all-access`：刷新所有帳戶的 Access Token。
- `--refresh-auth <帳戶>`：刷新指定帳戶的 ID Token（同時更新 Access Token）。
- `--refresh-all-auth`：刷新所有帳戶的 ID Token。
- `--check-quota`：查詢所有帳戶的剩餘配額並寫入設定檔。
- `--list`：列出目前設定檔內的帳戶資訊。
- `--backup`：手動備份設定檔。
- `--force`：不論 Token 是否過期都強制刷新。
- `--test`：呼叫程式內建的測試函式。

執行時若未帶入任何選項，程式將顯示說明文字。

## 紀錄檔

所有執行紀錄會寫入 `logs/jetbrain_api.log`，方便除錯與追蹤操作狀態。

## 授權條款

本專案採用 MIT License，詳見 [LICENSE](LICENSE)。
