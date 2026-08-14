from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    app_name: str = "UniAgent"
    llm_provider: str = "mock"
    gemini_api_key: str = ""
    database_url: str = "sqlite:///./app.db"
    cors_origins: str = "http://localhost:3000"
    jwt_secret: str = "dev-secret-change-me-0123456789abcdef"  # >= 32 bytes for HS256
    jwt_algorithm: str = "HS256"
    jwt_expires_minutes: int = 720  # 12 hours; plenty for a hackathon demo

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
