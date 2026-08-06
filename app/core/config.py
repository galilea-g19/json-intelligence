from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr, field_validator

class Settings(BaseSettings):
    openai_api_key: SecretStr | None = None
    groq_api_key: SecretStr | None = None

    # Input size limits (Issue #13) — single source of truth
    max_body_bytes: int = 1 * 1024 * 1024  # 1 MB: max body size for any request
    max_ai_json_bytes: int = 5000          # max size of the JSON sent to the AI (/explain)
    max_ai_json_chars: int = 10000

    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8", 
        extra="ignore"
    )

settings = Settings()