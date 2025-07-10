# JetBrains Token Refresh 工具

这个专案提供一个指令列工具和网页介面，用于管理及自动更新 JetBrains AI 相关帐户的 JWT Access Token。
程式会读取专案根目录的 `config.json`，依据档案内容自动刷新即将过期的 Token，同时可备份设定档、检查使用配额并列出帐户资讯。

## 功能特色

- **刷新 Access Token**：根据 ID Token 与授权资讯取得新的 JWT。可单一帐户或所有帐户一起更新。
- **配额查询**：呼叫 JetBrains API 取得目前剩余使用量与比率。
- **列出帐户资讯**：以易读格式输出各帐户的 Token、到期时间与配额资讯。
- **网页介面**：提供 Streamlit 网页介面进行视觉化管理和监控。

## 设定档格式

`config.json` 档案包含多个帐户资讯，结构如下（节录）：

```json
{
  "accounts": {
    "account_name": {
      "id_token": "<JWT>",
      "access_token": "<Token>",
      "access_token_expires_at": 1700000000,
      "license_id": "<license ID>",
      "created_time": 1690000000,
      "quota_info": {
        "remaining_amount": "...",
        "usage_percentage": 0.0,
        "status": "normal"
      }
    }
  }
}
```

## 使用范例

### Docker Compose

```yaml
services:
  gui:
    container_name: jetbrains_refresh_token
    image: apparition635/jetbrains_refresh_token:0.3.0
    ports:
      - "8501:8501"
    volumes:
      - ./config.json:/app/config.json
      - ./jetbrainsai.json:/app/jetbrainsai.json
      - ./logs:/app/logs
    restart: unless-stopped
    networks:
      - jetbrains-network

  api:
    container_name: jetbrainsai2api
    image: apparition635/jetbrainsai2api:v3.0.0
    ports:
      - "8000:8000"
    volumes:
      - ./jetbrainsai.json:/app/jetbrainsai.json:ro
      - ./client_api_keys.json:/app/client_api_keys.json:ro
      - ./models.json:/app/models.json:ro
    environment:
      - DEBUG_MODE=${DEBUG_MODE:-false}
    restart: unless-stopped
    networks:
      - jetbrains-network

networks:
  jetbrains-network:
    name: jetbrains-network
    driver: bridge
```

### 外部套件相容性

可自动转换为 jetbrainsai 格式

**外部格式** (`jetbrainsai.json`):
```json
[
  {
    "jwt": "eyJ...",
    "licenseId": "46GYU...",
    "authorization": "eyJ..."
  }
]
```

## 纪录档

所有执行纪录会写入 `logs/jetbrain_api.log`，方便除错与追踪操作状态。

## 授权条款

本专案采用 MIT License，详见 [LICENSE](LICENSE)。
