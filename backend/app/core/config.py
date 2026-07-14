from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    APP_NAME: str = "Autonomous Code Reviewer AI"
    APP_ENV: str = "development"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "replace-this-with-a-secure-random-secret-key-in-production"
    
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
    CHROMA_PERSIST_DIR: str = "./chroma_db"
    CHROMA_COLLECTION_NAME: str = "codebase_index"

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

settings = Settings()
