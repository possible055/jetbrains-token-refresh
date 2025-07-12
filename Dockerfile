# 使用官方 Python 3.12 slim 映像作為基礎映像
FROM python:3.12-slim

# 設定工作目錄
WORKDIR /app

# 設定環境變數
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 安裝系統依賴
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# 複製依賴文件
COPY requirements.txt pyproject.toml ./

# 安裝 Python 依賴
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# 複製應用程式代碼
COPY . .

# 創建必要的目錄
RUN mkdir -p logs

# 設定權限
RUN chmod +x main.py

# 暴露端口
# 8501 for Streamlit web interface
EXPOSE 8501

# 健康檢查 - 檢查 Web UI 和 Daemon 狀態
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health && \
        test -f /app/logs/daemon_status.json && \
        test $(find /app/logs/daemon_status.json -mmin -2 | wc -l) -gt 0 || exit 1

# 預設命令：啟動完整服務（前端 + 後端）
CMD ["python", "main.py", "--web-port", "8501"]
