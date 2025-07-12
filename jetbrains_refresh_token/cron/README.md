# JetBrains Token Refresh Cron Scripts

這個資料夾包含了兩種 cron 解決方案：

## 方案 1: 簡單方案（推薦）

### 文件
- `simple_cron.py` - 簡單的 44 行 Python 腳本
- `cron_refresh.sh` - 11 行 shell 腳本
- 使用系統 cron 進行調度

### 使用方式

#### 1. 直接執行 Python 腳本
```bash
# 刷新 token 和檢查配額
python -m jetbrains_refresh_token.cron.simple_cron

# 只刷新 token
python -m jetbrains_refresh_token.cron.simple_cron --mode token

# 只檢查配額
python -m jetbrains_refresh_token.cron.simple_cron --mode quota
```

#### 2. 執行 shell 腳本
```bash
./jetbrains_refresh_token/cron/cron_refresh.sh
```

#### 3. 系統 cron 設置
```bash
# 編輯 crontab
crontab -e

# 添加以下行：
# 每 6 小時執行一次
0 */6 * * * /path/to/jetbrains_refresh_token/cron/cron_refresh.sh

# 或者每天 8 點和 20 點執行
0 8,20 * * * /path/to/jetbrains_refresh_token/cron/cron_refresh.sh
```

## 方案 2: 複雜方案（APScheduler）

### 文件
- `cron_scheduler.py` - 主調度器（213 行）
- `cron_config.py` - 配置管理（64 行）
- `run_cron.py` - 命令行啟動器（132 行）
- `__init__.py` - 模組初始化

### 使用方式
```bash
# 運行完整調度器
python -m jetbrains_refresh_token.cron.run_cron

# 後台運行
python -m jetbrains_refresh_token.cron.run_cron --background

# 查看調度工作
python -m jetbrains_refresh_token.cron.run_cron --list-jobs
```

## 比較

| 特性 | 簡單方案 | 複雜方案 |
|------|----------|----------|
| 代碼行數 | 55 行 | 400+ 行 |
| 外部依賴 | 無 | APScheduler |
| 調度方式 | 系統 cron | Python 內建 |
| 資源消耗 | 低 | 中等 |
| 適用場景 | 大多數情況 | 需要複雜調度 |

## 推薦使用

對於大多數使用案例，**建議使用簡單方案**，因為：
1. 代碼簡潔易維護
2. 無外部依賴
3. 使用標準 Unix cron 系統
4. 資源消耗低
5. 符合 Unix 哲學

只有在需要複雜調度功能時，才考慮使用複雜方案。