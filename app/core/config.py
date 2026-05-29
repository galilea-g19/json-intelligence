from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr, field_validator

class Settings(BaseSettings):
    openai_api_key: SecretStr | None = None 
    groq_api_key: SecretStr | None = None

    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8", 
        extra="ignore"
    )

settings = Settings()