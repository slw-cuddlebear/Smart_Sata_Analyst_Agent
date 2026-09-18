import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# 项目根目录
BASE_DIR = Path(__file__).resolve().parent.parent

# 加载 .env（如果存在）
load_dotenv(BASE_DIR / ".env")


def _get(key: str, default: str = "") -> str:
    return os.getenv(key, default).strip()


@dataclass
class Settings:
    # LLM
    deepseek_api_key: str
    deepseek_base_url: str
    deepseek_model: str

    # 数据库
    db_type: str
    db_path: str

    mysql_host: str
    mysql_port: int
    mysql_user: str
    mysql_password: str
    mysql_database: str

    # LangSmith
    langchain_tracing_v2: bool
    langchain_api_key: str
    langchain_project: str

    # 应用
    output_dir: Path

    @property
    def database_url(self) -> str:
        """根据 DB_TYPE 返回 SQLAlchemy 连接字符串"""
        if self.db_type == "sqlite":
            # sqlite:///./data/sample.db
            path = (BASE_DIR / self.db_path.lstrip("./")).resolve()
            return f"sqlite:///{path}"
        if self.db_type == "mysql":
            return (
                f"mysql+pymysql://{self.mysql_user}:{self.mysql_password}"
                f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}"
                "?charset=utf8mb4"
            )
        raise ValueError(f"不支持的 DB_TYPE: {self.db_type}")


def load_settings() -> Settings:
    output_dir = Path(_get("OUTPUT_DIR", "./outputs"))
    if not output_dir.is_absolute():
        output_dir = BASE_DIR / output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    # LangSmith：优先新变量名，回退到旧变量名
    tracing = _get("LANGSMITH_TRACING") or _get("LANGCHAIN_TRACING_V2", "false")
    ls_key = _get("LANGSMITH_API_KEY") or _get("LANGCHAIN_API_KEY")
    ls_project = (
        _get("LANGSMITH_PROJECT")
        or _get("LANGCHAIN_PROJECT", "smart-data-analyst-agent")
    )

    return Settings(
        # LLM
        deepseek_api_key=_get("DEEPSEEK_API_KEY"),
        deepseek_base_url=_get("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        deepseek_model=_get("DEEPSEEK_MODEL", "deepseek-chat"),

        # 数据库
        db_type=_get("DB_TYPE", "sqlite").lower(),
        db_path=_get("DB_PATH", "./data/sample.db"),

        mysql_host=_get("MYSQL_HOST", "localhost"),
        mysql_port=int(_get("MYSQL_PORT", "3306") or "3306"),
        mysql_user=_get("MYSQL_USER", "root"),
        mysql_password=_get("MYSQL_PASSWORD", ""),
        mysql_database=_get("MYSQL_DATABASE", "demo"),

        # LangSmith
        langchain_tracing_v2=tracing.lower() == "true",
        langchain_api_key=ls_key,
        langchain_project=ls_project,

        # 应用
        output_dir=output_dir,
    )


settings = load_settings()