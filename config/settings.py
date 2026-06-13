import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings:
    FEISHU_WEBHOOK_URL = os.getenv("FEISHU_WEBHOOK_URL", "")
    TQSDK_USERNAME = os.getenv("TQSDK_USERNAME", "")
    TQSDK_PASSWORD = os.getenv("TQSDK_PASSWORD", "")
    
    # 大商所API配置
    DCE_API_KEY = os.getenv("DCE_API_KEY", "")
    DCE_API_SECRET = os.getenv("DCE_API_SECRET", "")
    DCE_API_URL = os.getenv("DCE_API_URL", "https://api.dce.com.cn")
    
    # 仓单采集配置（已修复API路径问题）
    ENABLE_RECEIPT_COLLECTION = os.getenv("ENABLE_RECEIPT_COLLECTION", "true").lower() == "true"
    
    DB_PATH = BASE_DIR / os.getenv("DB_PATH", "data/db/egg_monitor.db")
    DB_URL = f"sqlite:///{DB_PATH}"
    
    API_HOST = os.getenv("API_HOST", "127.0.0.1")
    API_PORT = int(os.getenv("API_PORT", "8000"))
    
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
    DATA_DIR = BASE_DIR / "data"
    LOG_DIR = BASE_DIR / "logs"
    
    @classmethod
    def ensure_dirs(cls):
        cls.DATA_DIR.mkdir(exist_ok=True)
        (cls.DATA_DIR / "db").mkdir(exist_ok=True)
        (cls.DATA_DIR / "uploads").mkdir(exist_ok=True)
        (cls.DATA_DIR / "backup").mkdir(exist_ok=True)
        cls.LOG_DIR.mkdir(exist_ok=True)

settings = Settings()
