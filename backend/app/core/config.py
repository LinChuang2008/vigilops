"""
应用配置模块 (Application Configuration Module)

使用 Pydantic Settings 管理 VigilOps 平台的所有配置项，支持从 .env 文件和环境变量读取。
提供数据库连接、Redis 缓存、AI 服务、JWT 认证等各模块的配置管理。

Uses Pydantic Settings to manage all configuration items for the VigilOps platform,
supporting reading from .env files and environment variables. Provides configuration
management for database connections, Redis cache, AI services, JWT authentication, and other modules.
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    应用全局配置类 (Application Global Configuration Class)
    
    使用 Pydantic BaseSettings 实现类型安全的配置管理。
    字段名自动映射同名环境变量（不区分大小写），支持 .env 文件加载。
    涵盖数据库、缓存、AI 服务、认证等所有核心组件的配置。
    
    Implements type-safe configuration management using Pydantic BaseSettings.
    Field names automatically map to same-named environment variables (case insensitive),
    supporting .env file loading. Covers configuration for all core components.
    """

    # 数据库配置 (Database Configuration)
    postgres_host: str = "localhost"  # PostgreSQL 主机地址 (PostgreSQL Host)
    postgres_port: int = 5432  # PostgreSQL 端口号 (PostgreSQL Port)
    postgres_db: str = "vigilops"  # 数据库名称 (Database Name)
    postgres_user: str = "vigilops"  # 数据库用户名 (Database Username)
    postgres_password: str = "vigilops_dev_password"  # 数据库密码 (Database Password)

    # Redis 配置 (Redis Configuration)
    redis_host: str = "localhost"  # Redis 主机地址 (Redis Host)
    redis_port: int = 6379  # Redis 端口号 (Redis Port)

    # AI 配置 (AI Service Configuration)
    ai_provider: str = "deepseek"  # AI 服务提供商 (AI Service Provider)
    ai_api_key: str = ""  # AI API 密钥 (AI API Key)
    ai_api_base: str = "https://api.deepseek.com/v1"  # AI API 基础 URL (AI API Base URL)
    ai_model: str = "deepseek-chat"  # AI 模型名称 (AI Model Name)
    ai_max_tokens: int = 2000  # AI 响应最大 Token 数 (AI Max Tokens)
    ai_auto_scan: bool = False  # 是否启用 AI 自动扫描 (Enable AI Auto Scan)

    # 记忆系统配置 (Memory System Configuration)
    memory_api_url: str = "http://host.docker.internal:8002/api/v1/memory"  # 记忆系统 API 地址 (Memory System API URL)
    memory_enabled: bool = True  # 是否启用记忆系统 (Enable Memory System)

    # Agent 自动修复配置 (Agent Auto-Remediation Configuration)
    agent_enabled: bool = False  # 是否启用自动修复 Agent (Enable Auto-Remediation Agent)
    # ⚠️ dry-run 默认开启！上线后建议先观察一周，确认无误再设为 False (Dry-run enabled by default for safety)
    agent_dry_run: bool = True  # 试运行模式：只记录不执行命令 (Dry-run Mode: Log Only, No Execution)
    agent_max_auto_per_hour: int = 10  # 每小时最大自动修复次数（限流） (Max Auto-Remediations Per Hour)
    agent_notify_on_success: bool = True  # 修复成功时发送通知 (Notify on Successful Remediation)
    agent_notify_on_failure: bool = True  # 修复失败/升级时发送通知 (Notify on Failed/Escalated Remediation)

    # JWT 认证配置 (JWT Authentication Configuration)
    jwt_secret_key: str = "change-me-in-production"  # JWT 签名密钥（生产环境必须修改） (JWT Secret Key)
    jwt_algorithm: str = "HS256"  # JWT 算法 (JWT Algorithm)
    jwt_access_token_expire_minutes: int = 120  # 访问令牌过期时间（分钟） (Access Token Expiry Minutes)
    jwt_refresh_token_expire_days: int = 7  # 刷新令牌过期时间（天） (Refresh Token Expiry Days)

    @property
    def database_url(self) -> str:
        """
        构造 PostgreSQL 异步连接 URL (Build PostgreSQL Async Connection URL)
        
        根据配置的数据库连接参数，生成适用于 asyncpg 驱动的连接字符串。
        用于 SQLAlchemy 异步数据库会话创建。
        
        Generates a connection string suitable for asyncpg driver based on configured
        database connection parameters. Used for SQLAlchemy async database session creation.
        """
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def redis_url(self) -> str:
        """
        构造 Redis 连接 URL (Build Redis Connection URL)
        
        根据配置的 Redis 连接参数，生成标准的 Redis 连接字符串。
        默认连接到数据库 0，用于缓存和会话存储。
        
        Generates a standard Redis connection string based on configured Redis parameters.
        Defaults to database 0, used for caching and session storage.
        """
        return f"redis://{self.redis_host}:{self.redis_port}/0"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}  # Pydantic 配置：自动加载 .env 文件 (Pydantic Config: Auto-load .env file)


# 全局配置实例 (Global Configuration Instance)
settings = Settings()
