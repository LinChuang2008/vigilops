"""
应用配置模块

使用 Pydantic Settings 管理所有配置项，支持从 .env 文件和环境变量读取。
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用全局配置类，字段名自动映射同名环境变量（不区分大小写）。"""

    # 数据库配置
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "vigilops"
    postgres_user: str = "vigilops"
    postgres_password: str = "vigilops_dev_password"

    # Redis 配置
    redis_host: str = "localhost"
    redis_port: int = 6379

    # AI 配置
    ai_provider: str = "deepseek"
    ai_api_key: str = ""
    ai_api_base: str = "https://api.deepseek.com/v1"
    ai_model: str = "deepseek-chat"
    ai_max_tokens: int = 2000
    ai_auto_scan: bool = False

    # 记忆系统配置
    memory_api_url: str = "http://host.docker.internal:8002/api/v1/memory"
    memory_enabled: bool = True

    # JWT 认证配置
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 120
    jwt_refresh_token_expire_days: int = 7

    @property
    def database_url(self) -> str:
        """构造 PostgreSQL 异步连接 URL。"""
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def redis_url(self) -> str:
        """构造 Redis 连接 URL。"""
        return f"redis://{self.redis_host}:{self.redis_port}/0"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
