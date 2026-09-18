"""app 包初始化：确保 .env 尽早加载"""
from dotenv import load_dotenv
from pathlib import Path

# 项目根目录的 .env
_BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(_BASE_DIR / ".env", override=False)