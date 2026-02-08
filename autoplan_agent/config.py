"""配置管理模块。

该模块定义了应用的所有配置项，通过 Pydantic BaseSettings 支持环境变量。
"""

from pathlib import Path
from urllib.parse import urlparse
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用全局设置类。

    Attributes:
        model: LLM 模型名称。
        model_base_url: LLM API 基础 URL。
        llm_fake: 是否使用伪造的 LLM。
        runs_dir: 运行结果存储目录。
        logs_dir: 日志存储目录。
        templates_dir: 模板存储目录。
        plugins_dir: 插件存储目录。
        max_rows_per_query: 每个查询的最大行数。
        query_timeout_s: 查询超时时间（秒）。
        default_limit: 默认查询限制。
        enable_explain: 是否启用 EXPLAIN。
        agent_api_key: 代理 API Key。
        mysql_url: MySQL 连接 URL。
        mysql_host: MySQL 主机名。
        mysql_port: MySQL 端口号。
        mysql_user: MySQL 用户名。
        mysql_password: MySQL 密码。
        mysql_db: MySQL 数据库名。
        mysql_ssl_ca: MySQL SSL CA。
        mysql_ssl_cert: MySQL SSL 证书。
        mysql_ssl_key: MySQL SSL 密钥。
        mysql_connect_timeout_s: MySQL 连接超时时间（秒）。
        mysql_read_timeout_s: MySQL 读取超时时间（秒）。
        mysql_write_timeout_s: MySQL 写入超时时间（秒）。
        mysql_pool_recycle_s: MySQL 连接池回收时间（秒）。
        mysql_pool_size: MySQL 连接池大小。
        mysql_max_overflow: MySQL 连接池最大溢出。
        mysql_query_retries: MySQL 查询重试次数。
        mysql_query_backoff_s: MySQL 查询重试退避时间（秒）。
        pdf_backend: PDF 生成后端。
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    model: str = Field(default="Qwen/Qwen3-30B-A3B-Instruct-2507", alias="MODEL")
    model_base_url: str | None = Field(default=None, alias="MODEL_BASE_URL")
    llm_fake: bool = Field(default=False, alias="LLM_FAKE")

    runs_dir: Path = Field(default=Path("runs"), alias="RUNS_DIR")
    logs_dir: Path = Field(default=Path("runs"), alias="LOGS_DIR")
    templates_dir: Path = Field(default=Path("templates"), alias="TEMPLATES_DIR")
    plugins_dir: Path | None = Field(default=None, alias="PLUGINS_DIR")

    max_rows_per_query: int = Field(default=10000, alias="MAX_ROWS_PER_QUERY")
    query_timeout_s: int = Field(default=30, alias="QUERY_TIMEOUT_S")
    default_limit: int = Field(default=10000, alias="DEFAULT_LIMIT")
    enable_explain: bool = Field(default=True, alias="ENABLE_EXPLAIN")

    agent_api_key: str | None = Field(default=None, alias="AGENT_API_KEY")

    mysql_url: str | None = Field(default=None, alias="MYSQL_URL")
    mysql_host: str | None = Field(default=None, alias="MYSQL_HOST")
    mysql_port: int | None = Field(default=3306, alias="MYSQL_PORT")
    mysql_user: str | None = Field(default=None, alias="MYSQL_USER")
    mysql_password: str | None = Field(default=None, alias="MYSQL_PASSWORD")
    mysql_db: str | None = Field(default=None, alias="MYSQL_DB")
    mysql_ssl_ca: str | None = Field(default=None, alias="MYSQL_SSL_CA")
    mysql_ssl_cert: str | None = Field(default=None, alias="MYSQL_SSL_CERT")
    mysql_ssl_key: str | None = Field(default=None, alias="MYSQL_SSL_KEY")
    mysql_connect_timeout_s: int = Field(default=10, alias="MYSQL_CONNECT_TIMEOUT_S")
    mysql_read_timeout_s: int = Field(default=60, alias="MYSQL_READ_TIMEOUT_S")
    mysql_write_timeout_s: int = Field(default=60, alias="MYSQL_WRITE_TIMEOUT_S")
    mysql_pool_recycle_s: int = Field(default=3600, alias="MYSQL_POOL_RECYCLE_S")
    mysql_pool_size: int = Field(default=5, alias="MYSQL_POOL_SIZE")
    mysql_max_overflow: int = Field(default=10, alias="MYSQL_MAX_OVERFLOW")
    mysql_query_retries: int = Field(default=2, alias="MYSQL_QUERY_RETRIES")
    mysql_query_backoff_s: float = Field(default=1.0, alias="MYSQL_QUERY_BACKOFF_S")

    pdf_backend: str = Field(default="weasyprint", alias="PDF_BACKEND")

    def mysql_dsn(self) -> str | None:
        """生成 MySQL DSN 连接字符串。

        Returns:
            str | None: MySQL DSN 字符串，如果配置不完整则返回 None。
        """
        if self.mysql_url:
            try:
                parsed = urlparse(self.mysql_url)
                hostname = parsed.hostname or ""
            except Exception:
                hostname = ""
            if hostname in {"", "host"} and all([self.mysql_host, self.mysql_user, self.mysql_password, self.mysql_db]):
                return (
                    f"mysql+pymysql://{self.mysql_user}:{self.mysql_password}"
                    f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_db}"
                )
            return self.mysql_url
        if all([self.mysql_host, self.mysql_user, self.mysql_password, self.mysql_db]):
            return (
                f"mysql+pymysql://{self.mysql_user}:{self.mysql_password}"
                f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_db}"
            )
        return None
