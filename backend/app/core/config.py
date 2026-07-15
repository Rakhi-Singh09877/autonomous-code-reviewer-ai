from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

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

    # RAG / Embedding Config
    EMBEDDING_PROVIDER: str = "openai"  # "openai", "anthropic", "local"
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIMENSIONS: int = 1536
    RAG_BATCH_SIZE: int = 100
    RAG_REQUEST_TIMEOUT: float = 30.0
    RAG_MAX_RETRIES: int = 3
    CHROMA_HOST: Optional[str] = None
    CHROMA_PORT: int = 8000
    CHROMA_PERSIST_DIR: str = "./chroma_db"
    CHROMA_COLLECTION_NAME: str = "codebase_index"

    # AI Review Agent Config
    LLM_PROVIDER: str = "anthropic"  # "anthropic", "openai", "local"
    ANTHROPIC_API_KEY: str = ""
    REVIEW_MODEL: str = "claude-3-5-sonnet-20241022"
    REVIEW_TEMPERATURE: float = 0.0
    REVIEW_MAX_TOKENS: int = 4000
    REVIEW_CONTEXT_WINDOW_LIMIT: int = 180000  # safety limit below 200k
    REVIEW_MAX_RETRIES: int = 3
    REVIEW_TIMEOUT_SEC: float = 60.0

    # Token Cost Config (per 1 Million tokens)
    REVIEW_COST_INPUT_1M: float = 3.0   # $3.00 per M tokens
    REVIEW_COST_OUTPUT_1M: float = 15.0 # $15.00 per M tokens

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

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

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
        if self.LLM_PROVIDER == "anthropic":
            if not self.ANTHROPIC_API_KEY:
                errors.append("ANTHROPIC_API_KEY is required when LLM_PROVIDER is 'anthropic'.")
        elif self.LLM_PROVIDER == "openai":
            if not self.OPENAI_API_KEY:
                errors.append("OPENAI_API_KEY is required when LLM_PROVIDER is 'openai'.")

        if self.EMBEDDING_PROVIDER == "openai":
            if not self.OPENAI_API_KEY:
                errors.append("OPENAI_API_KEY is required when EMBEDDING_PROVIDER is 'openai'.")

        if errors:
            raise ValueError("Configuration validation failed:\n" + "\n".join(errors))

settings = Settings()
