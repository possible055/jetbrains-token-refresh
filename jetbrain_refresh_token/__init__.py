from pathlib import Path

# 定義全域路徑常數
BASE_PATH = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_PATH.parent
LOG_PATH = PROJECT_ROOT / "logs"
