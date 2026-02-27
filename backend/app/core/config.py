"""
应用配置模块 (Application Configuration Module)

使用 Pydantic Settings 管理 VigilOps 平台的所有配置项，支持从 .env 文件和环境变量读取。
提供数据库连接、Redis 缓存、AI 服务、JWT 认证等各模块的配置管理。

Uses Pydantic Settings to manage all configuration items for the VigilOps platform,
supporting reading from .env files and environment variables. Provides configuration
management for database connections, Redis cache, AI services, JWT authentication, and other modules.
"""
import logging
import os
import secrets

from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


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

    # 日志后端配置 (Log Backend Configuration)
    log_backend_type: str = "postgresql"  # 日志后端类型：postgresql/clickhouse/loki (Log Backend Type)
    log_retention_days: int = 7  # 日志保留天数 (Log Retention Days)
    
    # ClickHouse 配置 (ClickHouse Configuration)
    clickhouse_host: str = "localhost"  # ClickHouse 主机地址 (ClickHouse Host)
    clickhouse_port: int = 8123  # ClickHouse HTTP 端口 (ClickHouse HTTP Port)
    clickhouse_user: str = "default"  # ClickHouse 用户名 (ClickHouse Username)
    clickhouse_password: str = ""  # ClickHouse 密码 (ClickHouse Password)
    clickhouse_database: str = "vigilops"  # ClickHouse 数据库名 (ClickHouse Database)
    
    # Loki 配置 (Loki Configuration)
    loki_url: str = "http://localhost:3100"  # Loki 服务地址 (Loki Service URL)
    loki_username: str = ""  # Loki 用户名 (Loki Username)
    loki_password: str = ""  # Loki 密码 (Loki Password)

    # Agent 自动修复配置 (Agent Auto-Remediation Configuration)
    agent_enabled: bool = False  # 是否启用自动修复 Agent (Enable Auto-Remediation Agent)
    # ⚠️ dry-run 默认开启！上线后建议先观察一周，确认无误再设为 False (Dry-run enabled by default for safety)
    agent_dry_run: bool = True  # 试运行模式：只记录不执行命令 (Dry-run Mode: Log Only, No Execution)
    agent_max_auto_per_hour: int = 10  # 每小时最大自动修复次数（限流） (Max Auto-Remediations Per Hour)
    agent_notify_on_success: bool = True  # 修复成功时发送通知 (Notify on Successful Remediation)
    agent_notify_on_failure: bool = True  # 修复失败/升级时发送通知 (Notify on Failed/Escalated Remediation)

    # JWT 认证配置 (JWT Authentication Configuration)
    # ⚠️ 生产环境必须通过环境变量 JWT_SECRET_KEY 设置！未设置时自动生成随机密钥（每次重启会变化）
    # ⚠️ MUST set JWT_SECRET_KEY env var in production! Auto-generated random key changes on every restart.
    jwt_secret_key: str = ""  # JWT 签名密钥 (JWT Secret Key)
    jwt_algorithm: str = "HS256"  # JWT 算法 (JWT Algorithm)
    jwt_access_token_expire_minutes: int = 120  # 访问令牌过期时间（分钟） (Access Token Expiry Minutes)
    jwt_refresh_token_expire_days: int = 7  # 刷新令牌过期时间（天） (Refresh Token Expiry Days)
    
    # OAuth 认证配置 (OAuth Authentication Configuration)
    # Google OAuth
    google_client_id: str = ""  # Google OAuth 客户端 ID (Google OAuth Client ID)
    google_client_secret: str = ""  # Google OAuth 客户端密钥 (Google OAuth Client Secret)
    
    # GitHub OAuth
    github_client_id: str = ""  # GitHub OAuth 客户端 ID (GitHub OAuth Client ID)
    github_client_secret: str = ""  # GitHub OAuth 客户端密钥 (GitHub OAuth Client Secret)
    
    # GitLab OAuth
    gitlab_client_id: str = ""  # GitLab OAuth 客户端 ID (GitLab OAuth Client ID)
    gitlab_client_secret: str = ""  # GitLab OAuth 客户端密钥 (GitLab OAuth Client Secret)
    
    # Microsoft OAuth
    microsoft_client_id: str = ""  # Microsoft OAuth 客户端 ID (Microsoft OAuth Client ID)
    microsoft_client_secret: str = ""  # Microsoft OAuth 客户端密钥 (Microsoft OAuth Client Secret)
    
    # LDAP/Active Directory 配置 (LDAP/Active Directory Configuration)
    ldap_server: str = ""  # LDAP 服务器地址 (LDAP Server Host)
    ldap_port: int = 389  # LDAP 服务器端口 (LDAP Server Port)
    ldap_use_tls: bool = False  # 是否使用 TLS/SSL (Use TLS/SSL)
    ldap_base_dn: str = ""  # LDAP 基础 DN (LDAP Base DN) 例如: "dc=company,dc=com"
    ldap_user_search: str = "uid={}"  # 用户搜索模式 (User Search Pattern) 例如: "uid={}" 或 "cn={}"
    ldap_bind_dn: str = ""  # 绑定 DN (Bind DN) - 管理员账户，留空使用用户凭证
    ldap_bind_password: str = ""  # 绑定密码 (Bind Password)

    # 安全和限流配置 (Security and Rate Limiting Configuration)
    enable_rate_limiting: bool = True  # 是否启用 API 限流 (Enable API Rate Limiting)
    enable_security_headers: bool = True  # 是否启用安全响应头 (Enable Security Headers)
    max_request_size: int = 10 * 1024 * 1024  # 最大请求体大小（字节） (Max Request Body Size in Bytes)
    environment: str = "development"  # 运行环境：development/production (Runtime Environment)
    frontend_url: str = "http://localhost:3001"  # 前端 URL (Frontend URL)
    api_domain: str = "localhost:8001"  # API 域名 (API Domain)

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

    @property
    def clickhouse_url(self) -> str:
        """
        构造 ClickHouse 连接 URL (Build ClickHouse Connection URL)
        
        根据配置的 ClickHouse 连接参数，生成 HTTP 接口访问的基础 URL。
        用于通过 HTTP 接口进行日志数据的高性能存储和查询。
        
        Generates a base URL for HTTP interface access based on configured ClickHouse parameters.
        Used for high-performance log data storage and querying via HTTP interface.
        """
        return f"http://{self.clickhouse_host}:{self.clickhouse_port}"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}  # Pydantic 配置：自动加载 .env 文件 (Pydantic Config: Auto-load .env file)


# 全局配置实例 (Global Configuration Instance)
settings = Settings()

# JWT 密钥安全检查：生产环境必须设置，开发环境自动生成
_env = os.getenv("ENVIRONMENT", "production").lower()
if not settings.jwt_secret_key or settings.jwt_secret_key == "change-me-in-production":
    if _env == "production":
        logger.error(
            "🔴 JWT_SECRET_KEY 未设置！生产环境必须通过环境变量设置固定密钥。"
            "请在 .env 中添加: JWT_SECRET_KEY=<random-64-char-string>"
            " | JWT_SECRET_KEY not set in production! Set it in .env."
        )
        # 仍然生成随机密钥保证能启动，但强烈警告
    settings.jwt_secret_key = secrets.token_urlsafe(64)
    logger.warning(
        "JWT_SECRET_KEY 已自动生成随机密钥。重启后所有 token 失效。"
        " | Auto-generated JWT key. Tokens invalidated on restart."
    )
