from pathlib import Path
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

# Compute the absolute path to the .env file that lives alongside this config module.
# This guarantees uvicorn / celery workers / tests all load the same file regardless
# of the working directory at startup.
_ENV_FILE = Path(__file__).resolve().parent.parent.parent / ".env"

class Settings(BaseSettings):
    APP_NAME: str = "Autonomous Code Reviewer AI"
    APP_ENV: str = "development"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "replace-this-with-a-secure-random-secret-key-in-production"
    OPENAI_API_KEY: str = ""
    DATABASE_URL: str = "sqlite:///./code_reviewer.db"
    
    # Storage and Loader Config
    TEMP_STORAGE_PATH: str = "./storage/temp"
    MAX_UPLOAD_SIZE_MB: int = 100
    CLONE_TIMEOUT_SEC: int = 60

    # RAG / Embedding Config — Local Sentence Transformers (zero-cost, no API keys)
    EMBEDDING_PROVIDER: str = "local"  # "local", "openai", "anthropic"
    LOCAL_EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    EMBEDDING_DIMENSIONS: int = 384
    RAG_BATCH_SIZE: int = 100
    RAG_REQUEST_TIMEOUT: float = 30.0
    RAG_MAX_RETRIES: int = 3
    CHROMA_HOST: Optional[str] = None
    CHROMA_PORT: int = 8000
    CHROMA_PERSIST_DIR: str = "./chroma_db"
    CHROMA_COLLECTION_NAME: str = "codebase_index"

    # AI Review Agent Config
    LLM_PROVIDER: str = "groq"  # "groq", "anthropic", "openai", "local"
    
    # Groq Configuration (primary provider)
    GROQ_API_KEY: str = "GROQ API KEY HERE"
    GROQ_MODEL: str = "openai/gpt-oss-120b"
    
    # Legacy keys — kept for backward compatibility during transition
    ANTHROPIC_API_KEY: str = ""
    REVIEW_MODEL: str = "openai/gpt-oss-120b"
    REVIEW_TEMPERATURE: float = 0.0
    REVIEW_MAX_TOKENS: int = 4000
    REVIEW_CONTEXT_WINDOW_LIMIT: int = 180000  # safety limit below 200k
    REVIEW_MAX_RETRIES: int = 3
    REVIEW_TIMEOUT_SEC: float = 60.0

    # Token Cost Config (per 1 Million tokens)
    # Groq pricing for openai/gpt-oss-120b (current as of 2026)
    REVIEW_COST_INPUT_1M: float = 0.60    # $0.60 per M input tokens
    REVIEW_COST_OUTPUT_1M: float = 0.90   # $0.90 per M output tokens

    # Prompt Versions
    PROMPT_VERSION_REVIEW: str = "review_v1"
    PROMPT_VERSION_SECURITY: str = "security_v1"
    PROMPT_VERSION_PERFORMANCE: str = "performance_v1"
    PROMPT_VERSION_DOCUMENTATION: str = "documentation_v1"

    # Production Infrastructure / Logging Settings
    LOG_LEVEL: str = "INFO"
    LOG_FILE_PATH: str = "./storage/logs/app.log"
    LOG_FORMAT: str = "json"  # "json" or "plain"
    CORS_ALLOWED_ORIGINS: list[str] = ["*"]
    APP_VERSION: str = "1.0.0"

    # Celery & Redis task settings
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"
    CELERY_MAX_RETRIES: int = 3
    CELERY_RETRY_DELAY: int = 5
    CELERY_RETRY_BACKOFF: bool = True
    JOB_TIMEOUT_SECONDS: int = 1800

    # ---- External / Third-Party Integrations (not consumed by backend code directly) ----
    # LangSmith observability (used by LangChain runtime)
    LANGCHAIN_TRACING_V2: bool = False
    LANGCHAIN_ENDPOINT: str = "https://api.smith.langchain.com"
    LANGCHAIN_API_KEY: str = ""
    LANGCHAIN_PROJECT: str = "autonomous-code-reviewer-ai"

    # MCP (Model Context Protocol) server config
    MCP_PORT: int = 8500
    MCP_SERVER_NAME: str = "reviewer-mcp-server"

    # Storage provider selection (local / S3)
    STORAGE_PROVIDER: str = "local"
    LOCAL_STORAGE_PATH: str = "./storage"

    # AWS S3 credentials (for optional S3-based storage)
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_BUCKET_NAME: str = ""

    # Legacy / deprecated (kept for backward compat, not referenced in current code)
    VECTOR_DB_DIR: str = "./chroma_db"  # replaced by CHROMA_PERSIST_DIR

    model_config = SettingsConfigDict(
        env_file=_ENV_FILE,
        case_sensitive=True,
        extra="allow",  # Accept env vars defined in .env but not explicitly declared in Settings
                         # (e.g. Docker, LangSmith, AWS, MCP vars consumed by other services)
    )

    @model_validator(mode="after")
    def _debug_env_loading(self):
        """Debug logging: verify .env file was loaded (never prints the key value)."""
        import logging, os
        log = logging.getLogger("app.core.config")
        
        env_path = str(self.model_config.get("env_file", "N/A"))
        log.info("Resolved .env file path: %s", env_path)
        log.info("Config file exists on disk: %s", Path(env_path).exists() if env_path != "N/A" else "unknown")

        key_len = len(self.GROQ_API_KEY) if self.GROQ_API_KEY else 0
        log.info("GROQ_API_KEY loaded: %s | Length: %d", "YES" if key_len > 0 else "NO", key_len)
        log.info("LLM_PROVIDER active: %s", self.LLM_PROVIDER)
        return self

    def validate_config(self, force: bool = False) -> None:
        """
        Validates the configuration settings based on active provider selections.
        Fails fast by raising ValueError during startup if configurations are invalid.
        """
        import sys
        if not force and ("pytest" in sys.modules or self.APP_ENV == "test"):
            # Skip checking API keys during unit tests
            return

        errors = []
        if self.LLM_PROVIDER == "groq":
            if not self.GROQ_API_KEY:
                errors.append("GROQ_API_KEY is required when LLM_PROVIDER is 'groq'.")
        elif self.LLM_PROVIDER == "anthropic":
            if not self.ANTHROPIC_API_KEY:
                errors.append("ANTHROPIC_API_KEY is required when LLM_PROVIDER is 'anthropic'.")
        elif self.LLM_PROVIDER == "openai":
            if not self.OPENAI_API_KEY:
                errors.append("OPENAI_API_KEY is required when LLM_PROVIDER is 'openai'.")

        # Local embedding provider requires no API key.
        # Only validate API keys when a paid cloud provider is explicitly selected.
        if self.EMBEDDING_PROVIDER == "openai":
            if not self.OPENAI_API_KEY:
                errors.append("OPENAI_API_KEY is required when EMBEDDING_PROVIDER is 'openai'.")
        elif self.EMBEDDING_PROVIDER == "anthropic":
            if not self.ANTHROPIC_API_KEY:
                errors.append("ANTHROPIC_API_KEY is required when EMBEDDING_PROVIDER is 'anthropic'.")

        if errors:
            raise ValueError("Configuration validation failed:\n" + "\n".join(errors))

settings = Settings()
