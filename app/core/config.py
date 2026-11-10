from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr, field_validator

class Settings(BaseSettings):
    openai_api_key: SecretStr | None = None
    groq_api_key: SecretStr | None = None

    # "development" (default) or "production". Production hides /test-env.
    environment: str = "development"

    # Input size limits (Issue #13) — single source of truth
    max_body_bytes: int = 1 * 1024 * 1024  # 1 MB: max body size for any request
    max_ai_json_bytes: int = 5000          # max size of the JSON sent to the AI (/explain)
    max_ai_json_chars: int = 10000

    # Rate limits for /explain (Issue #27), the only endpoint that costs money.
    # Rolling windows, counted in memory (one instance). 0 disables a limit.
    explain_rate_per_minute: int = 4    # per client IP
    explain_rate_per_day: int = 40      # per client IP
    explain_global_per_day: int = 500   # all clients together: caps the Groq budget

    # Where the rate-limit counters live (Issue #30). Set (Vercel injects it
    # from the Upstash integration) -> shared Redis, required when the API runs
    # on several instances. Unset or empty -> process memory (local, Docker, tests).
    redis_url: SecretStr | None = None

    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8", 
        extra="ignore"
    )

    @property
    def redis_configured(self) -> bool:
        return bool(self.redis_url and self.redis_url.get_secret_value().strip())

    @property
    def is_production(self) -> bool:
        return self.environment.strip().lower() == "production"


settings = Settings()