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

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

settings = Settings()
