from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    openai_api_key: str

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()

```
**Validate `main.py`:**
```python
    from fastapi import FastAPI
    from app.core.config import settings

    app = FastAPI()

    @app.get("/check-config")
    def test_config():
        return {"key_exists": bool(settings.openai_api_key)}
```